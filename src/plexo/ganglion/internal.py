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
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Type
from uuid import UUID

from pyrsistent import pdeque, pmap, pset
from pyrsistent.typing import PDeque, PMap, PSet

from plexo.exceptions import NeuronNotFound, SynapseExists, TransmitterNotFound
from plexo.neuron.neuron import Neuron
from plexo.receptor import create_receptor
from plexo.synapse.base import SynapseBase
from plexo.transmitter import create_transmitter
from plexo.typing import UnencodedSignal, Signal
from plexo.typing.transmitter import Transmitter
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class GanglionInternalBase(Ganglion, ABC):
    def __init__(self):
        self._tasks: PDeque = pdeque()

        self._synapses: PMap[str, SynapseBase] = pmap({})
        self._synapses_lock = asyncio.Lock()

        self._transmitters: PMap[Neuron, Transmitter] = pmap({})
        self._transmitters_lock = asyncio.Lock()

        self._type_neurons: PMap[Type, PSet[Neuron]] = pmap({})
        self._type_neurons_lock = asyncio.Lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    @abstractmethod
    async def _create_synapse_by_name(self, name: str) -> SynapseBase:
        ...

    @abstractmethod
    async def _create_synapse(self, neuron: Neuron[UnencodedSignal]) -> SynapseBase:
        ...

    async def get_synapse_by_name(self, name: str):
        if name not in self._synapses:
            try:
                return await self._create_synapse_by_name(name)
            except SynapseExists:
                pass

        return self._synapses[name]

    async def get_synapse(self, neuron: Neuron[UnencodedSignal]):
        name = neuron.name
        return await self.get_synapse_by_name(name)

    async def _update_type_neurons(self, neuron: Neuron[UnencodedSignal]):
        async with self._type_neurons_lock:
            try:
                type_neurons: PSet[Neuron[UnencodedSignal]] = self._type_neurons[
                    neuron.type
                ]
            except KeyError:
                type_neurons = pset()
            type_neurons = type_neurons.add(neuron)
            self._type_neurons = self._type_neurons.set(neuron.type, type_neurons)

    async def _create_transmitter(
        self, neuron: Neuron[UnencodedSignal], synapse: SynapseBase
    ):
        async with self._transmitters_lock:
            try:
                return self._transmitters[neuron]
            except KeyError:
                transmitter = create_transmitter((synapse,))
                self._transmitters = self._transmitters.set(neuron, transmitter)
                return transmitter

    async def create_transmitter(
        self, neuron: Neuron[UnencodedSignal], synapse: SynapseBase
    ):
        transmitter = await self._create_transmitter(neuron, synapse)

        await self._update_type_neurons(neuron)

        return transmitter

    async def update_transmitter(self, neuron: Neuron[UnencodedSignal]):
        synapse = await self.get_synapse(neuron)
        await self._create_transmitter(neuron, synapse)

        await self._update_type_neurons(neuron)

    async def _get_neurons_by_type(self, _type: Type):
        async with self._type_neurons_lock:
            try:
                return self._type_neurons[_type]
            except KeyError:
                raise NeuronNotFound(f"Neuron for {_type.__name__} does not exist.")

    async def _get_neurons(
        self, data: UnencodedSignal
    ) -> PSet[Neuron[UnencodedSignal]]:
        _type = type(data)
        return await self._get_neurons_by_type(_type)

    def _get_transmitter(self, neuron: Neuron[UnencodedSignal]):
        try:
            return self._transmitters[neuron]
        except KeyError:
            raise TransmitterNotFound(f"Transmitter for {neuron} does not exist.")

    async def _get_transmitters(self, data: Signal):
        try:
            neurons = await self._get_neurons(data)
        except NeuronNotFound:
            raise TransmitterNotFound(
                f"Transmitter for {type(data).__name__} does not exist."
            )
        return (self._get_transmitter(neuron) for neuron in neurons)

    async def react(
        self, neuron: Neuron[UnencodedSignal], reactants: Iterable[Reactant]
    ):
        synapse = await self.get_synapse(neuron)
        await synapse.update_receptors((create_receptor(reactants=reactants),))

    async def transmit(self, data: UnencodedSignal, reaction_id: Optional[UUID] = None):
        transmitters = await self._get_transmitters(data)

        return await asyncio.wait(
            [transmitter(data, reaction_id) for transmitter in transmitters]
        )

    async def adapt(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Optional[Iterable[Reactant]] = None,
    ):
        if reactants:
            await self.react(neuron, reactants)

        await self.update_transmitter(neuron)
