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

from typing import Iterable


class Namespace:
    def __init__(self, parts: Iterable[str], delimiter: str = "."):
        self.delimiter = delimiter
        self.parts = parts

        self.path = delimiter.join(parts)

    def __str__(self):
        return self.path

    def __hash__(self):
        return hash(self.path)

    def with_suffix(self, suffix: Iterable[str]):
        return self.delimiter.join((self.path, *suffix))
