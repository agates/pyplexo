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
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Iterable, Optional
from uuid import UUID

from typing_extensions import Protocol

from plexo.neuron.neuron import Neuron

if TYPE_CHECKING:
    # https://www.stefaanlippens.net/circular-imports-type-hints-python.html
    from plexo.typing.reactant import Reactant


class Ganglion(Protocol):
    @abstractmethod
    async def update_transmitter(self, neuron: Neuron):
        ...

    @abstractmethod
    async def react(self, neuron: Neuron, reactants: Iterable[Reactant]):
        ...

    @abstractmethod
    async def transmit(self, data, reaction_id: Optional[UUID] = None):
        ...

    @abstractmethod
    async def adapt(
        self, neuron: Neuron, reactants: Optional[Iterable[Reactant]] = None
    ):
        ...

    @abstractmethod
    def close(self):
        ...
