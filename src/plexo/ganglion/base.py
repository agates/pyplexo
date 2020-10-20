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
from abc import ABC, abstractmethod
from typing import Type, Optional

from pyrsistent import pmap, pdeque, PDeque, PMap,  pset

from plexo.coder import Coder
from plexo.exceptions import SynapseExists, TransmitterNotFound, CoderNotFound
from plexo.transmitter import create_transmitter, create_encoder_transmitter
from plexo.typing import U, DecodedReactant, Reactant
from plexo.synapse.base import SynapseBase
from plexo.receptor import create_receptor, create_decoder_receptor


class GanglionBase(ABC):
    def __init__(self, loop=None):
        self._tasks: PDeque = pdeque()

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._synapses: PMap = pmap()
        self._synapses_lock = asyncio.Lock()

        self._encoder_transmitters: PMap = pmap()
        self._encoder_transmitters_lock = asyncio.Lock()
        self._transmitters: PMap = pmap()
        self._transmitters_lock = asyncio.Lock()

        self._type_coders: PMap = pmap()
        self._type_coders_lock = asyncio.Lock()

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
    async def create_synapse_by_name(self, name: str): ...

    @abstractmethod
    async def create_synapse(self, coder: Coder): ...

    async def get_synapse_by_name(self, name: str):
        if name not in self._synapses:
            try:
                return await self.create_synapse_by_name(name)
            except SynapseExists:
                pass

        return self._synapses[name]

    async def get_synapse(self, coder: Coder):
        name = coder.full_name()
        return await self.get_synapse_by_name(name)

    async def update_type_coders(self, coder: Coder):
        async with self._type_coders_lock:
            try:
                type_coders = self._type_coders[coder.type]
            except KeyError:
                type_coders = pset()
            type_coders = type_coders.add(coder)
            self._type_coders = self._type_coders.set(coder.type, type_coders)

    async def _create_encoder_transmitter(self, coder: Coder, synapse: SynapseBase):
        async with self._encoder_transmitters_lock:
            try:
                return self._encoder_transmitters[coder]
            except KeyError:
                encoder_transmitter = create_encoder_transmitter((synapse,), coder.encoder, loop=self._loop)
                self._encoder_transmitters = self._encoder_transmitters.set(coder, encoder_transmitter)
                return encoder_transmitter

    async def create_encoder_transmitter(self, coder: Coder, synapse: SynapseBase):
        encoder_transmitter = self._create_encoder_transmitter(coder, synapse)

        await self.update_type_coders(coder)

        return encoder_transmitter

    async def _create_transmitter(self, coder: Coder, synapse: SynapseBase):
        async with self._transmitters_lock:
            try:
                return self._transmitters[coder]
            except KeyError:
                transmitter = create_transmitter((synapse,), loop=self._loop)
                self._transmitters = self._transmitters.set(coder, transmitter)
                return transmitter

    async def create_transmitter(self, coder: Coder, synapse: SynapseBase):
        transmitter = await self._create_transmitter(coder, synapse)

        await self.update_type_coders(coder)

        return transmitter

    async def update_transmitter(self, coder: Coder):
        synapse = await self.get_synapse(coder)
        await asyncio.gather(self._create_encoder_transmitter(coder, synapse),
                             self._create_transmitter(coder, synapse)
                             )

        await self.update_type_coders(coder)

    async def get_coders_by_type(self, _type: Type):
        async with self._type_coders_lock:
            try:
                return self._type_coders[_type]
            except KeyError:
                raise CoderNotFound("Coder for {} does not exist.".format(_type.__name__))

    async def get_coders(self, data: U):
        _type = type(data)
        return await self.get_coders_by_type(_type)

    def get_encoder_transmitter(self, coder: Coder):
        try:
            return self._encoder_transmitters[coder]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(coder))

    async def get_encoder_transmitters(self, data: U):
        try:
            coders = await self.get_coders(data)
        except CoderNotFound:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type(data).__name__))
        return (self.get_encoder_transmitter(coder) for coder in coders)

    def get_transmitter(self, coder: Coder):
        try:
            return self._transmitters[coder]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(coder))

    async def get_transmitters(self, data: U):
        try:
            coders = await self.get_coders(data)
        except CoderNotFound:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type(data).__name__))
        return (self.get_transmitter(coder) for coder in coders)

    async def react_decode(self, coder: Coder, reactant: DecodedReactant):
        synapse = await self.get_synapse(coder)
        await synapse.update_receptors(
            (create_decoder_receptor(reactants=(reactant,), decoder=coder.decoder, loop=self._loop),)
        )

    async def react(self, coder: Coder, reactant: Reactant):
        synapse = await self.get_synapse(coder)
        await synapse.update_receptors(
            (create_receptor(reactants=(reactant,), loop=self._loop),)
        )

    async def transmit_encode(self, data: U):
        encoder_transmitters = await self.get_encoder_transmitters(data)

        return await asyncio.wait(
            [encoder_transmitter(data) for encoder_transmitter in encoder_transmitters],
            loop=self._loop)

    async def transmit(self, data: U):
        transmitters = await self.get_transmitters(data)

        return await asyncio.wait(
            [transmitter(data) for transmitter in transmitters],
            loop=self._loop)

    async def adapt(self, coder: Coder,
                    reactant: Optional[Reactant] = None,
                    decoded_reactant: Optional[DecodedReactant] = None):
        if reactant:
            await self.react(coder, reactant)
        if decoded_reactant:
            await self.react_decode(coder, decoded_reactant)

        return await self.update_transmitter(coder)
