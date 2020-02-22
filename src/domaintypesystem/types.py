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
from typing import TypeVar
from typing_extensions import Protocol

EncodedDataType = TypeVar('EncodedDataType')
UnencodedDataType = TypeVar('UnencodedDataType')


class EncoderProtocol(Protocol):
    def encode(self, s: UnencodedDataType): ...


class DecoderProtocol(Protocol):
    def decode(self, s: EncodedDataType): ...


class ReceptorProtocol(Protocol):
    async def activate(self, data: EncodedDataType): ...
