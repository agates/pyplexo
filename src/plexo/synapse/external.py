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
from typing import Optional, Iterable
from uuid import UUID

import zmq
from zmq.asyncio import Socket

from plexo.synapse.base import SynapseBase
from plexo.typing import EncodedSignal
from plexo.typing.receptor import Receptor


class SynapseExternal(SynapseBase):
    def __init__(
        self, topic: str, socket_pub: Socket, receptors: Iterable[Receptor] = ()
    ) -> None:
        super().__init__(topic, receptors)

        self._socket_pub: Socket = socket_pub

    async def transmit(self, data: EncodedSignal, reaction_id: Optional[UUID] = None):
        if self._socket_pub is not None:
            await self._socket_pub.send(self.topic_bytes, zmq.SNDMORE)
            await self._socket_pub.send(data)
