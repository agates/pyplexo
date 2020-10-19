#  pyplexo
#   Copyright (C) 2020  Alecks Gates
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
import ipaddress
import logging
import pickle

from plexo.coder import Coder
from plexo.ganglion.multicast import GanglionPlexoMulticast
from plexo.namespace import Namespace

test_multicast_cidr = ipaddress.ip_network('239.255.0.0/16')
test_port = 5561


class Foo:
    message: str


async def _foo_reaction(f: Foo):
    logging.info("Received Foo.string: {}".format(f.message))


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    ganglion = GanglionPlexoMulticast(multicast_cidr=test_multicast_cidr,
                                      port=test_port,
                                      heartbeat_interval_seconds=10,
                                      loop=loop)
    namespace = Namespace(["plexo", "test"])
    foo_coder = Coder(Foo, namespace, pickle.dumps, pickle.loads)
    loop.create_task(ganglion.adapt(foo_coder, decoded_reactant=_foo_reaction))

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
