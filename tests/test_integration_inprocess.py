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
from domaintypesystem.synapse import DTSInProcessSynapse
from domaintypesystem.transmitter import DTSTransmitter


@pytest.mark.asyncio
@pytest.mark.parametrize("stub_count,transmit_count",
                         tuple((n, m) for n in range(1, 5) for m in range(1, 5))
                         )
async def test_inprocess_receptor_transmit_multiple(mocker, stub_count, transmit_count):
    json_decoder = json.JSONDecoder()
    json_encoder = json.JSONEncoder()

    def make_stub_async(stub):
        async def stub_async(_):
            return stub(_)

        return stub_async

    stubs = tuple(mocker.stub() for _ in range(stub_count))
    receptor = DTSReceptor[str, dict]((make_stub_async(stub) for stub in stubs), json_decoder)
    ipc_synapse = DTSInProcessSynapse[str]("test", receptors=(receptor,))
    transmitter = DTSTransmitter[dict, str](ipc_synapse, json_encoder)

    foo_bar_dict = {"foo": "bar"}
    await asyncio.wait(tuple(transmitter.transmit(foo_bar_dict) for _ in range(transmit_count)))

    for stub in stubs:
        stub.assert_called_with(foo_bar_dict)
        assert stub.call_count == transmit_count


@pytest.mark.asyncio
@pytest.mark.parametrize("stub_count,transmitter_count",
                         tuple((n, m) for n in range(1, 5) for m in range(1, 5))
                         )
async def test_inprocess_receptor_many_transmitters(mocker, stub_count, transmitter_count):
    json_decoder = json.JSONDecoder()
    json_encoder = json.JSONEncoder()

    def make_stub_async(stub):
        async def stub_async(_):
            return stub(_)

        return stub_async

    stubs = tuple(mocker.stub() for _ in range(stub_count))
    receptor = DTSReceptor[str, dict]((make_stub_async(stub) for stub in stubs), json_decoder)
    ipc_synapse = DTSInProcessSynapse[str]("test", receptors=(receptor,))
    transmitters = (DTSTransmitter[dict, str](ipc_synapse, json_encoder) for _ in range(transmitter_count))

    foo_bar_dict = {"foo": "bar"}
    await asyncio.wait(tuple(transmitter.transmit(foo_bar_dict) for transmitter in transmitters))

    for stub in stubs:
        stub.assert_called_with(foo_bar_dict)
        assert stub.call_count == transmitter_count


@pytest.mark.asyncio
@pytest.mark.parametrize("stub_count,transmit_count",
                         tuple((n, m) for n in range(1, 5) for m in range(1, 5))
                         )
async def test_inprocess_many_receptors_transmit_multiple(mocker, stub_count, transmit_count):
    json_decoder = json.JSONDecoder()
    json_encoder = json.JSONEncoder()

    def generate_receptor(stub):
        async def stub_async(_):
            return stub(_)

        return DTSReceptor[str, dict]((stub_async,), json_decoder)

    stubs = tuple(mocker.stub() for _ in range(stub_count))
    receptors = (generate_receptor(stub) for stub in stubs)
    ipc_synapse = DTSInProcessSynapse[str]("test", receptors=receptors)
    transmitter = DTSTransmitter[dict, str](ipc_synapse, json_encoder)

    foo_bar_dict = {"foo": "bar"}
    await asyncio.wait(tuple(transmitter.transmit(foo_bar_dict) for _ in range(transmit_count)))

    for stub in stubs:
        stub.assert_called_with(foo_bar_dict)
        assert stub.call_count == transmit_count


@pytest.mark.asyncio
@pytest.mark.parametrize("stub_count,transmitter_count",
                         tuple((n, m) for n in range(1, 5) for m in range(1, 5))
                         )
async def test_inprocess_many_receptors_many_transmitters(mocker, stub_count, transmitter_count):
    json_decoder = json.JSONDecoder()
    json_encoder = json.JSONEncoder()

    def generate_receptor(stub):
        async def stub_async(_):
            return stub(_)

        return DTSReceptor[str, dict]((stub_async,), json_decoder)

    stubs = tuple(mocker.stub() for _ in range(stub_count))
    receptors = (generate_receptor(stub) for stub in stubs)
    ipc_synapse = DTSInProcessSynapse[str]("test", receptors=receptors)
    transmitters = (DTSTransmitter[dict, str](ipc_synapse, json_encoder) for _ in range(transmitter_count))

    foo_bar_dict = {"foo": "bar"}
    await asyncio.wait(tuple(transmitter.transmit(foo_bar_dict) for transmitter in transmitters))

    for stub in stubs:
        stub.assert_called_with(foo_bar_dict)
        assert stub.call_count == transmitter_count
