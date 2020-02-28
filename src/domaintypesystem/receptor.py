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
from typing import Any, ByteString, Callable, Generic, Iterable, Set, Tuple

from pyrsistent import pvector

from domaintypesystem.typing import UnencodedDataType


class DTSReceptorBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, reactants: Iterable[Callable[[UnencodedDataType], Any]],
                 decoder: Callable[[ByteString], UnencodedDataType],
                 loop=None) -> None:
        self.reactants = pvector(reactants)
        self.reactants_lock = asyncio.Lock()
        self._decoder = decoder

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

    @abstractmethod
    async def activate(self, data: ByteString): ...

    async def add_reactant(self, reactant: Callable[[UnencodedDataType], Any]) -> None:
        async with self.reactants_lock:
            self.reactants = self.reactants.append(reactant)


class DTSReceptor(DTSReceptorBase, Generic[UnencodedDataType]):
    async def activate(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        decoded = self._decoder(data)
        async with self.reactants_lock:
            return await asyncio.wait([reactant(decoded) for reactant in self.reactants], loop=self._loop)


class DTSReceptorInProcessBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, reactants: Iterable[Callable[[UnencodedDataType], Any]],
                 loop=None) -> None:
        self.reactants = pvector(reactants)
        self.reactants_lock = asyncio.Lock()

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

    @abstractmethod
    async def activate(self, data: Any): ...

    async def add_reactant(self, reactant: Callable[[UnencodedDataType], Any]) -> None:
        async with self.reactants_lock:
            self.reactants = self.reactants.append(reactant)


class DTSReceptorInProcess(DTSReceptorInProcessBase, Generic[UnencodedDataType]):
    async def activate(self, data: Any) -> Tuple[Set[Future], Set[Future]]:
        async with self.reactants_lock:
            return await asyncio.wait([reactant(data) for reactant in self.reactants], loop=self._loop)
