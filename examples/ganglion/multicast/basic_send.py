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
from timeit import default_timer as timer

from plexo.ganglion import GanglionMulticast

test_multicast_cidr = ipaddress.ip_network('239.255.0.0/16')
test_port = 5561


class Foo:
    message: str


async def send_foo_hello_str(transmitter):
    i = 1
    foo = Foo
    while True:
        start_time = timer()
        foo.message = "Hello, Plexo+Multicast {} …".format(i)
        logging.info("Sending Foo: {}".format(foo))
        await transmitter(foo)
        i += 1
        await asyncio.sleep(1-(start_time-timer()))


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    ganglion = GanglionMulticast(multicast_cidr=test_multicast_cidr,
                                 port=test_port,
                                 heartbeat_interval_seconds=10,
                                 loop=loop)

    transmitter = await ganglion.update_transmitter(Foo, pickle.dumps)

    loop.create_task(send_foo_hello_str(transmitter))

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
