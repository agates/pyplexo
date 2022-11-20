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
from typing import Iterable, Optional, Generic
from uuid import UUID

from pyrsistent import pset, pvector
from pyrsistent.typing import PVector

from plexo.neuron.neuron import Neuron
from plexo.typing import EncodedSignal, UnencodedSignal
from plexo.typing.reactant import Reactant, RawReactant


class Receptor(Generic[UnencodedSignal]):
    def __init__(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Iterable[Reactant[UnencodedSignal]] = (),
    ):
        self.neuron = neuron
        self._reactants = pvector(pset(reactants))
        self._reactants_write_lock = asyncio.Lock()

    @property
    def reactants(self) -> PVector[Reactant[UnencodedSignal]]:
        return self._reactants

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        async with self._reactants_write_lock:
            self._reactants = pvector(pset(self._reactants).update(reactants))

    async def remove_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        async with self._reactants_write_lock:
            self._reactants = pvector(pset(self._reactants).difference(reactants))

    async def transduce(
        self, data: UnencodedSignal, reaction_id: Optional[UUID] = None
    ):
        neuron = self.neuron
        try:
            return await asyncio.gather(
                *(reactant(data, neuron, reaction_id) for reactant in self.reactants)
            )
        except ValueError:
            # Got empty list, continue
            pass


class DecoderReceptor(Generic[UnencodedSignal]):
    def __init__(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Iterable[Reactant[UnencodedSignal]] = (),
        raw_reactants: Iterable[RawReactant[UnencodedSignal]] = (),
    ):
        self.neuron = neuron
        self._reactants = pvector(pset(reactants))
        self._raw_reactants = pvector(pset(raw_reactants))
        self._reactants_write_lock = asyncio.Lock()

    @property
    def reactants(self) -> PVector[Reactant[UnencodedSignal]]:
        return self._reactants

    @property
    def raw_reactants(self) -> PVector[RawReactant[UnencodedSignal]]:
        return self._raw_reactants

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        async with self._reactants_write_lock:
            self._reactants = pvector(pset(self._reactants).update(reactants))

    async def add_raw_reactants(
        self, raw_reactants: Iterable[RawReactant[UnencodedSignal]]
    ):
        async with self._reactants_write_lock:
            self._raw_reactants = pvector(
                pset(self._raw_reactants).update(raw_reactants)
            )

    async def remove_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        async with self._reactants_write_lock:
            self._reactants = pvector(pset(self._reactants).difference(reactants))

    async def remove_raw_reactants(
        self, raw_reactants: Iterable[RawReactant[UnencodedSignal]]
    ):
        async with self._reactants_write_lock:
            self._raw_reactants = pvector(
                pset(self._raw_reactants).difference(raw_reactants)
            )

    async def transduce(self, data: EncodedSignal, reaction_id: Optional[UUID] = None):
        neuron = self.neuron
        try:
            decoded_data = self.neuron.decode(data)
            return await asyncio.gather(
                *(
                    reactant(decoded_data, neuron, reaction_id)
                    for reactant in self.reactants
                ),
                *(
                    raw_reactant(data, neuron, reaction_id)
                    for raw_reactant in self.raw_reactants
                ),
            )
        except ValueError:
            # Got empty list, continue
            pass
