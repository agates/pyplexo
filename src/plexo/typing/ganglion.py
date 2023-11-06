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

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Iterable, Optional, runtime_checkable
from uuid import UUID

from typing_extensions import Protocol

from plexo.neuron.neuron import Neuron
from plexo.typing import UnencodedType, EncodedType

if TYPE_CHECKING:
    # https://www.stefaanlippens.net/circular-imports-type-hints-python.html
    from plexo.typing.reactant import Reactant, RawReactant


@runtime_checkable
class Ganglion(Protocol):
    @abstractmethod
    def capable(self, neuron: Neuron[UnencodedType]) -> bool:
        ...

    # TODO: maybe implement this later as an optimization
    # @abstractmethod
    # def capable_by_name(self, neuron: Neuron[UnencodedSignal]) -> bool:
    #    ...

    @abstractmethod
    async def update_transmitter(self, neuron: Neuron[UnencodedType]):
        ...

    @abstractmethod
    async def react(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Iterable[Reactant[UnencodedType]],
    ):
        ...

    @abstractmethod
    async def transmit(
        self,
        data: UnencodedType,
        neuron: Neuron[UnencodedType],
        reaction_id: Optional[UUID] = None,
    ):
        ...

    @abstractmethod
    async def adapt(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Optional[Iterable[Reactant[UnencodedType]]] = None,
    ):
        ...

    @abstractmethod
    def close(self):
        ...


class GanglionExternal(Ganglion):
    # TODO: maybe implement this later as an optimization
    # @abstractmethod
    # def capable_by_name(self, neuron: Neuron[UnencodedSignal]) -> bool:
    #    ...

    @abstractmethod
    async def react_raw(
        self,
        neuron: Neuron[UnencodedType],
        raw_reactants: Iterable[RawReactant[UnencodedType]],
    ):
        ...

    @abstractmethod
    async def transmit_encoded(
        self,
        data: EncodedType,
        neuron: Neuron[UnencodedType],
        reaction_id: Optional[UUID] = None,
    ):
        ...

    @abstractmethod
    async def adapt(
        self,
        neuron: Neuron[UnencodedType],
        reactants: Optional[Iterable[Reactant[UnencodedType]]] = None,
        raw_reactants: Optional[Iterable[RawReactant[UnencodedType]]] = None,
    ):
        ...
