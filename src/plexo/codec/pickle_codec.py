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
import pickle  # nosec - Pickle is entirely optional in this library

from plexo.typing import EncodedSignal
from plexo.typing.codec import Codec


class PickleCodec(Codec):
    _name = "pickle"

    def encode(self, data: object) -> EncodedSignal:
        return pickle.dumps(data)

    def decode(self, data: EncodedSignal):
        return pickle.loads(data)  # nosec - Pickle is entirely optional in this library

    @property
    def name(self) -> str:
        return self._name
