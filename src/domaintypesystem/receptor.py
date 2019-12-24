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
from codecs import Codec
from typing import Any, Callable, Generic

from domaintypesystem.types import EncodedDataType, UnencodedDataType


class DTSReceptorBase(ABC, Generic[EncodedDataType]):
    def __init__(self, _callable: Callable[[UnencodedDataType], Any]) -> None:
        self._callable = _callable

    @abstractmethod
    async def activate(self, data) -> None:
        pass


class DTSReceptor(DTSReceptorBase):
    def __init__(self, _callable: Callable[[UnencodedDataType], Any], codec: Codec) -> None:
        super().__init__(_callable)
        self._codec = codec

    async def activate(self, data: EncodedDataType) -> None:
        decoded, length = self._codec.decode(data)
        await self._callable(decoded)
