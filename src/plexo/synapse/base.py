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

import asyncio
from abc import ABC
from typing import Iterable, Optional
from uuid import UUID

from pyrsistent import PDeque, pdeque

from plexo.neuron.neuron import Neuron
from plexo.receptor import Receptor, DecoderReceptor
from plexo.typing import UnencodedSignal, EncodedSignal
from plexo.typing.reactant import RawReactant, Reactant
from plexo.typing.synapse import SynapseInternal, SynapseExternal


class SynapseInternalBase(SynapseInternal[UnencodedSignal], ABC):
    def __init__(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Iterable[Reactant[UnencodedSignal]] = (),
    ) -> None:
        self.neuron = neuron
        self.topic_bytes = neuron.name.encode("UTF-8")

        self._receptor: Receptor = Receptor(neuron, reactants)

        self._receptors_write_lock = asyncio.Lock()

        self._tasks: PDeque = pdeque()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            self._tasks = pdeque()

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        await self._receptor.add_reactants(reactants)

    async def transduce(
        self, data: UnencodedSignal, reaction_id: Optional[UUID] = None
    ):
        return await self._receptor.transduce(data, reaction_id)


class SynapseExternalBase(SynapseExternal[UnencodedSignal], ABC):
    def __init__(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Iterable[Reactant[UnencodedSignal]] = (),
        raw_reactants: Iterable[RawReactant[UnencodedSignal]] = (),
    ) -> None:
        self.neuron = neuron
        self.topic_bytes = neuron.name.encode("UTF-8")

        self._receptor: DecoderReceptor = DecoderReceptor(
            neuron, reactants, raw_reactants
        )

        self._receptors_write_lock = asyncio.Lock()

        self._tasks: PDeque = pdeque()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            self._tasks = pdeque()

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        await self._receptor.add_reactants(reactants)

    async def add_raw_reactants(
        self, raw_reactants: Iterable[RawReactant[UnencodedSignal]]
    ):
        await self._receptor.add_raw_reactants(raw_reactants)

    async def transduce(self, data: EncodedSignal, reaction_id: Optional[UUID] = None):
        return await self._receptor.transduce(data, reaction_id)
