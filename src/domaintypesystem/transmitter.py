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
from typing import Generic

from domaintypesystem.synapse import DTSSynapseBase
from domaintypesystem.types import UnencodedDataType


class DTSTransmitterBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, synapse: DTSSynapseBase) -> None:
        self._synapse = synapse

    @property
    def synapse(self) -> DTSSynapseBase:
        return self._synapse

    @abstractmethod
    async def transmit(self, data) -> None:
        pass


class DTSTransmitter(DTSTransmitterBase):
    def __init__(self, synapse: DTSSynapseBase, codec: Codec) -> None:
        super().__init__(synapse)
        self._codec = codec

    async def transmit(self, data: UnencodedDataType) -> None:
        encoded, length = self._codec.encode(data)
        await self.synapse.pass_data(encoded)
