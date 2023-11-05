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
from capnpy.struct_ import Struct

from plexo.typing import EncodedSignal
from plexo.typing.codec import Codec


class CapnpyCodec(Codec):
    _name = "capnp"

    def __init__(self, capnpy_struct):
        self.capnpy_struct: Struct = capnpy_struct

    def encode(self, data) -> EncodedSignal:
        return self.capnpy_struct.dumps(data)

    def decode(self, data: EncodedSignal):
        return self.capnpy_struct.loads(data)

    @property
    def name(self) -> str:
        return self._name
