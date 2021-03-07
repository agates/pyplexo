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
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
from abc import ABC
from functools import partial
from typing import Any, Callable, Coroutine, Iterable, Optional
from uuid import UUID

from pyrsistent import pmap
from pyrsistent.typing import PMap

from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound, NeuronNotFound
from plexo.ganglion.internal import GanglionInternalBase
from plexo.receptor import create_decoder_receptor
from plexo.synapse.base import SynapseBase
from plexo.transmitter import create_encoder_transmitter
from plexo.typing import U
from plexo.typing.reactant import DecodedReactant, Reactant


class GanglionExternalBase(GanglionInternalBase, ABC):
    def __init__(self, loop=None):
        super(GanglionExternalBase, self).__init__(loop=loop)
        self._encoder_transmitters: PMap[Neuron, partial[Coroutine]] = pmap({})
        self._encoder_transmitters_lock = asyncio.Lock()

    async def _create_encoder_transmitter(self, neuron: Neuron, synapse: SynapseBase):
        async with self._encoder_transmitters_lock:
            try:
                return self._encoder_transmitters[neuron]
            except KeyError:
                encoder_transmitter = create_encoder_transmitter((synapse,), neuron.encode, loop=self._loop)
                self._encoder_transmitters = self._encoder_transmitters.set(neuron, encoder_transmitter)
                return encoder_transmitter

    async def create_encoder_transmitter(self, neuron: Neuron, synapse: SynapseBase):
        encoder_transmitter = self._create_encoder_transmitter(neuron, synapse)

        await self._update_type_neurons(neuron)

        return encoder_transmitter

    async def update_transmitter(self, neuron: Neuron):
        synapse = await self.get_synapse(neuron)
        await asyncio.gather(self._create_encoder_transmitter(neuron, synapse),
                             self._create_transmitter(neuron, synapse)
                             )

        await self._update_type_neurons(neuron)

    def _get_encoder_transmitter(self, neuron: Neuron):
        try:
            return self._encoder_transmitters[neuron]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(neuron))

    async def _get_encoder_transmitters(self, data: U) -> Iterable[Callable[[U, Optional[UUID]], Any]]:
        try:
            neurons = await self._get_neurons(data)
        except NeuronNotFound:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type(data).__name__))
        return (self._get_encoder_transmitter(neuron) for neuron in neurons)

    async def react_decode(self, neuron: Neuron[U], reactants: Iterable[DecodedReactant[U]]):
        synapse = await self.get_synapse(neuron)
        await synapse.update_receptors(
            (create_decoder_receptor(reactants=reactants, decoder=neuron.decode, loop=self._loop),)
        )

    async def transmit_encode(self, data, reaction_id: Optional[UUID] = None):
        encoder_transmitters = await self._get_encoder_transmitters(data)

        return await asyncio.gather(
            *(encoder_transmitter(data, reaction_id) for encoder_transmitter in encoder_transmitters),
            loop=self._loop)

    async def adapt(self, neuron: Neuron[U],
                    reactants: Optional[Iterable[Reactant]] = None,
                    decoded_reactants: Optional[Iterable[DecodedReactant[U]]] = None):
        if decoded_reactants:
            await self.react_decode(neuron, decoded_reactants)

        return await super(GanglionExternalBase, self).adapt(neuron, reactants=reactants)
