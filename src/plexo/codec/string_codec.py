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

from typing import cast

from plexo.typing import EncodedType
from plexo.typing.codec import Codec


class StringCodec(Codec):
    _name = "string_UTF-8"

    def encode(self, data: str) -> EncodedType:
        return data.encode("UTF-8")

    def decode(self, data: EncodedType):
        return cast(bytes, data).decode("UTF-8")

    @property
    def name(self) -> str:
        return self._name
