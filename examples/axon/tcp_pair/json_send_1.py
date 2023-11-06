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

import asyncio
import logging
import os
import uuid
from timeit import default_timer as timer
from typing import Type, Optional
from uuid import UUID

import python_jsonschema_objects as pjs

from plexo.axon import Axon
from plexo.codec.json_codec import JsonCodec
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.namespace.namespace import Namespace
from plexo.plexus import Plexus


test_port_bind = 5581


foo_schema = {
    "title": "Foo",
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "message_id": {"type": "string"},
        "message_num": {"type": "number"},
        "node_id": {"type": "string"},
    },
    "required": ["message", "message_id", "message_num", "node_id"],
}

foo_builder = pjs.ObjectBuilder(foo_schema)
foo_jsonschema_namespace = foo_builder.build_classes()

Foo = foo_jsonschema_namespace[foo_schema["title"]]


bar_schema = {
    "title": "Bar",
    "type": "object",
    "properties": {
        "foo_message_id": {"type": "string"},
        "node_id": {"type": "string"},
    },
    "required": ["foo_message_id", "node_id"],
}

bar_builder = pjs.ObjectBuilder(bar_schema)
bar_jsonschema_namespace = bar_builder.build_classes()

Bar = bar_jsonschema_namespace[bar_schema["title"]]


async def _bar_reaction(bar: Bar, neruon: Neuron[Bar], reaction_id: Optional[UUID]):
    logging.info(f"Received Bar: {bar.serialize()}, reaction_id: {reaction_id}")


async def send_foo_hello_str(axon: Axon[Foo]):
    i = 1
    while True:
        start_time = timer()
        foo = Foo(
            message=f"Hello, Plexo+TcpPair {i}",
            message_id=str(uuid.uuid1()),
            message_num=i,
            node_id=os.path.basename(__file__),
        )
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
    bar_codec = JsonCodec(Bar)

    namespace = Namespace(["dev", "plexo", "test"])

    foo_neuron = Neuron(foo_codec.schema_class, namespace, foo_codec)
    bar_neuron = Neuron(bar_codec.schema_class, namespace, bar_codec)

    tcp_pair_ganglion = GanglionZmqTcpPair(
        port=test_port_bind,
        relevant_neurons=(bar_neuron, foo_neuron),
    )
    plexus = Plexus(ganglia=(tcp_pair_ganglion,))

    foo_plexus_axon = Axon(foo_neuron, plexus)
    bar_plexus_axon = Axon(bar_neuron, plexus)

    asyncio.run(bar_plexus_axon.react(reactants=[_bar_reaction]))
    asyncio.run(send_foo_hello_str(foo_plexus_axon))

    plexus.close()


if __name__ == "__main__":
    run()
