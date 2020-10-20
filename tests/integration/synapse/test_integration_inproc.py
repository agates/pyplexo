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
from itertools import repeat

import pytest

from plexo.receptor import create_receptor
from plexo.synapse.inproc import SynapseInproc
from plexo.transmitter import create_transmitter


@pytest.mark.asyncio
@pytest.mark.parametrize("stub_count,transmit_count",
                         tuple((n, m) for n in range(1, 5) for m in range(1, 5))
                         )
async def test_inprocess_receptor_transmit_multiple(mocker, stub_count, transmit_count):
    def make_stub_async(stub):
        async def stub_async(_):
            return stub(_)

        return stub_async

    stubs = tuple(mocker.stub() for _ in range(stub_count))
    receptor = create_receptor(reactants=(make_stub_async(stub) for stub in stubs))
    synapse = SynapseInproc("test", receptors=(receptor,))
    transmitter = create_transmitter((synapse,))

    foo_bar_dict = {"foo": "bar"}
    await asyncio.wait(tuple(t(foo_bar_dict) for t in repeat(transmitter, transmit_count)))

    for stub in stubs:
        stub.assert_called_with(foo_bar_dict)
        assert stub.call_count == transmit_count
