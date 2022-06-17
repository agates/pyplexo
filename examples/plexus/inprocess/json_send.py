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

foo_codec = JsonCodec(foo_schema, "Foo")


async def _foo_reaction(f: foo_codec.schema_class, _, _2):
    logging.info(f"Received Foo.message: {f.message}")


async def send_foo_hello_str(plexus: Plexus):
    i = 1
    foo = foo_codec.schema_class()
    while True:
        start_time = timer()
        foo.message = f"Hello, Plexo+Inproc {i} …"
        logging.info(f"Sending Foo with message: {foo.message}")
        logging.debug(f"JSON: {foo.serialize()}")
        try:
            await plexus.transmit(foo)
        except TransmitterNotFound as e:
            logging.error(e)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


def run():
    logging.basicConfig(level=logging.DEBUG)

    plexus = Plexus()
    namespace = Namespace(["plexo", "test"])

    foo_neuron = Neuron(foo_codec.schema_class, namespace, foo_codec)

    asyncio.run(plexus.adapt(foo_neuron, reactants=[_foo_reaction]))
    asyncio.run(send_foo_hello_str(plexus))
    plexus.close()


if __name__ == "__main__":
    run()
