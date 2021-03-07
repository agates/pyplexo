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
import logging

from plexo.neuron.neuron import Neuron
from plexo.exceptions import SynapseExists
from plexo.ganglion.internal import GanglionInternalBase
from plexo.synapse.inproc import SynapseInproc


class GanglionInproc(GanglionInternalBase):
    async def _create_synapse_by_name(self, name: str):
        if name in self._synapses:
            raise SynapseExists("Synapse for {} already exists.".format(name))

        logging.debug("GanglionInproc:Creating synapse for type {}".format(name))

        synapse: SynapseInproc = SynapseInproc(topic=name, loop=self._loop)

        async with self._synapses_lock:
            self._synapses = self._synapses.set(name, synapse)

        return synapse

    async def _create_synapse(self, neuron: Neuron):
        return await self._create_synapse_by_name(neuron.name)
