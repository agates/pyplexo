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
from asyncio import Future
from typing import ByteString, Callable, Generic, Set, Tuple

from domaintypesystem.synapse import DTSSynapseBase, DTSSynapseInProcessBase
from domaintypesystem.typing import UnencodedDataType


class DTSTransmitterBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, synapse: DTSSynapseBase,
                 encoder: Callable[[UnencodedDataType], ByteString]) -> None:
        self._synapse = synapse
        self._encoder = encoder

    @abstractmethod
    async def transmit(self, data): ...


class DTSTransmitter(DTSTransmitterBase, Generic[UnencodedDataType]):
    async def transmit(self, data: UnencodedDataType) -> Tuple[Set[Future], Set[Future]]:
        encoded = self._encoder(data)
        return await self._synapse.shift(encoded)


class DTSTransmitterInProcessBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, synapse: DTSSynapseInProcessBase) -> None:
        self._synapse = synapse

    @abstractmethod
    async def transmit(self, data): ...


class DTSTransmitterInProcess(DTSTransmitterInProcessBase, Generic[UnencodedDataType]):
    async def transmit(self, data: UnencodedDataType) -> Tuple[Set[Future], Set[Future]]:
        return await self._synapse.shift(data)
