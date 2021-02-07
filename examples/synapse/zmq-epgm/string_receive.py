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
from typing import ByteString

from plexo.synapse.zeromq import SynapseZmqEPGM
from plexo.receptor import create_decoder_receptor
from plexo.typing.ganglion import Ganglion

test_ip_address = ipaddress.IPv4Address('239.255.0.1')
test_port = 5561

start_time = timer()
messages_lock = asyncio.Lock()
messages = {"received": 0}


class FakeGanglion(Ganglion):
    async def update_transmitter(self, coder):
        pass

    async def react(self, coder, reactant):
        pass

    async def transmit(self, data):
        pass

    async def adapt(self, coder, reactant = None):
        pass


async def print_handler(data: str, _):
    async with messages_lock:
        messages["received"] += 1
        logging.info("Print handler: {0} - {1} messages/s".format(
            data,
            messages["received"]/(timer()-start_time))
        )


def bytes_decode(b: ByteString):
    return bytes(b).decode("UTF-8")


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    ganglion = FakeGanglion()

    receptor = create_decoder_receptor(reactants=(print_handler,), decoder=bytes_decode)
    synapse = SynapseZmqEPGM("example_string",
                             ganglion=ganglion,
                             multicast_address=test_ip_address,
                             port=test_port,
                             receptors=(receptor,),
                             loop=loop)

    if not loop.is_running():  # pragma: no cover
        try:
            logging.info("Running asyncio loop")
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    synapse.close()


if __name__ == "__main__":
    run()
