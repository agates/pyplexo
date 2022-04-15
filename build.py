from capnpy.compiler.distutils import capnpy_schemas


class SetupKwargsProxy:
    def __init__(self, d):
        self._d = d

    @property
    def capnpy_options(self):
        return {}

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
