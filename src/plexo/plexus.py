#  pyplexo
#   Copyright © 2018-2020  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
import itertools
from typing import Any, Iterable, Optional, Set, Tuple
from weakref import WeakKeyDictionary
from uuid import uuid4, UUID

from pyrsistent import pset, PSet
from plexo.ganglion.internal import GanglionInternalBase
from returns.curry import partial

from plexo.coder import Coder
from plexo.ganglion.external import GanglionExternalBase
from plexo.ganglion.inproc import GanglionInproc
from plexo.typing import E
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class Plexus(Ganglion):
    def __init__(self, ganglia: Iterable[Ganglion] = (), loop=None):
        ganglia = pset(ganglia)
        self.inproc_ganglion: GanglionInternalBase = GanglionInproc(loop=loop)

        self._external_ganglia = pset(ganglion for ganglion in ganglia
                                            if isinstance(ganglion, GanglionExternalBase))
        self._external_ganglia_lock = asyncio.Lock()
        self._internal_ganglia = pset(ganglion for ganglion in ganglia
                                            if not isinstance(ganglion, GanglionExternalBase))
        self._internal_ganglia = self._internal_ganglia.add(self.inproc_ganglion)
        self._internal_ganglia_lock = asyncio.Lock()

        self._coders: PSet[Coder] = pset()
        self._coders_lock = asyncio.Lock()
        self._coder_ganglia: PSet[Tuple[Coder, Ganglion]] = pset()
        self._coder_ganglia_lock = asyncio.Lock()

        self._reactions: WeakKeyDictionary[UUID, Set[Ganglion]] = WeakKeyDictionary()
        self._reaction_locks: WeakKeyDictionary[UUID, asyncio.Lock] = WeakKeyDictionary()
        self._reaction_locks_lock = asyncio.Lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for ganglion in itertools.chain(self._internal_ganglia, self._external_ganglia):
                ganglion.close()
        except RuntimeError:
            pass

    async def _internal_reaction(self, current: Ganglion, data: Any, reaction_id: Optional[UUID] = None):
        if reaction_id is None:
            reaction_id = uuid4()
            reaction_lock = asyncio.Lock()
            async with self._reaction_locks_lock:
                self._reaction_locks[reaction_id] = reaction_lock
        else:
            reaction_lock = self._reaction_locks[reaction_id]
        
        async with reaction_lock:
            if reaction_id not in self._reactions:
                self._reactions[reaction_id] = {current}
            else:
                self._reactions[reaction_id].add(current)

            internal = (ganglion.transmit(data, reaction_id) for ganglion in self._internal_ganglia - self._reactions[reaction_id])
            external = (ganglion.transmit_encode(data, reaction_id) for ganglion in self._external_ganglia - self._reactions[reaction_id])

        try:
            await asyncio.gather(*itertools.chain(internal, external))
        except ValueError:
            # Got empty list, continue
            pass

    async def _external_internal_reaction(self, current: GanglionExternalBase, data: Any, reaction_id: Optional[UUID] = None):
        if reaction_id is None:
            reaction_id = uuid4()
            reaction_lock = asyncio.Lock()
            async with self._reaction_locks_lock:
                self._reaction_locks[reaction_id] = reaction_lock
        else:
            reaction_lock = self._reaction_locks[reaction_id]
        
        async with reaction_lock:
            if reaction_id not in self._reactions:
                self._reactions[reaction_id] = {current}
            else:
                self._reactions[reaction_id].add(current)

            internal = (ganglion.transmit(data, reaction_id) for ganglion in self._internal_ganglia - self._reactions[reaction_id])

        try:
            await asyncio.gather(*internal)
        except ValueError:
            # Got empty list, continue
            pass

    async def _external_external_reaction(self, current: GanglionExternalBase, data: E, reaction_id: Optional[UUID] = None):
        if reaction_id is None:
            reaction_id = uuid4()
            reaction_lock = asyncio.Lock()
            async with self._reaction_locks_lock:
                self._reaction_locks[reaction_id] = reaction_lock
        else:
            reaction_lock = self._reaction_locks[reaction_id]
        
        async with reaction_lock:
            if reaction_id not in self._reactions:
                self._reactions[reaction_id] = {current}
            else:
                self._reactions[reaction_id].add(current)

            external = (ganglion.transmit(data, reaction_id) for ganglion in self._external_ganglia - self._reactions[reaction_id])

        try:
            await asyncio.gather(*external)
        except ValueError:
            # Got empty list, continue
            pass

    async def infuse_ganglion(self, ganglion: Ganglion):
        if isinstance(ganglion, GanglionExternalBase):
            async with self._external_ganglia_lock:
                self._external_ganglia = self._external_ganglia.add(ganglion)
        else:
            async with self._internal_ganglia_lock:
                self._internal_ganglia = self._internal_ganglia.add(ganglion)

        await self._update_coder_ganglia()

    async def _update_coders(self, coder: Coder):
        async with self._coders_lock:
            self._coders = self._coders.add(coder)

        await self._update_coder_ganglia()

    async def _update_coder_ganglia(self):
        all_ganglia = itertools.chain(self._internal_ganglia, self._external_ganglia)
        all_coder_ganglia = pset(itertools.product(self._coders, all_ganglia))
        async with self._coder_ganglia_lock:
            new_coder_ganglia = all_coder_ganglia.difference(self._coder_ganglia)
            self._coder_ganglia = all_coder_ganglia

        new_external_coder_ganglia = pset((coder, ganglion) for coder, ganglion in new_coder_ganglia
                                          if isinstance(ganglion, GanglionExternalBase))
        new_internal_coder_ganglia = new_coder_ganglia.difference(new_external_coder_ganglia)
        internal = (ganglion.adapt(coder, reactants=(partial(self._internal_reaction, ganglion),))
                    for coder, ganglion in new_internal_coder_ganglia)
        external_external = (ganglion.adapt(coder, reactants=(partial(self._external_external_reaction, ganglion),))
                             for coder, ganglion in new_external_coder_ganglia)
        external_internal = (ganglion.adapt(coder, decoded_reactants=(partial(self._external_internal_reaction, ganglion),))
                             for coder, ganglion in new_external_coder_ganglia)
        try:
            await asyncio.gather(*itertools.chain(internal, external_external, external_internal))
        except ValueError:
            # Got empty list, continue
            pass

    async def update_transmitter(self, coder: Coder):
        await self._update_coders(coder)

        return await self.inproc_ganglion.update_transmitter(coder)

    async def react(self, coder: Coder, reactants: Iterable[Reactant]):
        return await self.inproc_ganglion.react(coder, reactants)

    async def transmit(self, data):
        return await self.inproc_ganglion.transmit(data)

    async def adapt(self, coder: Coder, reactants: Optional[Iterable[Reactant]] = None):
        if reactants:
            await self.react(coder, reactants)

        return await self.update_transmitter(coder)
