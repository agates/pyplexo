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
import ipaddress
import logging
from timeit import default_timer as timer

from plexo.codec.pickle_codec import PickleCodec
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.ganglion.plexo_multicast import GanglionPlexoMulticast
from plexo.namespace.namespace import Namespace

test_multicast_cidr = ipaddress.ip_network("239.255.0.0/16")
test_port = 5561


class Foo:
    message: str


async def send_foo_hello_str(ganglion: GanglionPlexoMulticast, foo_neuron: Neuron[Foo]):
    i = 1
    foo = Foo()
    while True:
        start_time = timer()
        foo.message = f"Hello, Plexo+Multicast {i} …"
        logging.info(f"Sending Foo with message: {foo.message}")
        try:
            await ganglion.transmit(foo, foo_neuron)
        except TransmitterNotFound as e:
            logging.error(e)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    ganglion = GanglionPlexoMulticast(
        multicast_cidr=test_multicast_cidr,
        port=test_port,
        heartbeat_interval_seconds=10,
    )
    namespace = Namespace(["dev", "plexo", "test"])
    foo_neuron = Neuron(Foo, namespace, PickleCodec())
    asyncio.run(ganglion.adapt(foo_neuron))
    asyncio.run(send_foo_hello_str(ganglion, foo_neuron))

    if not loop.is_running():  # pragma: no cover
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    ganglion.close()


if __name__ == "__main__":
    run()
