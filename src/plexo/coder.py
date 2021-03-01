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

from plexo.namespace import Namespace
from plexo.typing import Decoder, Encoder, U


class Coder(Generic[U]):
    def __init__(self, _type: Type[U], namespace: Namespace, encoder: Encoder[U], decoder: Decoder[U]):
        self.type: Type[U] = _type
        self.namespace: Namespace = namespace
        self.encoder = encoder
        self.decoder = decoder

    def __str__(self):
        return self.type.__name__

    def __hash__(self):
        return hash(self.full_name())

    def full_name(self):
        return self.namespace.with_suffix(self.type.__name__)
