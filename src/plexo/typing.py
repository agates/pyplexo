#  pyplexo
#   Copyright (C) 2019  Alecks Gates
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
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from typing import TypeVar, Union, ByteString, Callable, Any

E = Union[ByteString, bytes]
U = TypeVar('U')
D = Union[E, U]

Decoder = Callable[[E], U]
Encoder = Callable[[U], E]
DecodedReactant = Callable[[U], Any]
Reactant = Callable[[D], Any]

IPAddress = Union[IPv4Address, IPv6Address]
IPNetwork = Union[IPv4Network, IPv6Network]
