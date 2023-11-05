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

from plexo.codec.string_codec import StringCodec
from plexo.namespace.namespace import Namespace
from plexo.neuron.neuron import Neuron
from plexo.synapse.zeromq_plexopubsub_epgm import SynapseZmqPlexoPubSubEPGM
from plexo.transmitter import create_external_encoder_transmitter
from plexo.typing.transmitter import Transmitter

test_ip_address = ipaddress.IPv4Address("239.255.0.1")
test_port = 5561


async def send_hello_str(transmitter: Transmitter):
    i = 1
    while True:
        start_time = timer()
        message = f"Hello, Plexo+EPGM {i} …"
        logging.info(f"Sending message: {message}")
        await transmitter(message)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    namespace = Namespace(["dev", "plexo", "test"])
    str_neuron = Neuron(str, namespace, StringCodec())
    synapse = SynapseZmqPlexoPubSubEPGM(
        str_neuron, multicast_address=test_ip_address, port=test_port
    )
    transmitter = create_external_encoder_transmitter(synapse, str.encode)

    loop.create_task(send_hello_str(transmitter))

    if not loop.is_running():  # pragma: no cover
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    synapse.close()


if __name__ == "__main__":
    run()
