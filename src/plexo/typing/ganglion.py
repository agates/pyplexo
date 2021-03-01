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
from typing import Any, Iterable, Optional, Tuple,TYPE_CHECKING

from typing_extensions import Protocol

from plexo.coder import Coder
if TYPE_CHECKING:
    # https://www.stefaanlippens.net/circular-imports-type-hints-python.html
    from plexo.typing import U
    from plexo.typing.reactant import Reactant


class Ganglion(Protocol):
    @abstractmethod
    async def update_transmitter(self, coder: Coder[U]): ...

    @abstractmethod
    async def react(self, coder: Coder[U], reactants: Iterable[Reactant]): ...

    @abstractmethod
    async def transmit(self, data: U) ->  Tuple[Any]: ... # pyright: reportInvalidTypeVarUse=false

    @abstractmethod
    async def adapt(self, coder: Coder[U], reactants: Optional[Iterable[Reactant]] = None): ...

    @abstractmethod
    def close(self): ...
