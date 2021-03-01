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
from typing import Any, Iterable

from pyrsistent import plist

from plexo.typing import E, U, Decoder
from plexo.typing.reactant import DecodedReactant, Reactant


def create_decoder_receptor(reactants: Iterable[DecodedReactant[U]], decoder: Decoder[U], loop=None):
    return partial(transduce_decode, plist(reactants), decoder, loop=loop)


def create_receptor(reactants: Iterable[Reactant], loop=None):
    return partial(transduce, plist(reactants), loop=loop)


async def transduce(reactants: Iterable[Reactant], data: Any, loop=None):
    return await asyncio.gather(*(reactant(data, None) for reactant in reactants), loop=loop)


async def transduce_decode(reactants: Iterable[DecodedReactant[U]], decoder: Decoder[U], data: E, loop=None):
    decoded = decoder(data)
    return await asyncio.gather(*(reactant(decoded, None) for reactant in reactants), loop=loop)
