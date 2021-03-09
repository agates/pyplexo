#  pyplexo
#   Copyright © 2018-2020  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Iterable, Optional
from uuid import UUID

from pyrsistent import plist

from plexo.synapse.base import SynapseBase
from plexo.typing import U, Encoder


def create_encoder_transmitter(
    synapses: Iterable[SynapseBase], encoder: Encoder, loop=None
):
    return partial(transmit_encode, plist(synapses), encoder, loop=loop)


def create_transmitter(synapses: Iterable[SynapseBase], loop=None):
    return partial(transmit, plist(synapses), loop=loop)


async def transmit(
    synapses: Iterable[SynapseBase],
    data: Any,
    reaction_id: Optional[UUID] = None,
    loop=None,
):
    return await asyncio.gather(
        *(synapse.transmit(data, reaction_id) for synapse in synapses), loop=loop
    )


async def transmit_encode(
    synapses: Iterable[SynapseBase],
    encoder: Encoder[U],
    data: U,
    reaction_id: Optional[UUID] = None,
    loop=None,
):
    encoded = encoder(data)
    return await transmit(synapses, encoded, reaction_id, loop=loop)
