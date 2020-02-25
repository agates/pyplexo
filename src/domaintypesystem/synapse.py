#  domain-type-system
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
import logging
from abc import ABC, abstractmethod
import asyncio
from asyncio import Future
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Iterable, Set, Tuple, Union, ByteString, Generic

from pyrsistent import pvector
import zmq
import zmq.asyncio

from domaintypesystem import DTSReceptorBase
from domaintypesystem.types import UnencodedDataType


class DTSSynapseBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[DTSReceptorBase[UnencodedDataType]] = ()) -> None:
        self._topic = topic
        self._receptors = pvector(receptors)
        self._receptors_lock = asyncio.Lock()

    async def add_receptor(self, receptor: DTSReceptorBase[UnencodedDataType]) -> None:
        async with self._receptors_lock:
            self._receptors = self._receptors.append(receptor)

    @abstractmethod
    async def pass_data(self, data): ...


class DTSInProcessSynapse(DTSSynapseBase, Generic[UnencodedDataType]):
    async def pass_data(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        async with self._receptors_lock:
            return await asyncio.wait([receptor.activate(data) for receptor in self._receptors])


class DTSZmqIpcSynapse(DTSSynapseBase, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[DTSReceptorBase[UnencodedDataType]] = (),
                 directory: Path = None,
                 loop=None) -> None:
        super(DTSZmqIpcSynapse, self).__init__(topic, receptors)

        if not directory:
            directory = Path("/tmp/dts/zmq")

        directory.mkdir(parents=True, exist_ok=True)

        if not directory.is_dir():
            raise Exception("Given path is not a directory")

        self._directory = directory
        topic_uri = "ipc://{0}/{1}".format(directory, topic)

        context = zmq.asyncio.Context()

        # noinspection PyUnresolvedReferences
        self._socket_pub = context.socket(zmq.PUB, io_loop=loop)
        self._socket_pub.connect(topic_uri)
        # noinspection PyUnresolvedReferences
        self._socket_sub = context.socket(zmq.SUB, io_loop=loop)
        self._socket_sub.bind(topic_uri)
        # noinspection PyUnresolvedReferences
        self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, "")

        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        task = self._recv_loop()
        loop.create_task(task)

    async def pass_data(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        return await self._socket_pub.send(data)

    async def _recv_loop(self):
        loop = self.loop
        receptors_lock = self._receptors_lock
        socket_sub = self._socket_sub

        while True:
            data = await socket_sub.recv()
            async with receptors_lock:
                await asyncio.wait([receptor.activate(data) for receptor in self._receptors], loop=loop)


class DTSZmqEpgmSynapse(DTSSynapseBase, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 ip_address: Union[IPv4Address, IPv6Address],
                 port: int = 5555,
                 receptors: Iterable[DTSReceptorBase[UnencodedDataType]] = (),
                 loop=None) -> None:
        super(DTSZmqEpgmSynapse, self).__init__(topic, receptors)

        if not ip_address.is_multicast:
            raise Exception("Specified ip_address is not a multicast ip address")

        self.multicast_group = ip_address

        context = zmq.asyncio.Context()

        # noinspection PyUnresolvedReferences
        self._socket_pub = context.socket(zmq.PUB, io_loop=loop)
        self._socket_pub.connect("epgm://{}:{}".format(ip_address.compressed, port))

        # noinspection PyUnresolvedReferences
        self._socket_sub = context.socket(zmq.SUB, io_loop=loop)
        # noinspection PyUnresolvedReferences
        self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, "")
        self._socket_sub.bind("epgm://{}:{}".format(ip_address.compressed, port))

        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        task = self._recv_loop()
        loop.create_task(task)

    async def pass_data(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        return await self._socket_pub.send(data)

    async def _recv_loop(self):
        topic = self._topic
        loop = self.loop
        socket_sub = self._socket_sub

        while True:
            try:
                data = await socket_sub.recv()
                await asyncio.wait([receptor.activate(data) for receptor in self._receptors], loop=loop)
            except Exception as e:
                logging.debug("{}:_recv_loop: {}".format(topic, e))
                continue
