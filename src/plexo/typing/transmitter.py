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

from typing import Optional, Coroutine, Protocol
from uuid import UUID

from plexo.typing import UnencodedType, EncodedType


class ExternalTransmitter(Protocol):
    def __call__(
        self,
        data: EncodedType,
        reaction_id: Optional[UUID] = None,
    ) -> Coroutine:
        ...


class Transmitter(Protocol):
    def __call__(
        self,
        data: UnencodedType,
        reaction_id: Optional[UUID] = None,
    ) -> Coroutine:
        ...
