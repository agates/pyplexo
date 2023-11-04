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
from dataclasses import dataclass
from ipaddress import IPv4Address
from timeit import default_timer as timer
from uuid import UUID

from returns.curry import partial

from plexo.axon import Axon
from plexo.codec.pickle_codec import PickleCodec
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.host_information import get_primary_ip
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.namespace.namespace import Namespace
from plexo.plexus import Plexus


test_port_connect = 5581


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


perf = {"start_time": timer(), "num_messages_received": 0}


async def _foo_reaction(bar_plexus_axon: Axon[Bar], foo: Foo, _, _2):
    logging.info(f"Received Foo: {foo}")
    try:
        bar = Bar(foo_message_id=foo.message_id, node_id=os.path.basename(__file__))
        transmit_task = asyncio.create_task(bar_plexus_axon.transmit(bar))
        logging.info(f"Replying with: {bar}")
        perf["num_messages_received"] += 1
        logging.info(
            f"messages/s: {perf['num_messages_received']/(timer()-perf['start_time'])}"
        )
        await transmit_task
    except TransmitterNotFound as e:
        logging.error(e)


async def wait_until_cancelled():
    while True:
        start_time = timer()
        await asyncio.sleep(10 - (start_time - timer()))


async def run_async(foo_plexus_axon: Axon[Foo], bar_plexus_axon: Axon[Bar]):
    await foo_plexus_axon.react(reactants=[partial(_foo_reaction, bar_plexus_axon)])
    await wait_until_cancelled()


def run():
    logging.basicConfig(level=logging.DEBUG)

    namespace = Namespace(["dev", "plexo", "test"])
    foo_neuron = Neuron(Foo, namespace, PickleCodec())
    bar_neuron = Neuron(Bar, namespace, PickleCodec())

    tcp_pair_ganglion = GanglionZmqTcpPair(
        peer=(IPv4Address(get_primary_ip()), test_port_connect),
        allowed_codecs=(PickleCodec,),
    )
    plexus = Plexus(ganglia=(tcp_pair_ganglion,))

    foo_plexus_axon = Axon(foo_neuron, plexus)
    bar_plexus_axon = Axon(bar_neuron, plexus)

    asyncio.run(run_async(foo_plexus_axon, bar_plexus_axon))

    plexus.close()


if __name__ == "__main__":
    run()
