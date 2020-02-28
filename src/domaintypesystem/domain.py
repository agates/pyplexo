#  domain-type-system
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
import asyncio
from abc import ABC, abstractmethod
from ipaddress import IPv4Network, IPv6Network
from typing import Union, Type, Callable, Any

from domaintypesystem import UnencodedDataType


class DTSDomainBase(ABC):
    @abstractmethod
    async def react(self, _type: Type, reactant: Callable[[UnencodedDataType], Any]): ...

    @abstractmethod
    async def transmit(self, data: UnencodedDataType): ...


class DTSDomainMulticast(DTSDomainBase):
    def __init__(self, bind_interface: str = None,
                 multicast_cidr: Union[IPv4Network, IPv6Network] = None,
                 port: int = 5560,
                 loop=None) -> None:

        self._tasks = []

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            pass

    async def _heartbeat_loop(self):
        pass

    async def _heartbeat_reaction(self, heartbeat):
        pass

    async def react(self, _type: Type, reactant: Callable[[UnencodedDataType], Any]):
        pass

    async def transmit(self, data: UnencodedDataType):
        pass
