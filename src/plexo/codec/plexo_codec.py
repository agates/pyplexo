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

from plexo.codec.capnpy_codec import CapnpyCodec
from plexo.schema.plexo_approval import PlexoApproval
from plexo.schema.plexo_heartbeat import PlexoHeartbeat
from plexo.schema.plexo_message import PlexoMessage
from plexo.schema.plexo_preparation import PlexoPreparation
from plexo.schema.plexo_promise import PlexoPromise
from plexo.schema.plexo_proposal import PlexoProposal
from plexo.schema.plexo_rejection import PlexoRejection


plexo_approval_codec = CapnpyCodec(PlexoApproval)
plexo_heartbeat_codec = CapnpyCodec(PlexoHeartbeat)
plexo_message_codec = CapnpyCodec(PlexoMessage)
plexo_preparation_codec = CapnpyCodec(PlexoPreparation)
plexo_promise_codec = CapnpyCodec(PlexoPromise)
plexo_proposal_codec = CapnpyCodec(PlexoProposal)
plexo_rejection_codec = CapnpyCodec(PlexoRejection)
