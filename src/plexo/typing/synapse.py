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
from typing import TYPE_CHECKING, Iterable, Optional
from uuid import UUID

from typing_extensions import Protocol

from plexo.typing import UnencodedType, EncodedType

if TYPE_CHECKING:
    # https://www.stefaanlippens.net/circular-imports-type-hints-python.html
    from plexo.typing.reactant import Reactant, RawReactant


class SynapseInternal(Protocol[UnencodedType]):
    @abstractmethod
    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedType]]):
        ...

    @abstractmethod
    async def transduce(self, data: UnencodedType, reaction_id: Optional[UUID] = None):
        ...

    @abstractmethod
    async def transmit(
        self,
        data: UnencodedType,
        reaction_id: Optional[UUID] = None,
    ):
        ...

    @abstractmethod
    def close(self):
        ...


class SynapseExternal(Protocol[UnencodedType]):
    @abstractmethod
    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedType]]):
        ...

    @abstractmethod
    async def add_raw_reactants(
        self, raw_reactants: Iterable[RawReactant[UnencodedType]]
    ):
        ...

    @abstractmethod
    async def transduce(self, data: EncodedType, reaction_id: Optional[UUID] = None):
        ...

    @abstractmethod
    async def transmit(
        self,
        data: EncodedType,
        reaction_id: Optional[UUID] = None,
    ):
        ...

    @abstractmethod
    def close(self):
        ...
