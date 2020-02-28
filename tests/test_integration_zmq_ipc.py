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

import pytest

from domaintypesystem.receptor import DTSReceptor
from domaintypesystem.synapse import DTSSynapseZmqIPC
from domaintypesystem.transmitter import DTSTransmitter


def encode_json_bytes(o: dict) -> bytes:
    return json.dumps(o).encode("UTF-8")


def decode_json_bytes(s: bytes) -> dict:
    return json.loads(s.decode("UTF-8"))


@pytest.mark.asyncio
async def test_zmq_ipc_synapse(event_loop):
    test_queue = asyncio.Queue()

    async def receptor_queue(_):
        await test_queue.put(_)

    receptor = DTSReceptor[dict]((receptor_queue,), decode_json_bytes, loop=event_loop)
    synapse = DTSSynapseZmqIPC[dict]("test", receptors=(receptor,), loop=event_loop)
    transmitter = DTSTransmitter[dict](synapse, encode_json_bytes)

    await asyncio.sleep(.25)

    foo_bar_dict = {"foo": "bar"}
    await transmitter.transmit(foo_bar_dict)

    await asyncio.sleep(.25)

    data = await test_queue.get()
    assert data == foo_bar_dict
    test_queue.task_done()
