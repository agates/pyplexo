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
from typing import Iterable, Callable, Any, ByteString

from pyrsistent import pdeque

from plexo import UnencodedDataType


def create_receptor(reactants: Iterable[Callable[[UnencodedDataType], Any]],
                    decoder: Callable[[ByteString], UnencodedDataType]):
    return partial(transduce_decode, pdeque(reactants), decoder)


def create_receptor_inproc(reactants: Iterable[Callable[[UnencodedDataType], Any]]):
    return partial(transduce, pdeque(reactants))


async def transduce(reactants: Iterable[Callable[[UnencodedDataType], Any]],
                    data: UnencodedDataType):
    return await asyncio.wait([reactant(data) for reactant in reactants])


async def transduce_decode(reactants: Iterable[Callable[[UnencodedDataType], Any]],
                           decoder: Callable[[ByteString], UnencodedDataType],
                           data: ByteString):
    return await transduce(reactants, decoder(data))
