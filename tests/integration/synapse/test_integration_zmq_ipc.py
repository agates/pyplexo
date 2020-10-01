#  pyplexo
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
from typing import ByteString

import pytest

from plexo.receptor import create_decoder_receptor
from plexo.synapse.zeromq import SynapseZmqIPC
from plexo.transmitter import transmit_encode


def encode_json_bytes(o: dict) -> bytes:
    return json.dumps(o).encode("UTF-8")


def decode_json_bytes(s: ByteString) -> dict:
    return json.loads(bytes(s).decode("UTF-8"))


@pytest.mark.asyncio
async def test_zmq_ipc_synapse(event_loop):
    test_queue = asyncio.Queue(loop=event_loop)

    async def receptor_queue(_):
        await test_queue.put(_)

    receptor = create_decoder_receptor(reactants=(receptor_queue,), decoder=decode_json_bytes, loop=event_loop)
    synapse = SynapseZmqIPC("test", receptors=(receptor,), loop=event_loop)

    await asyncio.sleep(.25, loop=event_loop)

    foo_bar_dict = {"foo": "bar"}
    await transmit_encode((synapse,), encode_json_bytes, foo_bar_dict, loop=event_loop)

    data = await test_queue.get()
    assert data == foo_bar_dict
    test_queue.task_done()
