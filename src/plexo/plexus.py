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
from typing import Iterable, Optional, Set, Tuple
from uuid import UUID, uuid4
from weakref import WeakKeyDictionary

from pyrsistent import PSet, pset
from returns.curry import partial

from plexo.ganglion.external import GanglionExternalBase
from plexo.ganglion.inproc import GanglionInproc
from plexo.ganglion.internal import GanglionInternalBase
from plexo.neuron.neuron import Neuron
from plexo.typing import EncodedSignal, UnencodedSignal, Signal
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class Plexus(Ganglion):
    def __init__(self, ganglia: Iterable[Ganglion] = ()):
        ganglia = pset(ganglia)
        self.inproc_ganglion: GanglionInternalBase = GanglionInproc()

        self._external_ganglia = pset(
            ganglion
            for ganglion in ganglia
            if isinstance(ganglion, GanglionExternalBase)
        )
        self._external_ganglia_lock = asyncio.Lock()
        self._internal_ganglia = pset(
            ganglion
            for ganglion in ganglia
            if not isinstance(ganglion, GanglionExternalBase)
        )
        self._internal_ganglia = self._internal_ganglia.add(self.inproc_ganglion)
        self._internal_ganglia_lock = asyncio.Lock()

        self._neurons: PSet[Neuron] = pset()
        self._neurons_lock = asyncio.Lock()
        self._neuron_ganglia: PSet[Tuple[Neuron, Ganglion]] = pset()
        self._neuron_ganglia_lock = asyncio.Lock()

        self._reactions: WeakKeyDictionary[UUID, Set[Ganglion]] = WeakKeyDictionary()
        self._reaction_locks: WeakKeyDictionary[
            UUID, asyncio.Lock
        ] = WeakKeyDictionary()
        self._reaction_locks_lock = asyncio.Lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for ganglion in itertools.chain(
                self._internal_ganglia, self._external_ganglia
            ):
                ganglion.close()
        except RuntimeError:
            pass

    async def _internal_reaction(
        self,
        current: Ganglion,
        data: UnencodedSignal,
        reaction_id: Optional[UUID] = None,
    ):
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

            internal = (
                ganglion.transmit(data, reaction_id)
                for ganglion in self._internal_ganglia - self._reactions[reaction_id]
            )
            external = (
                ganglion.transmit_encode(data, reaction_id)
                for ganglion in self._external_ganglia - self._reactions[reaction_id]
            )

        try:
            await asyncio.gather(*itertools.chain(internal, external))
        except ValueError:
            # Got empty list, continue
            pass

    async def _external_internal_reaction(
        self,
        current: GanglionExternalBase,
        data: UnencodedSignal,
        reaction_id: Optional[UUID] = None,
    ):
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

            internal = (
                ganglion.transmit(data, reaction_id)
                for ganglion in self._internal_ganglia - self._reactions[reaction_id]
            )

        try:
            await asyncio.gather(*internal)
        except ValueError:
            # Got empty list, continue
            pass

    async def _external_external_reaction(
        self,
        current: GanglionExternalBase,
        data: EncodedSignal,
        reaction_id: Optional[UUID] = None,
    ):
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

            external = (
                ganglion.transmit(data, reaction_id)
                for ganglion in self._external_ganglia - self._reactions[reaction_id]
            )

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

        await self._update_neuron_ganglia()

    async def _update_neurons(self, neuron: Neuron):
        async with self._neurons_lock:
            self._neurons = self._neurons.add(neuron)

        await self._update_neuron_ganglia()

    async def _update_neuron_ganglia(self):
        all_ganglia = itertools.chain(self._internal_ganglia, self._external_ganglia)
        all_neuron_ganglia = pset(itertools.product(self._neurons, all_ganglia))
        async with self._neuron_ganglia_lock:
            new_neuron_ganglia = all_neuron_ganglia.difference(self._neuron_ganglia)
            self._neuron_ganglia = all_neuron_ganglia

        new_external_neuron_ganglia = pset(
            (neuron, ganglion)
            for neuron, ganglion in new_neuron_ganglia
            if isinstance(ganglion, GanglionExternalBase)
        )
        new_internal_neuron_ganglia = new_neuron_ganglia.difference(
            new_external_neuron_ganglia
        )
        internal = (
            ganglion.adapt(
                neuron, reactants=(partial(self._internal_reaction, ganglion),)
            )
            for neuron, ganglion in new_internal_neuron_ganglia
        )
        external_external = (
            ganglion.adapt(
                neuron, reactants=(partial(self._external_external_reaction, ganglion),)
            )
            for neuron, ganglion in new_external_neuron_ganglia
        )
        external_internal = (
            ganglion.adapt(
                neuron,
                decoded_reactants=(
                    partial(self._external_internal_reaction, ganglion),
                ),
            )
            for neuron, ganglion in new_external_neuron_ganglia
        )
        try:
            await asyncio.gather(
                *itertools.chain(internal, external_external, external_internal)
            )
        except ValueError:
            # Got empty list, continue
            pass

    async def update_transmitter(self, neuron: Neuron):
        await self._update_neurons(neuron)

        return await self.inproc_ganglion.update_transmitter(neuron)

    async def react(self, neuron: Neuron, reactants: Iterable[Reactant]):
        return await self.inproc_ganglion.react(neuron, reactants)

    async def transmit(self, data: Signal, reaction_id: Optional[UUID] = None):
        return await self.inproc_ganglion.transmit(data, reaction_id)

    async def adapt(
        self, neuron: Neuron, reactants: Optional[Iterable[Reactant]] = None
    ):
        if reactants:
            await self.react(neuron, reactants)

        await self.update_transmitter(neuron)
