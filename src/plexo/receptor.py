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

from plexo.typing import Decoder, EncodedSignal, UnencodedSignal, Signal
from plexo.typing.reactant import DecodedReactant, Reactant
from plexo.typing.receptor import Receptor, DecoderReceptor


def create_decoder_receptor(
    reactants: Iterable[DecodedReactant[UnencodedSignal]],
    decoder: Decoder[UnencodedSignal],
) -> DecoderReceptor:
    return partial(transduce_decode, plist(reactants), decoder)


def create_receptor(reactants: Iterable[Reactant]) -> Receptor:
    return partial(transduce, plist(reactants))


async def transduce(
    reactants: Iterable[Reactant],
    data: Signal,
    reaction_id: Optional[UUID] = None,
):
    return await asyncio.wait([reactant(data, reaction_id) for reactant in reactants])


async def transduce_decode(
    reactants: Iterable[DecodedReactant[UnencodedSignal]],
    decoder: Decoder[UnencodedSignal],
    data: EncodedSignal,
    reaction_id: Optional[UUID] = None,
):
    decoded = decoder(data)
    return await asyncio.wait(
        [reactant(decoded, reaction_id) for reactant in reactants]
    )
