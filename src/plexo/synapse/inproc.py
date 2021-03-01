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
from typing import Any

from plexo.synapse.base import SynapseBase


class SynapseInproc(SynapseBase):
    async def transmit(self, data: Any):
        try:
            return await asyncio.gather(*(receptor(data) for receptor in self.receptors), loop=self._loop)
        except ValueError:
            # Got empty list, continue
            pass
