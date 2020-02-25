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
from domaintypesystem.synapse import DTSZmqEpgmSynapse
from domaintypesystem.transmitter import DTSTransmitter


test_ip_address = ipaddress.IPv4Address('239.255.0.1')
test_port = 6000


class JSONEncoderBytes(json.JSONEncoder):
    def encode(self, o):
        return super(JSONEncoderBytes, self).encode(o).encode("UTF-8")


class JSONDecoderBytes(json.JSONDecoder):
    def decode(self, s, **kwargs):
        return super(JSONDecoderBytes, self).decode(s.decode("UTF-8"))


@pytest.mark.skip
@pytest.mark.asyncio
async def test_zmq_epgm_receptor(event_loop):
    json_encoder = JSONEncoderBytes()
    json_decoder = JSONDecoderBytes()
    test_queue = asyncio.Queue()

    async def receptor_queue(_):
        await test_queue.put(_)

    receptor = DTSReceptor[bytes, dict]((receptor_queue,), json_decoder, loop=event_loop)
    ipc_synapse = DTSZmqEpgmSynapse[bytes]("test",
                                           ip_address=test_ip_address,
                                           port=test_port,
                                           receptors=(receptor,),
                                           loop=event_loop)
    transmitter = DTSTransmitter[dict, bytes](ipc_synapse, json_encoder)

    await asyncio.sleep(.5)

    foo_bar_dict = {"foo": "bar"}
    await transmitter.transmit(foo_bar_dict)

    data = await test_queue.get()
    assert data == foo_bar_dict
    test_queue.task_done()
