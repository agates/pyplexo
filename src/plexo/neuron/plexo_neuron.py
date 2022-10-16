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

from plexo.codec.plexo_codec import (
    plexo_approval_codec,
    plexo_heartbeat_codec,
    plexo_preparation_codec,
    plexo_promise_codec,
    plexo_proposal_codec,
    plexo_rejection_codec,
)
from plexo.namespace import plexo_namespace
from plexo.neuron.neuron import Neuron
from plexo.schema.plexo_approval import PlexoApproval
from plexo.schema.plexo_heartbeat import PlexoHeartbeat
from plexo.schema.plexo_preparation import PlexoPreparation
from plexo.schema.plexo_promise import PlexoPromise
from plexo.schema.plexo_proposal import PlexoProposal
from plexo.schema.plexo_rejection import PlexoRejection


approval_neuron = Neuron(PlexoApproval, plexo_namespace, plexo_approval_codec)
heartbeat_neuron = Neuron(PlexoHeartbeat, plexo_namespace, plexo_heartbeat_codec)
preparation_neuron = Neuron(PlexoPreparation, plexo_namespace, plexo_preparation_codec)
promise_neuron = Neuron(PlexoPromise, plexo_namespace, plexo_promise_codec)
proposal_neuron = Neuron(PlexoProposal, plexo_namespace, plexo_proposal_codec)
rejection_neuron = Neuron(PlexoRejection, plexo_namespace, plexo_rejection_codec)
