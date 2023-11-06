#  pyplexo
#  Copyright © 2023  Alecks Gates
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
from typing import Generic, Iterable, Optional

from plexo.neuron.neuron import Neuron
from plexo.typing import UnencodedType
from plexo.typing.ganglion import Ganglion
from plexo.typing.reactant import Reactant


class Axon(Generic[UnencodedType]):
    def __init__(
        self,
        neuron: Neuron[UnencodedType],
        ganglion: Ganglion,
    ):
        self.neuron = neuron
        self.ganglion = ganglion

        self._startup_done = False

    async def adapt(self):
        await self.ganglion.adapt(self.neuron)
        self._startup_done = True

    async def react(
        self,
        reactants: Iterable[Reactant[UnencodedType]],
    ):
        if not self._startup_done:
            await self.adapt()

        return await self.ganglion.react(self.neuron, reactants)

    async def transmit(
        self,
        data: UnencodedType,
    ):
        if not self._startup_done:
            await self.adapt()

        return await self.ganglion.transmit(data, self.neuron)
