#  pyplexo
#   Copyright (C) 2020  Alecks Gates
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

class ConsensusNotReached(RuntimeError):
    """Raise when a multicast ganglion cannot come to a consensus for a type"""


class IpLeaseExists(RuntimeError):
    """Raise when an ip_address is already leased"""


class IpNotFound(KeyError):
    """Raise when an ip_address is not found"""


class IpNotLeased(RuntimeError):
    """Raise when an ip_address is not leased"""


class IpsExhausted(RuntimeError):
    """Raise when no more ip_addresses are available"""


class PreparationRejection(RuntimeError):
    """Raise when a preparation is rejected by the consensus"""


class ProposalPromiseNotMade(RuntimeError):
    """Raise when a promise has not been made for a proposal"""


class ProposalNotLatest(RuntimeError):
    """Raise when a newer proposal has been promised"""


class SynapseExists(RuntimeError):
    """Raise when a synapse for a type already exists inside a ganglion"""


class TransmitterNotFound(KeyError):
    """Raise when a transmitter is not found inside a ganglion"""
