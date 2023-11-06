#  pyplexo
#  Copyright © 2018-2023  Alecks Gates
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
from plexo.dendrite import Dendrite, DecoderDendrite
from plexo.typing import UnencodedType, EncodedType
from plexo.typing.reactant import RawReactant, Reactant
from plexo.typing.synapse import SynapseInternal, SynapseExternal


class SynapseInternalBase(SynapseInternal[UnencodedType], ABC):
    def __init__(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Iterable[Reactant[UnencodedType]] = (),
    ) -> None:
        self.neuron = neuron
        self.topic_bytes = neuron.name.encode("UTF-8")

        self._dendrite: Dendrite = Dendrite(neuron, reactants)

        self._tasks: PDeque = pdeque()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            wait_coro = asyncio.wait(
                self._tasks, timeout=10, return_when=asyncio.ALL_COMPLETED
            )
            try:
                loop = asyncio.get_running_loop()

                future = asyncio.run_coroutine_threadsafe(wait_coro, loop)
                # This is broken, pending https://bugs.python.org/issue42130
                future.result(10)
            except RuntimeError:
                asyncio.run(wait_coro)
            except TimeoutError:
                pass
            finally:
                self._tasks = pdeque()

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedType]]):
        await self._dendrite.add_reactants(reactants)

    async def transduce(self, data: UnencodedType, reaction_id: Optional[UUID] = None):
        return await self._dendrite.transduce(data, reaction_id)


class SynapseExternalBase(SynapseExternal[UnencodedType], ABC):
    def __init__(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Iterable[Reactant[UnencodedType]] = (),
        raw_reactants: Iterable[RawReactant[UnencodedType]] = (),
    ) -> None:
        self.neuron = neuron
        self.topic_bytes = neuron.name.encode("UTF-8")

        self._dendrite: DecoderDendrite = DecoderDendrite(
            neuron, reactants, raw_reactants
        )

        self._tasks: PDeque = pdeque()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            wait_coro = asyncio.wait(
                self._tasks, timeout=10, return_when=asyncio.ALL_COMPLETED
            )
            try:
                loop = asyncio.get_running_loop()

                future = asyncio.run_coroutine_threadsafe(wait_coro, loop)
                # This is broken, pending https://bugs.python.org/issue42130
                future.result(10)
            except RuntimeError:
                asyncio.run(wait_coro)
            except TimeoutError:
                pass
            finally:
                self._tasks = pdeque()

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedType]]):
        await self._dendrite.add_reactants(reactants)

    async def add_raw_reactants(
        self, raw_reactants: Iterable[RawReactant[UnencodedType]]
    ):
        await self._dendrite.add_raw_reactants(raw_reactants)

    async def transduce(self, data: EncodedType, reaction_id: Optional[UUID] = None):
        return await self._dendrite.transduce(data, reaction_id)
