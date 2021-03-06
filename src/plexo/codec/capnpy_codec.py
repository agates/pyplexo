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
from plexo.typing import E
from plexo.typing.codec import Codec


class CapnpyCodec(Codec):
    name = "capnp"

    def __init__(self, capnpy_struct):
        self.capnpy_struct = capnpy_struct

    def encode(self, data) -> E:
        return self.capnpy_struct.dumps(data)

    def decode(self, data: E):
        return self.capnpy_struct.loads(data)
