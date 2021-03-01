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
from typing import Any, Callable, Iterable, Type, Optional
from uuid import UUID

from pyrsistent import pdeque, pmap, pset
from pyrsistent.typing import PDeque, PMap, PSet

from plexo.coder import Coder
from plexo.exceptions import SynapseExists, CoderNotFound, TransmitterNotFound
from plexo.receptor import create_receptor
from plexo.synapse.base import SynapseBase
from plexo.transmitter import create_transmitter
from plexo.typing import U
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class GanglionInternalBase(Ganglion, ABC):
    def __init__(self, loop=None):
        self._tasks: PDeque = pdeque()

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._synapses: PMap[str, SynapseBase] = pmap({})
        self._synapses_lock = asyncio.Lock()

        self._transmitters: PMap[Coder, Callable[[Any, Optional[UUID]], Any]] = pmap({})
        self._transmitters_lock = asyncio.Lock()

        self._type_coders: PMap[Type, PSet[Coder]] = pmap({})
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
    async def _create_synapse_by_name(self, name: str) -> SynapseBase: ...

    @abstractmethod
    async def _create_synapse(self, coder: Coder) -> SynapseBase: ...

    async def get_synapse_by_name(self, name: str):
        if name not in self._synapses:
            try:
                return await self._create_synapse_by_name(name)
            except SynapseExists:
                pass

        return self._synapses[name]

    async def get_synapse(self, coder: Coder):
        name = coder.full_name()
        return await self.get_synapse_by_name(name)

    async def _update_type_coders(self, coder: Coder):
        async with self._type_coders_lock:
            try:
                type_coders: PSet[Coder] = self._type_coders[coder.type]
            except KeyError:
                type_coders = pset()
            type_coders = type_coders.add(coder)
            self._type_coders = self._type_coders.set(coder.type, type_coders)

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

        await self._update_type_coders(coder)

        return transmitter

    async def update_transmitter(self, coder: Coder):
        synapse = await self.get_synapse(coder)
        await self._create_transmitter(coder, synapse)

        await self._update_type_coders(coder)

    async def _get_coders_by_type(self, _type: Type):
        async with self._type_coders_lock:
            try:
                return self._type_coders[_type]
            except KeyError:
                raise CoderNotFound("Coder for {} does not exist.".format(_type.__name__))

    async def _get_coders(self, data: U) -> PSet[Coder[U]]:
        _type = type(data)
        return await self._get_coders_by_type(_type)

    def _get_transmitter(self, coder: Coder):
        try:
            return self._transmitters[coder]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(coder))

    async def _get_transmitters(self, data: U) -> Iterable[Callable[[U, Optional[UUID]], Any]]:
        try:
            coders = await self._get_coders(data)
        except CoderNotFound:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type(data).__name__))
        return (self._get_transmitter(coder) for coder in coders)

    async def react(self, coder: Coder, reactants: Iterable[Reactant]):
        synapse = await self.get_synapse(coder)
        await synapse.update_receptors(
            (create_receptor(reactants=reactants, loop=self._loop),)
        )

    async def transmit(self, data, reaction_id: Optional[UUID] = None):
        transmitters = await self._get_transmitters(data)

        return await asyncio.gather(
            *(transmitter(data, reaction_id) for transmitter in transmitters),
            loop=self._loop)

    async def adapt(self, coder: Coder, reactants: Optional[Iterable[Reactant]] = None):
        if reactants:
            await self.react(coder, reactants)

        return await self.update_transmitter(coder)
