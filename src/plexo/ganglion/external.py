#  pyplexo
#  Copyright © 2018-2023  Alecks Gates
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

from pyrsistent import pmap, pdeque, pset
from pyrsistent.typing import PMap, PSet, PDeque

from plexo.exceptions import (
    NeuronNotFound,
    TransmitterNotFound,
    SynapseExists,
    NeuronNotAvailable,
)
from plexo.neuron.neuron import Neuron
from plexo.transmitter import (
    create_external_encoder_transmitter,
    create_external_transmitter,
)
from plexo.typing import UnencodedType, Signal, EncodedType
from plexo.typing.ganglion import Ganglion
from plexo.typing.synapse import SynapseExternal
from plexo.typing.transmitter import Transmitter, ExternalTransmitter
from plexo.typing.reactant import Reactant, RawReactant


class GanglionExternalBase(Ganglion, ABC):
    def __init__(
        self,
        relevant_neurons: Iterable[Neuron] = (),
        ignored_neurons: Iterable[Neuron] = (),
        allowed_codecs: Iterable[Type] = (),
    ):
        self._tasks: PDeque = pdeque()

        self._synapses: PMap[str, SynapseExternal] = pmap({})
        self._synapses_lock = asyncio.Lock()

        self._transmitters: PMap[Neuron, Transmitter] = pmap({})
        self._transmitters_lock = asyncio.Lock()

        self._external_transmitters: PMap[Neuron, ExternalTransmitter] = pmap({})
        self._external_transmitters_lock = asyncio.Lock()

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
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            wait_coro = asyncio.wait(
                self._tasks, timeout=10, return_when=asyncio.ALL_COMPLETED
            )
            try:
                loop = asyncio.get_running_loop()

                future = asyncio.run_coroutine_threadsafe(wait_coro, loop)
                # This is broken, pending https://bugs.python.org/issue42130
                future.result(10)
            except RuntimeError:
                asyncio.run(wait_coro)
            except TimeoutError:
                pass
            finally:
                self._tasks = pdeque()

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    @abstractmethod
    async def _create_synapse_by_name(
        self, neuron: Neuron[UnencodedType], name: str
    ) -> SynapseExternal[UnencodedType]:
        ...

    @abstractmethod
    async def _create_synapse(
        self, neuron: Neuron[UnencodedType]
    ) -> SynapseExternal[UnencodedType]:
        ...

    async def get_synapse_by_name(
        self, name: str, neuron: Optional[Neuron[UnencodedType]] = None
    ) -> SynapseExternal[UnencodedType]:
        if name not in self._synapses:
            try:
                return await self._create_synapse_by_name(
                    neuron or await self._get_neuron_by_name(name), name
                )
            except SynapseExists:
                pass

        return self._synapses[name]

    async def get_synapse(self, neuron: Neuron[UnencodedType]):
        name = neuron.name
        return await self.get_synapse_by_name(name, neuron)

    async def _update_name_neurons(self, neuron: Neuron[UnencodedType]):
        async with self._name_neurons_lock:
            if neuron.name not in self._name_neurons:
                self._name_neurons = self._name_neurons.set(neuron.name, neuron)

    async def _create_external_transmitter(
        self, neuron: Neuron[UnencodedType], synapse: SynapseExternal[UnencodedType]
    ):
        async with self._external_transmitters_lock:
            try:
                return self._external_transmitters[neuron]
            except KeyError:
                external_transmitter = create_external_transmitter(synapse)
                self._external_transmitters = self._external_transmitters.set(
                    neuron, external_transmitter
                )
                return external_transmitter

    async def create_external_transmitter(
        self, neuron: Neuron[UnencodedType], synapse: SynapseExternal[UnencodedType]
    ):
        external_transmitter = await self._create_external_transmitter(neuron, synapse)

        await self._update_name_neurons(neuron)

        return external_transmitter

    async def _create_transmitter(
        self, neuron: Neuron[UnencodedType], synapse: SynapseExternal[UnencodedType]
    ):
        async with self._transmitters_lock:
            try:
                return self._transmitters[neuron]
            except KeyError:
                transmitter = create_external_encoder_transmitter(
                    synapse, neuron.encode
                )
                self._transmitters = self._transmitters.set(neuron, transmitter)
                return transmitter

    async def create_transmitter(
        self, neuron: Neuron[UnencodedType], synapse: SynapseExternal[UnencodedType]
    ):
        encoder_transmitter = self._create_transmitter(neuron, synapse)

        return encoder_transmitter

    def capable(self, neuron: Neuron[UnencodedType]) -> bool:
        if len(self._relevant_neurons) > 0 and neuron not in self._relevant_neurons:
            return False

        if len(self._ignored_neurons) > 0 and neuron in self._ignored_neurons:
            return False
        # issubclass()

        if (
            len(self._allowed_codecs) > 0
            and type(neuron.codec) not in self._allowed_codecs
        ):
            return False

        return True

    async def update_transmitter(self, neuron: Neuron[UnencodedType]):
        synapse = await self.get_synapse(neuron)
        await asyncio.gather(
            self._create_transmitter(neuron, synapse),
            self._create_external_transmitter(neuron, synapse),
        )

    async def _get_neuron_by_name(self, name: str):
        async with self._name_neurons_lock:
            try:
                return self._name_neurons[name]
            except KeyError:
                raise NeuronNotFound(f"Neuron for {name} does not exist.")

    def _get_external_transmitter(self, neuron: Neuron[UnencodedType]):
        try:
            return self._external_transmitters[neuron]
        except KeyError:
            raise TransmitterNotFound(f"Transmitter for {neuron} does not exist.")

    async def _get_external_transmitters(
        self,
        neuron: Neuron[UnencodedType],
    ) -> Iterable[ExternalTransmitter]:
        return (self._get_external_transmitter(neuron),)

    def _get_transmitter(self, neuron: Neuron[UnencodedType]):
        try:
            return self._transmitters[neuron]
        except KeyError:
            raise TransmitterNotFound(f"Transmitter for {neuron} does not exist.")

    async def _get_transmitters(
        self,
        neuron: Neuron[UnencodedType],
    ) -> Iterable[Transmitter]:
        return (self._get_transmitter(neuron),)

    async def react(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Iterable[Reactant[UnencodedType]],
    ):
        synapse = await self.get_synapse(neuron)
        await synapse.add_reactants(reactants)

    async def react_raw(
        self,
        neuron: Neuron[UnencodedType],
        raw_reactants: Iterable[RawReactant[UnencodedType]],
    ):
        synapse = await self.get_synapse(neuron)
        await synapse.add_raw_reactants(raw_reactants)

    async def transmit_encoded(
        self,
        data: EncodedType,
        neuron: Neuron[UnencodedType],
        reaction_id: Optional[UUID] = None,
    ):
        external_transmitters = await self._get_external_transmitters(neuron)

        return await asyncio.gather(
            *(
                external_transmitter(data, reaction_id)
                for external_transmitter in external_transmitters
            )
        )

    async def transmit(
        self,
        data: UnencodedType,
        neuron: Neuron[UnencodedType],
        reaction_id: Optional[UUID] = None,
    ):
        transmitters = await self._get_transmitters(neuron)

        return await asyncio.gather(
            *(transmitter(data, reaction_id) for transmitter in transmitters),
        )

    async def adapt(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Optional[Iterable[Reactant[UnencodedType]]] = None,
        raw_reactants: Optional[Iterable[RawReactant[UnencodedType]]] = None,
    ):
        if not self.capable(neuron):
            logging.warning(
                f"GanglionExternalBase:adapt not capable of adapting to Neuron {neuron}"
            )
            return

        if reactants:
            await self.react(neuron, reactants)

        if raw_reactants:
            await self.react_raw(neuron, raw_reactants)

        await self.update_transmitter(neuron)
