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

from typing import Optional
from uuid import UUID

from returns.curry import partial

from plexo.neuron.neuron import Neuron
from plexo.typing import Encoder, UnencodedSignal, EncodedSignal
from plexo.typing.synapse import SynapseExternal, SynapseInternal
from plexo.typing.transmitter import Transmitter, ExternalTransmitter


def create_external_encoder_transmitter(
    synapse: SynapseExternal[UnencodedSignal], encoder: Encoder
) -> Transmitter:
    return partial(transmit_external_encode, synapse, encoder)


def create_external_transmitter(
    synapse: SynapseExternal[UnencodedSignal],
) -> ExternalTransmitter:
    return partial(transmit_external, synapse)


def create_transmitter(synapse: SynapseInternal[UnencodedSignal]) -> Transmitter:
    return partial(transmit, synapse)


async def transmit(
    synapse: SynapseInternal[UnencodedSignal],
    data: UnencodedSignal,
    neuron: Optional[Neuron[UnencodedSignal]] = None,
    reaction_id: Optional[UUID] = None,
):
    return await synapse.transmit(data, neuron, reaction_id)


async def transmit_external(
    synapse: SynapseExternal[UnencodedSignal],
    data: EncodedSignal,
    neuron: Optional[Neuron[UnencodedSignal]] = None,
    reaction_id: Optional[UUID] = None,
):
    return await synapse.transmit(data, neuron, reaction_id)


async def transmit_external_encode(
    synapse: SynapseExternal[UnencodedSignal],
    encoder: Encoder[UnencodedSignal],
    data: UnencodedSignal,
    neuron: Optional[Neuron[UnencodedSignal]] = None,
    reaction_id: Optional[UUID] = None,
):
    encoded = encoder(data)
    return await synapse.transmit(encoded, neuron, reaction_id)
