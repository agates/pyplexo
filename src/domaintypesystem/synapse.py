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
from asyncio import Lock, Queue
from collections import deque
from typing import Generic, Type, TypeVar

from domaintypesystem.receptor import DTSReceptorBase

EncodedDataType = TypeVar('EncodedDataType')


class DTSSynapse(ABC, Generic[EncodedDataType]):
    def __init__(self, name: str) -> None:
        self._name = name
        self._queue = Queue()
        self._receptors = deque()
        self._receptors_lock = Lock()

    @property
    def name(self) -> str:
        return self._name

    async def add_receptor(self, receptor: DTSReceptorBase):
        with self._receptors_lock:
            self._receptors.append(receptor)

    @abstractmethod
    async def pass_data(self, data: EncodedDataType) -> None:
        pass


class InProcessSynapse(DTSSynapse):
    async def pass_data(self, data: EncodedDataType) -> None:
        with self._receptors_lock:
            await asyncio.wait([receptor(data) for receptor in self._receptors])


def create_synapse(name: str, synapse_type: Type[DTSSynapse]) -> DTSSynapse:
    return synapse_type(name)
