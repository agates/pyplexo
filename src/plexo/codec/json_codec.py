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
from typing import Optional

import python_jsonschema_objects as pjs

from plexo.typing import EncodedSignal
from plexo.typing.codec import Codec


class JsonCodec(Codec):
    _name = "json"

    def __init__(self, schema_class, serialize_args: Optional[dict] = None):
        if serialize_args is None:
            serialize_args = {"separators": (",", ":")}

        self.serialize_args = serialize_args
        self.schema_class = schema_class

    @classmethod
    def load_from_schema(
        cls, json_schema: dict, schema_name: str, serialize_args: Optional[dict] = None
    ):
        builder = pjs.ObjectBuilder(json_schema)
        namespace = builder.build_classes()

        return cls(namespace[schema_name], serialize_args=serialize_args)

    def encode(self, data) -> EncodedSignal:
        return data.serialize(**self.serialize_args)

    def decode(self, data: EncodedSignal):
        return self.schema_class().from_json(data)

    @property
    def name(self) -> str:
        return self._name
