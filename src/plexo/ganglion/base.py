#  pyplexo
#   Copyright (C) 2020  Alecks Gates
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
from abc import ABC, abstractmethod
from typing import Type

from pyrsistent import pmap, pdeque, PDeque, PMap

from plexo.exceptions import SynapseExists, TransmitterNotFound
from plexo.transmitter import create_transmitter, create_encoder_transmitter
from plexo.typing import U, DecodedReactant, Decoder, Encoder, Reactant
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
    async def create_synapse_by_name(self, type_name: str): ...

    @abstractmethod
    async def create_synapse_by_type(self, _type: Type): ...

    async def get_synapse_by_name(self, type_name: str):
        type_name_bytes = type_name.encode("UTF-8")
        if type_name_bytes not in self._synapses:
            try:
                return await self.create_synapse_by_name(type_name)
            except SynapseExists:
                pass

        return self._synapses[type_name_bytes]

    async def get_synapse_by_type(self, _type: Type):
        type_name = _type.__name__
        return await self.get_synapse_by_name(type_name)

    async def get_synapse_by_data_class(self, data_class: object):
        _type = type(data_class)
        return await self.get_synapse_by_type(_type)

    async def create_encode_transmitter(self, type_name: str, synapse: SynapseBase, encoder: Encoder):
        encoder_transmitter = create_encoder_transmitter((synapse,), encoder, loop=self._loop)

        async with self._encoder_transmitters_lock:
            self._encoder_transmitters = self._encoder_transmitters.set(type_name, encoder_transmitter)

        return encoder_transmitter

    async def create_transmitter(self, type_name: str, synapse: SynapseBase):
        transmitter = create_transmitter((synapse,), loop=self._loop)

        async with self._transmitters_lock:
            self._transmitters = self._transmitters.set(type_name, transmitter)

        return transmitter

    async def update_transmitter_by_name(self, type_name: str, encoder: Encoder):
        synapse = await self.get_synapse_by_name(type_name)
        return asyncio.gather(self.create_encode_transmitter(type_name, synapse, encoder),
                              self.create_transmitter(type_name, synapse)
                              )

    async def update_transmitter_by_type(self, _type: Type, encoder: Encoder):
        type_name = _type.__name__
        synapse = await self.get_synapse_by_type(_type)
        return asyncio.gather(await self.create_encode_transmitter(type_name, synapse, encoder),
                              self.create_transmitter(type_name, synapse)
                              )

    def get_encoder_transmitter(self, data: U):
        type_name = type(data).__name__
        try:
            return self._encoder_transmitters[type_name]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type_name))

    def get_transmitter(self, data: U):
        type_name = type(data).__name__
        try:
            return self._transmitters[type_name]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type_name))

    async def react_decode_by_data_class(self, data_class: object, reactant: DecodedReactant, decoder: Decoder):
        synapse = await self.get_synapse_by_data_class(data_class)
        await synapse.update_receptors(
            (create_decoder_receptor(reactants=(reactant,), decoder=decoder, loop=self._loop),)
        )

    async def react_by_data_class(self, data_class: object, reactant: Reactant):
        synapse = await self.get_synapse_by_data_class(data_class)
        await synapse.update_receptors(
            (create_receptor(reactants=(reactant,), loop=self._loop),)
        )

    async def transmit_encode(self, data: U):
        encoder_transmitter = self.get_encoder_transmitter(data)

        return await encoder_transmitter(data)

    async def transmit(self, data: U):
        transmitter = self.get_transmitter(data)

        return await transmitter(data)
