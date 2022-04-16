#  pyplexo
#  Copyright © 2018-2022  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import asyncio
from functools import partial
from typing import Iterable, Optional
from uuid import UUID

from pyrsistent import plist

from plexo.synapse.base import SynapseBase
from plexo.typing import Encoder, UnencodedSignal, Signal
from plexo.typing.transmitter import EncoderTransmitter, Transmitter


def create_encoder_transmitter(
    synapses: Iterable[SynapseBase], encoder: Encoder
) -> EncoderTransmitter:
    return partial(transmit_encode, plist(synapses), encoder)


def create_transmitter(synapses: Iterable[SynapseBase]) -> Transmitter:
    return partial(transmit, plist(synapses))


async def transmit(
    synapses: Iterable[SynapseBase],
    data: Signal,
    reaction_id: Optional[UUID] = None,
):
    return await asyncio.gather(
        *(synapse.transmit(data, reaction_id) for synapse in synapses)
    )


async def transmit_encode(
    synapses: Iterable[SynapseBase],
    encoder: Encoder[UnencodedSignal],
    data: UnencodedSignal,
    reaction_id: Optional[UUID] = None,
):
    encoded = encoder(data)
    return await transmit(synapses, encoded, reaction_id)
