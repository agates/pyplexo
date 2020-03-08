#  pyplexo
#   Copyright (C) 2020  Alecks Gates
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
import asyncio
from functools import partial
from typing import Iterable, Callable, ByteString, Union

from pyrsistent import pdeque

from plexo import SynapseBase, UnencodedDataType


def create_transmitter(synapses: Iterable[SynapseBase[UnencodedDataType]],
                       encoder: Callable[[UnencodedDataType], ByteString]):
    return partial(transmit_encode, pdeque(synapses), encoder)


def create_transmitter_inproc(synapses: Iterable[SynapseBase[UnencodedDataType]]):
    return partial(transmit, pdeque(synapses))


async def transmit(synapses: Iterable[SynapseBase[UnencodedDataType]],
                   data: Union[ByteString, UnencodedDataType]):
    return await asyncio.wait([synapse.transmit(data) for synapse in synapses])


async def transmit_encode(synapses: Iterable[SynapseBase[UnencodedDataType]],
                          encoder: Callable[[UnencodedDataType], ByteString],
                          data: UnencodedDataType):
    return await transmit(synapses, encoder(data))