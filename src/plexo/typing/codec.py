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
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.
from abc import abstractmethod

from typing_extensions import Protocol

from plexo.typing import E


class Codec(Protocol):
    name: str

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    @abstractmethod
    def encode(self, data) -> E:
        ...

    @abstractmethod
    def decode(self, data: E):
        ...
