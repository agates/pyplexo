#  pyplexo
#  Copyright © 2018-2022  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Type
from uuid import UUID

from pyrsistent import pdeque, pmap, pset
from pyrsistent.typing import PDeque, PMap, PSet

from plexo.exceptions import (
    NeuronNotFound,
    SynapseExists,
    TransmitterNotFound,
    NeuronNotAvailable,
)
from plexo.neuron.neuron import Neuron
from plexo.transmitter import create_transmitter
from plexo.typing import UnencodedSignal
from plexo.typing.synapse import SynapseInternal
from plexo.typing.transmitter import Transmitter
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class GanglionInternalBase(Ganglion, ABC):
    def __init__(
        self,
        relevant_neurons: Iterable[Neuron] = (),
        ignored_neurons: Iterable[Neuron] = (),
        allowed_codecs: Iterable[Type] = (),
    ):
        self._tasks: PDeque = pdeque()

        self._synapses: PMap[str, SynapseInternal] = pmap({})
        self._synapses_lock = asyncio.Lock()

        self._transmitters: PMap[Neuron, Transmitter] = pmap({})
        self._transmitters_lock = asyncio.Lock()

        # There can be multiple Neurons per type because a single type
        # may have multiple different namespaces
        self._type_neurons: PMap[Type, PSet[Neuron]] = pmap({})
        self._type_neurons_lock = asyncio.Lock()

        # IF we have a type string we know it includes a namespace,
        # so we only map it to one Neuron
        self._name_neurons: PMap[str, Neuron] = pmap({})
        self._name_neurons_lock = asyncio.Lock()

        # This is a set of neurons that the Ganglion will handle
        self._relevant_neurons: PSet[Neuron] = pset(relevant_neurons)

        # This is a set of neurons that the Ganglion will ignore
        self._ignored_neurons: PSet[Neuron] = pset(ignored_neurons)

        self._allowed_codecs: PSet[Type] = pset(allowed_codecs)

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
    async def _create_synapse_by_name(
        self, neuron: Neuron[UnencodedSignal], name: str
    ) -> SynapseInternal[UnencodedSignal]:
        ...

    @abstractmethod
    async def _create_synapse(
        self, neuron: Neuron[UnencodedSignal]
    ) -> SynapseInternal[UnencodedSignal]:
        ...

    async def get_synapse_by_name(
        self, name: str, neuron: Optional[Neuron[UnencodedSignal]] = None
    ) -> SynapseInternal[UnencodedSignal]:
        if name not in self._synapses:
            try:
                return await self._create_synapse_by_name(
                    neuron or await self._get_neuron_by_name(name), name
                )
            except SynapseExists:
                pass

        return self._synapses[name]

    async def get_synapse(self, neuron: Neuron[UnencodedSignal]):
        name = neuron.name
        return await self.get_synapse_by_name(name, neuron)

    async def _update_name_neurons(self, neuron: Neuron[UnencodedSignal]):
        async with self._name_neurons_lock:
            if neuron.name not in self._name_neurons:
                self._name_neurons = self._name_neurons.set(neuron.name, neuron)

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
        self, neuron: Neuron[UnencodedSignal], synapse: SynapseInternal[UnencodedSignal]
    ):
        async with self._transmitters_lock:
            try:
                return self._transmitters[neuron]
            except KeyError:
                transmitter = create_transmitter(synapse)
                self._transmitters = self._transmitters.set(neuron, transmitter)
                return transmitter

    async def create_transmitter(
        self, neuron: Neuron[UnencodedSignal], synapse: SynapseInternal[UnencodedSignal]
    ):
        transmitter = await self._create_transmitter(neuron, synapse)

        await self._update_name_neurons(neuron)
        await self._update_type_neurons(neuron)

        return transmitter

    def capable(self, neuron: Neuron[UnencodedSignal]) -> bool:
        if len(self._relevant_neurons) > 0 and neuron not in self._relevant_neurons:
            return False

        if len(self._ignored_neurons) > 0 and neuron in self._ignored_neurons:
            return False

        if (
            len(self._allowed_codecs) > 0
            and type(neuron.codec) not in self._allowed_codecs
        ):
            return False

        return True

    async def update_transmitter(self, neuron: Neuron[UnencodedSignal]):
        synapse = await self.get_synapse(neuron)
        await self._create_transmitter(neuron, synapse)

        await self._update_name_neurons(neuron)
        await self._update_type_neurons(neuron)

    async def _get_neuron_by_name(self, name: str):
        async with self._name_neurons_lock:
            try:
                return self._name_neurons[name]
            except KeyError:
                raise NeuronNotFound(f"Neuron for {name} does not exist.")

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

    async def _get_transmitters(
        self,
        data: UnencodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
    ) -> Iterable[Transmitter]:
        if neuron is not None:
            return (self._get_transmitter(neuron),)
        else:
            try:
                neurons: PSet[Neuron[UnencodedSignal]] = await self._get_neurons(data)
            except (NeuronNotAvailable, NeuronNotFound):
                raise TransmitterNotFound(
                    f"Transmitter for {type(data).__name__} does not exist."
                )
            return (self._get_transmitter(neuron) for neuron in neurons)

    async def react(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Iterable[Reactant[UnencodedSignal]],
    ):
        synapse = await self.get_synapse(neuron)
        await synapse.add_reactants(reactants)

    async def transmit(
        self,
        data: UnencodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        transmitters = await self._get_transmitters(data, neuron)

        return await asyncio.gather(
            *(transmitter(data, neuron, reaction_id) for transmitter in transmitters)
        )

    async def adapt(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Optional[Iterable[Reactant[UnencodedSignal]]] = None,
    ):
        if not self.capable(neuron):
            logging.warning(
                f"GanglionInternalBase:adapt not capable of adapting to Neuron {neuron}"
            )
            return

        if reactants:
            await self.react(neuron, reactants)

        await self.update_transmitter(neuron)
