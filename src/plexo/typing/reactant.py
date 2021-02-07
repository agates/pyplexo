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

from typing import Callable, Coroutine, Any, TYPE_CHECKING

#from typing_extensions import Protocol # pyright: reportMissingModuleSource=false

if TYPE_CHECKING:
    # https://www.stefaanlippens.net/circular-imports-type-hints-python.html
    from plexo.typing import U, D
    from plexo.typing.ganglion import Ganglion


DecodedReactant = Callable[["U", "Ganglion"], Coroutine[Any, Any, Any]]
Reactant = Callable[["D", "Ganglion"], Coroutine[Any, Any, Any]]

#class DecodedReactant(Protocol):
#    def __call__(self, data: U, source: Ganglion) -> Coroutine[Any, Any, Any]: ...
#
#
#class Reactant(Protocol):
#    def __call__(self, data: D, source: Ganglion) -> Coroutine[Any, Any, Any]: ...
