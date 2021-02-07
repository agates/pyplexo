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
from typing import Iterable, Optional

from pyrsistent import  pset, PSet
from plexo.ganglion.internal import GanglionInternalBase
from returns.curry import partial

from plexo.coder import Coder
from plexo.ganglion.external import GanglionExternalBase
from plexo.ganglion.inproc import GanglionInproc
from plexo.typing import D, E, U
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class Plexus(Ganglion):
    def __init__(self, ganglia: Iterable[Ganglion] = (), loop=None):
        ganglia = pset(ganglia)
        self.inproc_ganglion: GanglionInternalBase = GanglionInproc(loop=loop)

        self._external_ganglia: PSet = pset(ganglion for ganglion in ganglia
                                            if isinstance(ganglion, GanglionExternalBase))
        self._external_ganglia_lock = asyncio.Lock()
        self._internal_ganglia: PSet = pset(ganglion for ganglion in ganglia
                                            if not isinstance(ganglion, GanglionExternalBase))
        self._internal_ganglia = self._internal_ganglia.add(self.inproc_ganglion)
        self._internal_ganglia_lock = asyncio.Lock()

        self._coders: PSet = pset()
        self._coders_lock = asyncio.Lock()
        self._coder_ganglia: PSet = pset()
        self._coder_ganglia_lock = asyncio.Lock()

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

    async def _internal_reaction(self, current: Ganglion, data: D, source: Ganglion):
        internal = (ganglion.transmit(data) for ganglion in self._internal_ganglia - {current, source})
        external = (ganglion.transmit_encode(data) for ganglion in self._external_ganglia - {source})
        try:
            await asyncio.gather(*itertools.chain(internal, external))
        except ValueError:
            # Got empty list, continue
            pass

    async def _external_internal_reaction(self, data: D, source: Ganglion):
        try:
            await asyncio.gather(*(ganglion.transmit(data) for ganglion in self._internal_ganglia - {source}))
        except ValueError:
            # Got empty list, continue
            pass

    async def _external_external_reaction(self, current: GanglionExternalBase, data: E, source: Ganglion):
        try:
            await asyncio.gather(*(ganglion.transmit(data) for ganglion in self._external_ganglia - {current, source}))
        except ValueError:
            # Got empty list, continue
            pass

    async def bridge_ganglion(self, ganglion: Ganglion):
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
        internal = (ganglion.adapt(coder, reactant=partial(self._internal_reaction, ganglion))
                    for coder, ganglion in new_internal_coder_ganglia)
        external_external = (ganglion.adapt(coder, reactant=partial(self._external_external_reaction, ganglion))
                             for coder, ganglion in new_external_coder_ganglia)
        external_internal = (ganglion.adapt(coder, decoded_reactant=self._external_internal_reaction)
                             for coder, ganglion in new_external_coder_ganglia)
        try:
            await asyncio.gather(*itertools.chain(internal, external_external, external_internal))
        except ValueError:
            # Got empty list, continue
            pass

    async def update_transmitter(self, coder: Coder):
        await self._update_coders(coder)

        return await self.inproc_ganglion.update_transmitter(coder)

    async def react(self, coder: Coder, reactant: Reactant):
        return await self.inproc_ganglion.react(coder, reactant)

    async def transmit(self, data: U): # pyright: reportInvalidTypeVarUse=false
        return await self.inproc_ganglion.transmit(data)

    async def adapt(self, coder: Coder, reactant: Optional[Reactant] = None):
        if reactant:
            await self.react(coder, reactant)

        return await self.update_transmitter(coder)
