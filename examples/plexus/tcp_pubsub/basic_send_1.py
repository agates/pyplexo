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
import os
import uuid
from dataclasses import dataclass
from ipaddress import IPv4Address
from timeit import default_timer as timer
from uuid import UUID

from plexo.codec.pickle_codec import PickleCodec
from plexo.ganglion.tcp_pubsub import GanglionZmqTcpPubSub
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.namespace.namespace import Namespace
from plexo.plexus import Plexus


test_port_pub = 5571


@dataclass
class Foo:
    message: str
    message_id: UUID
    message_num: int
    node_id: str


@dataclass
class Bar:
    foo_message_id: UUID
    node_id: str


async def _bar_reaction(bar: Bar, _, _2):
    logging.info(f"Received Bar: {bar}")


async def send_foo_hello_str(plexus: Plexus):
    i = 1
    while True:
        start_time = timer()
        foo = Foo(
            message=f"Hello, Plexo+TcpPubSub {i}",
            message_id=uuid.uuid1(),
            message_num=i,
            node_id=os.path.basename(__file__),
        )
        logging.info(f"Sending Foo: {str(foo)}")
        try:
            await plexus.transmit(foo)
        except TransmitterNotFound as e:
            logging.error(e)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


async def run_async(foo_neuron: Neuron[Foo], bar_neuron: Neuron[Bar], plexus: Plexus):
    await plexus.adapt(foo_neuron)
    await plexus.adapt(bar_neuron, reactants=[_bar_reaction])
    await send_foo_hello_str(plexus)


def run():
    logging.basicConfig(level=logging.DEBUG)

    tcp_pubsub_ganglion = GanglionZmqTcpPubSub(
        port_pub=test_port_pub, peers=[(IPv4Address("192.168.1.157"), 5572)]
    )
    plexus = Plexus(ganglia=(tcp_pubsub_ganglion,))
    namespace = Namespace(["plexo", "test"])
    foo_neuron = Neuron(Foo, namespace, PickleCodec())
    bar_neuron = Neuron(Bar, namespace, PickleCodec())

    asyncio.run(run_async(foo_neuron, bar_neuron, plexus))

    plexus.close()


if __name__ == "__main__":
    run()
