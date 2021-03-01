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

from pyrsistent.typing import PMap

from plexo.coder import Coder
from plexo.exceptions import TransmitterNotFound, CoderNotFound
from plexo.ganglion.internal import GanglionInternalBase
from plexo.receptor import create_decoder_receptor
from plexo.synapse.base import SynapseBase
from plexo.transmitter import create_encoder_transmitter
from plexo.typing import U
from plexo.typing.reactant import DecodedReactant, Reactant


class GanglionExternalBase(GanglionInternalBase, ABC):
    def __init__(self, loop=None):
        super(GanglionExternalBase, self).__init__(loop=loop)
        self._encoder_transmitters: PMap[Coder, partial[Coroutine]] = PMap()
        self._encoder_transmitters_lock = asyncio.Lock()

    async def _create_encoder_transmitter(self, coder: Coder, synapse: SynapseBase):
        async with self._encoder_transmitters_lock:
            try:
                return self._encoder_transmitters[coder]
            except KeyError:
                encoder_transmitter = create_encoder_transmitter((synapse,), coder.encoder, loop=self._loop)
                self._encoder_transmitters = self._encoder_transmitters.set(coder, encoder_transmitter)
                return encoder_transmitter

    async def create_encoder_transmitter(self, coder: Coder, synapse: SynapseBase):
        encoder_transmitter = self._create_encoder_transmitter(coder, synapse)

        await self._update_type_coders(coder)

        return encoder_transmitter

    async def update_transmitter(self, coder: Coder):
        synapse = await self.get_synapse(coder)
        await asyncio.gather(self._create_encoder_transmitter(coder, synapse),
                             self._create_transmitter(coder, synapse)
                             )

        await self._update_type_coders(coder)

    def _get_encoder_transmitter(self, coder: Coder):
        try:
            return self._encoder_transmitters[coder]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(coder))

    async def _get_encoder_transmitters(self, data: U) -> Iterable[Callable[[U], Any]]:
        try:
            coders = await self._get_coders(data)
        except CoderNotFound:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(type(data).__name__))
        return (self._get_encoder_transmitter(coder) for coder in coders)

    async def react_decode(self, coder: Coder[U], reactants: Iterable[DecodedReactant[U]]):
        synapse = await self.get_synapse(coder)
        await synapse.update_receptors(
            (create_decoder_receptor(reactants=reactants, decoder=coder.decoder, loop=self._loop),)
        )

    async def transmit_encode(self, data):
        encoder_transmitters = await self._get_encoder_transmitters(data)

        return await asyncio.gather(
            *(encoder_transmitter(data) for encoder_transmitter in encoder_transmitters),
            loop=self._loop)

    async def adapt(self, coder: Coder[U],
                    reactants: Optional[Iterable[Reactant]] = None,
                    decoded_reactants: Optional[Iterable[DecodedReactant[U]]] = None):
        if decoded_reactants:
            await self.react_decode(coder, decoded_reactants)

        return await super(GanglionExternalBase, self).adapt(coder, reactants=reactants)
