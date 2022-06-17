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
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Callable, TypeVar, Union, ByteString

# If EncodedSignal is ever made into a Union,
# python 3.10+ will be required for isinstance to work
# https://peps.python.org/pep-0604/#isinstance-and-issubclass
# EncodedSignal = Union[ByteString, str]
EncodedSignal = ByteString
UnencodedSignal = TypeVar("UnencodedSignal")
Signal = Union[EncodedSignal, UnencodedSignal]
Decoder = Callable[[EncodedSignal], UnencodedSignal]
Encoder = Callable[[UnencodedSignal], EncodedSignal]
IPAddress = Union[IPv4Address, IPv6Address]
IPNetwork = Union[IPv4Network, IPv6Network]
