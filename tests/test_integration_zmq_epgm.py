#  domain-type-system
#   Copyright (C) 2019  Alecks Gates
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
import json
import ipaddress

import pytest

from domaintypesystem.receptor import DTSReceptor
from domaintypesystem.synapse import DTSSynapseZmqEPGM
from domaintypesystem.transmitter import DTSTransmitter

test_ip_address = ipaddress.IPv4Address('239.255.0.1')
test_port = 5561


def encode_json_bytes(o: dict) -> bytes:
    return json.dumps(o).encode("UTF-8")


def decode_json_bytes(s: bytes) -> dict:
    return json.loads(s.decode("UTF-8"))


@pytest.mark.skip
@pytest.mark.asyncio
async def test_zmq_epgm_receptor(event_loop):
    test_queue = asyncio.Queue()

    async def receptor_queue(_):
        await test_queue.put(_)

    receptor = DTSReceptor[dict]((receptor_queue,), decode_json_bytes, loop=event_loop)
    synapse = DTSSynapseZmqEPGM[dict]("test",
                                      multicast_address=test_ip_address,
                                      port=test_port,
                                      receptors=(receptor,),
                                      loop=event_loop)
    transmitter = DTSTransmitter[dict](synapse, encode_json_bytes)

    await asyncio.sleep(.1)

    foo_bar_dict = {"foo": "bar"}
    await transmitter.transmit(foo_bar_dict)

    await asyncio.sleep(.1)

    data = await test_queue.get()
    assert data == foo_bar_dict
    test_queue.task_done()
