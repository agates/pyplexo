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

from capnpy.compiler.distutils import capnpy_schemas


class SetupKwargsProxy:
    def __init__(self, d):
        self._d = d

    @property
    def capnpy_options(self):
        return {
            "include_reflection_data": True,
            # TODO: Remove the below options once we stabilize the capnpy version
            "version_check": False,
        }

    @property
    def ext_modules(self):
        try:
            return self._d["ext_modules"]
        except KeyError:
            return None

    @ext_modules.setter
    def ext_modules(self, v):
        self._d["ext_modules"] = v


schema_files = [
    "src/plexo/schema/plexo_approval.capnp",
    "src/plexo/schema/plexo_heartbeat.capnp",
    "src/plexo/schema/plexo_message.capnp",
    "src/plexo/schema/plexo_preparation.capnp",
    "src/plexo/schema/plexo_promise.capnp",
    "src/plexo/schema/plexo_proposal.capnp",
    "src/plexo/schema/plexo_rejection.capnp",
]


def build(setup_kwargs):
    capnpy_schemas(SetupKwargsProxy(setup_kwargs), "capnpy_schemas", schema_files)
