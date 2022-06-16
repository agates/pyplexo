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


class NeuronNotAvailable(RuntimeError):
    """Raise when a Neuron is not relevant to a type"""


class NeuronNotFound(KeyError):
    """Raise when a Neuron does not exist in a ganglion"""


class ConsensusNotReached(RuntimeError):
    """Raise when a multicast ganglion cannot come to a consensus for a type"""


class IpAddressIsNotMulticast(RuntimeError):
    """Raise when a given ip_address is not a multicast address"""


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


class SynapseDoesNotExist(RuntimeError):
    """Raise when a synapse for a type does not exist inside a ganglion"""


class SynapseExists(RuntimeError):
    """Raise when a synapse for a type already exists inside a ganglion"""


class TransmitterNotFound(KeyError):
    """Raise when a transmitter is not found inside a ganglion"""
