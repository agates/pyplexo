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

from typing import Generic, Type, Optional

from plexo.namespace.namespace import Namespace
from plexo.typing import EncodedType, UnencodedType
from plexo.typing.codec import Codec


class Neuron(Codec, Generic[UnencodedType]):
    def __init__(
        self,
        _type: Type[UnencodedType],
        namespace: Namespace,
        codec: Codec,
        type_name_alias: Optional[str] = None,
    ):
        self.type: Type[UnencodedType] = _type
        self.namespace: Namespace = namespace
        self.codec = codec
        self.type_name_alias = type_name_alias or self.type.__name__

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(str(self))

    def encode(self, data: UnencodedType) -> EncodedType:
        return self.codec.encode(data)

    def decode(self, data: EncodedType) -> UnencodedType:
        return self.codec.decode(data)

    @property
    def name(self) -> str:
        return self.namespace.with_suffix((self.type_name_alias, self.codec.name))

    @property
    def name_without_codec(self) -> str:
        return self.namespace.with_suffix((self.type_name_alias,))
