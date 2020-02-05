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
from asyncio import Lock, Future
from collections import deque
from typing import Generic, Iterable, Tuple, Set

from domaintypesystem.receptor import DTSReceptorBase
from domaintypesystem.types import EncodedDataType, UnencodedDataType


class DTSSynapseBase(ABC, Generic[EncodedDataType]):
    def __init__(self, receptors: Iterable[DTSReceptorBase] = ()) -> None:
        self._receptors = deque(receptors)
        self._receptors_lock = Lock()

    async def add_receptor(self, receptor: DTSReceptorBase[EncodedDataType, UnencodedDataType]) -> None:
        async with self._receptors_lock:
            self._receptors.append(receptor)

    @abstractmethod
    async def pass_data(self, data: EncodedDataType) -> Tuple[Set[Future], Set[Future]]: ...


class DTSInProcessSynapse(DTSSynapseBase):
    async def pass_data(self, data: EncodedDataType) -> Tuple[Set[Future], Set[Future]]:
        async with self._receptors_lock:
            return await asyncio.wait([receptor.activate(data) for receptor in self._receptors])
