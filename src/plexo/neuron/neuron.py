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
from typing import Generic, Type

from plexo.namespace.namespace import Namespace
from plexo.typing import U, E
from plexo.typing.codec import Codec


class Neuron(Generic[U], Codec):
    def __init__(self, _type: Type[U], namespace: Namespace, codec: Codec):
        self.type: Type[U] = _type
        self.namespace: Namespace = namespace
        self.codec = codec

    def __str__(self):
        return self.type.__name__

    def __hash__(self):
        return hash(self.name)

    def encode(self, data) -> E:
        return self.codec.encode(data)

    def decode(self, data: E):
        return self.codec.decode(data)

    @property
    def name(self):
        return self.namespace.with_suffix((self.type.__name__, self.codec.name))
