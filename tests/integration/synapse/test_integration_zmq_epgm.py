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
import json
import ipaddress

import pytest

from plexo.receptor import create_decoder_receptor
from plexo.synapse.zeromq import SynapseZmqEPGM
from plexo.transmitter import transmit_encode

test_ip_address = ipaddress.IPv4Address("239.255.0.1")
test_port = 5561


def encode_json_bytes(o: dict) -> bytes:
    return json.dumps(o).encode("UTF-8")


def decode_json_bytes(s: bytes) -> dict:
    return json.loads(s)


@pytest.mark.skip
@pytest.mark.asyncio
async def test_zmq_epgm_receptor(event_loop):
    test_queue: asyncio.Queue = asyncio.Queue()

    async def receptor_queue(_1, _2):
        await test_queue.put(_1)

    receptor = create_decoder_receptor(
        reactants=(receptor_queue,), decoder=decode_json_bytes
    )
    synapse = SynapseZmqEPGM(
        "test",
        multicast_address=test_ip_address,
        port=test_port,
        receptors=(receptor,),
        loop=event_loop,
    )

    await asyncio.sleep(0.1)

    foo_bar_dict = {"foo": "bar"}
    await transmit_encode((synapse,), encode_json_bytes, foo_bar_dict)

    await asyncio.sleep(0.1)

    data = await test_queue.get()
    assert data == foo_bar_dict
    test_queue.task_done()
