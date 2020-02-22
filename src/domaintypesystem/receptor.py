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
from typing import Any, Callable, Generic, Iterable, Tuple, Set

from pyrsistent import pvector

from domaintypesystem.types import EncodedDataType, UnencodedDataType, DecoderProtocol


class DTSReceptorBase(ABC, Generic[EncodedDataType, UnencodedDataType]):
    def __init__(self, _callables: Iterable[Callable[[UnencodedDataType], Any]], decoder: DecoderProtocol) -> None:
        self._callables = pvector(_callables)
        self._decoder = decoder

    @abstractmethod
    async def activate(self, data): ...


class DTSReceptor(DTSReceptorBase, Generic[EncodedDataType, UnencodedDataType]):
    async def activate(self, data: EncodedDataType) -> Tuple[Set[Future], Set[Future]]:
        decoded = self._decoder.decode(data)
        return await asyncio.wait([_callable(decoded) for _callable in self._callables])
