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

import logging

from plexo.exceptions import SynapseExists
from plexo.ganglion.internal import GanglionInternalBase
from plexo.neuron.neuron import Neuron
from plexo.synapse.inproc import SynapseInproc
from plexo.typing import UnencodedSignal


class GanglionInproc(GanglionInternalBase):
    async def _create_synapse_by_name(self, neuron: Neuron[UnencodedSignal], name: str):
        if name in self._synapses:
            raise SynapseExists(f"Synapse for {name} already exists.")

        logging.debug(f"GanglionInproc:Creating synapse for type {name}")

        synapse: SynapseInproc = SynapseInproc(neuron)

        async with self._synapses_lock:
            self._synapses = self._synapses.set(name, synapse)

        return synapse

    async def _create_synapse(self, neuron: Neuron):
        return await self._create_synapse_by_name(neuron, neuron.name)
