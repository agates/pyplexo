#  pyplexo
#  Copyright © 2018-2023  Alecks Gates
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

# python 3.10+ is required for isinstance to work on Union
# https://peps.python.org/pep-0604/#isinstance-and-issubclass
# This union allows encoded data to be strings or bytes depending on the protocol
EncodedType = Union[ByteString, str]
UnencodedType = TypeVar("UnencodedType")
Signal = Union[EncodedType, UnencodedType]
Decoder = Callable[[EncodedType], UnencodedType]
Encoder = Callable[[UnencodedType], EncodedType]
IPAddress = Union[IPv4Address, IPv6Address]
IPNetwork = Union[IPv4Network, IPv6Network]
