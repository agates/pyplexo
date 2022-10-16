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

from typing import Optional, Iterable
from uuid import UUID

import zmq
from zmq.asyncio import Socket

from plexo.neuron.neuron import Neuron
from plexo.synapse.base import SynapseExternalBase
from plexo.typing import EncodedSignal, UnencodedSignal
from plexo.typing.reactant import Reactant, RawReactant


class SynapseZmqBasicPub(SynapseExternalBase):
    def __init__(
        self,
        neuron: Neuron[UnencodedSignal],
        socket_pub: Socket,
        reactants: Iterable[Reactant[UnencodedSignal]] = (),
        raw_reactants: Iterable[RawReactant[UnencodedSignal]] = (),
    ) -> None:
        super().__init__(neuron, reactants, raw_reactants)

        self._socket_pub: Socket = socket_pub

    async def transmit(
        self,
        data: EncodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        await self._socket_pub.send(self.topic_bytes, zmq.SNDMORE)
        await self._socket_pub.send(data)
