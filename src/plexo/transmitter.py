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
from typing import Iterable

from pyrsistent import plist

from plexo.synapse.base import SynapseBase
from plexo.typing import D, U, Encoder


def create_encoder_transmitter(synapses: Iterable[SynapseBase], encoder: Encoder, loop=None):
    return partial(transmit_encode, plist(synapses), encoder, loop=loop)


def create_transmitter(synapses: Iterable[SynapseBase], loop=None):
    return partial(transmit, plist(synapses), loop=loop)


async def transmit(synapses: Iterable[SynapseBase], data: D, loop=None):
    return await asyncio.wait([synapse.transmit(data) for synapse in synapses], loop=loop)


async def transmit_encode(synapses: Iterable[SynapseBase], encoder: Encoder, data: U, loop=None):
    encoded = encoder(data)
    return await transmit(synapses, encoded, loop=loop)
