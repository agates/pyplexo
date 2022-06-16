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
import ipaddress
import logging

from plexo.codec.pickle_codec import PickleCodec
from plexo.neuron.neuron import Neuron
from plexo.ganglion.multicast import GanglionPlexoMulticast
from plexo.namespace.namespace import Namespace

test_multicast_cidr = ipaddress.ip_network("239.255.0.0/16")
test_port = 5561


class Foo:
    message: str


async def _foo_reaction(data: Foo, _):
    logging.info(f"Received Foo.string: {data.message}")


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    ganglion = GanglionPlexoMulticast(
        multicast_cidr=test_multicast_cidr,
        port=test_port,
        heartbeat_interval_seconds=10,
    )
    namespace = Namespace(["plexo", "test"])
    foo_neuron = Neuron(Foo, namespace, PickleCodec())

    asyncio.run(ganglion.adapt(foo_neuron, raw_reactants=[_foo_reaction]))

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
