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

import asyncio
import logging
from timeit import default_timer as timer

import python_jsonschema_objects as pjs

from plexo.axon import Axon
from plexo.codec.json_codec import JsonCodec
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.namespace.namespace import Namespace
from plexo.plexus import Plexus

foo_schema = {
    "title": "Foo",
    "type": "object",
    "properties": {
        "message": {"type": "string"},
    },
    "required": ["message"],
}

builder = pjs.ObjectBuilder(foo_schema)
jsonschema_namespace = builder.build_classes()

Foo = jsonschema_namespace[foo_schema["title"]]


async def _foo_reaction(f: Foo, _, _2):  # type: ignore
    logging.info(f"Received Foo.message: {f.message}")  # type: ignore


async def send_foo_hello_str(axon: Axon):
    i = 1
    foo = Foo()
    while True:
        start_time = timer()
        foo.message = f"Hello, Plexo+Inproc {i} …"
        logging.info(f"Sending Foo with message: {foo.message}")
        logging.debug(f"JSON: {foo.serialize()}")
        try:
            await axon.transmit(foo)
        except TransmitterNotFound as e:
            logging.error(e)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


def run():
    logging.basicConfig(level=logging.DEBUG)

    foo_codec = JsonCodec(Foo)

    plexus = Plexus()
    namespace = Namespace(["dev", "plexo", "test"])

    foo_neuron = Neuron(foo_codec.schema_class, namespace, foo_codec)

    foo_plexus_axon = Axon(foo_neuron, plexus)

    asyncio.run(foo_plexus_axon.react(reactants=[_foo_reaction]))
    asyncio.run(send_foo_hello_str(foo_plexus_axon))
    plexus.close()


if __name__ == "__main__":
    run()
