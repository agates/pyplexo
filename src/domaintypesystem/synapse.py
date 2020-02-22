#  domain-type-system
#   Copyright (C) 2019  Alecks Gates
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
from abc import ABC, abstractmethod
import asyncio
from asyncio import Future
from typing import Iterable, Set, Tuple, Generic

from pyrsistent import pvector

from domaintypesystem.types import EncodedDataType, ReceptorProtocol


class DTSSynapseBase(ABC):
    def __init__(self, receptors: Iterable[ReceptorProtocol] = ()) -> None:
        self._receptors = pvector(receptors)
        self._receptors_lock = asyncio.Lock()

    async def add_receptor(self, receptor: ReceptorProtocol) -> None:
        async with self._receptors_lock:
            self._receptors = self._receptors.append(receptor)

    @abstractmethod
    async def pass_data(self, data): ...


class DTSInProcessSynapse(DTSSynapseBase, Generic[EncodedDataType]):
    async def pass_data(self, data: EncodedDataType) -> Tuple[Set[Future], Set[Future]]:
        async with self._receptors_lock:
            return await asyncio.wait([receptor.activate(data) for receptor in self._receptors])
