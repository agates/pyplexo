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
from timeit import default_timer as timer

from plexo.axon import Axon
from plexo.codec.string_codec import StringCodec
from plexo.neuron.neuron import Neuron
from plexo.exceptions import TransmitterNotFound
from plexo.namespace.namespace import Namespace
from plexo.plexus import Plexus


async def _str_reaction(s: str, _, _2):
    logging.info(f"Received message: {s}")


async def send_hello_str(axon: Axon[str]):
    i = 1
    while True:
        start_time = timer()
        message = f"Hello, Plexo+Inproc {i} …"
        logging.info(f"Sending message: {message}")
        try:
            await axon.transmit(message)
        except TransmitterNotFound as e:
            logging.error(e)
        i += 1
        await asyncio.sleep(1 - (start_time - timer()))


def run():
    logging.basicConfig(level=logging.DEBUG)

    plexus = Plexus()
    namespace = Namespace(["dev", "plexo", "test"])

    str_neuron = Neuron(str, namespace, StringCodec())

    str_plexus_axon = Axon(str_neuron, plexus)

    asyncio.run(str_plexus_axon.react(reactants=[_str_reaction]))
    asyncio.run(send_hello_str(str_plexus_axon))
    plexus.close()


if __name__ == "__main__":
    run()
