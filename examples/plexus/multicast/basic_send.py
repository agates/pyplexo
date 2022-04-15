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
import asyncio
import ipaddress
import logging
from timeit import default_timer as timer

from plexo.codec.pickle_codec import PickleCodec
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.ganglion.multicast import GanglionPlexoMulticast
from plexo.namespace.namespace import Namespace
from plexo.plexus import Plexus


test_multicast_cidr = ipaddress.ip_network("239.255.0.0/16")
test_port = 5561


class Foo:
    message: str


async def _foo_reaction(f: Foo, _):
    logging.info(f"Received Foo.string: {f.message}")


async def send_foo_hello_str(plexus: Plexus):
    i = 1
    foo = Foo()
    while True:
        start_time = timer()
        foo.message = f"Hello, Plexo+Multicast {i} …"
        logging.info(f"Sending Foo with message: {foo.message}")
        try:
            await plexus.transmit(foo)
        except TransmitterNotFound as e:
            logging.error(e)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


def run():
    logging.basicConfig(level=logging.DEBUG)

    multicast_ganglion = GanglionPlexoMulticast(
        multicast_cidr=test_multicast_cidr,
        port=test_port,
        heartbeat_interval_seconds=10,
    )
    plexus = Plexus(ganglia=(multicast_ganglion,))
    namespace = Namespace(["plexo", "test"])
    foo_coder = Neuron(Foo, namespace, PickleCodec())

    asyncio.run(
        asyncio.wait(
            [
                plexus.adapt(foo_coder, reactants=[_foo_reaction]),
                multicast_ganglion.startup(),
            ]
        )
    )
    asyncio.run(send_foo_hello_str(plexus))

    plexus.close()


if __name__ == "__main__":
    run()
