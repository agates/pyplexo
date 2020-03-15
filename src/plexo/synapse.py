#  pyplexo
#   Copyright (C) 2019-2020  Alecks Gates
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
import logging
from abc import ABC, abstractmethod
from asyncio import Future
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Iterable, Set, Tuple, Union, ByteString, Generic, Callable, Any

import zmq
import zmq.asyncio
from pyrsistent import pdeque, pset

from plexo.host_information import get_primary_ip
from plexo.typing import UnencodedDataType


class SynapseBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[Callable[[Union[ByteString, UnencodedDataType]], Any]] = (),
                 loop=None) -> None:
        self.topic = topic
        self._receptors = pset(receptors)
        self._receptors_write_lock = asyncio.Lock()

        self._tasks = pdeque()

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

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    @property
    def receptors(self):
        return self._receptors

    async def update_receptors(self, receptors: Iterable[Callable[[Union[ByteString, UnencodedDataType]], Any]]):
        async with self._receptors_write_lock:
            self._receptors = self._receptors.update(receptors)

    @abstractmethod
    async def transmit(self, data): ...


class SynapseZmqIPC(SynapseBase, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[Callable[[Union[ByteString, UnencodedDataType]], Any]] = (),
                 directory: Path = None,
                 loop=None) -> None:
        super(SynapseZmqIPC, self).__init__(topic, receptors)

        self._tasks = pdeque()

        if not directory:
            directory = Path("/tmp/dts/zmq")

        directory.mkdir(parents=True, exist_ok=True)

        if not directory.is_dir():
            raise Exception("Given path is not a directory")

        self._directory = directory
        topic_uri = "ipc://{0}/{1}".format(directory, topic)

        zmq_context = zmq.asyncio.Context()
        self._zmq_context = zmq_context

        # noinspection PyUnresolvedReferences
        self._socket_pub = zmq_context.socket(zmq.PUB, io_loop=loop)
        self._socket_pub.connect(topic_uri)
        # noinspection PyUnresolvedReferences
        self._socket_sub = zmq_context.socket(zmq.SUB, io_loop=loop)
        self._socket_sub.bind(topic_uri)
        # noinspection PyUnresolvedReferences
        self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, "")

        self._add_task(loop.create_task(self._recv_loop()))

    def close(self):
        try:
            super(SynapseZmqIPC, self).close()
        finally:
            if self._socket_sub:
                self._socket_sub.close()
            if self._socket_pub:
                self._socket_pub.close()

    async def transmit(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        return await self._socket_pub.send(data)

    async def _recv_loop(self):
        topic = self.topic
        loop = self._loop
        socket_sub = self._socket_sub

        while True:
            try:
                data = await socket_sub.recv()
                await asyncio.wait([receptor(data) for receptor in self.receptors], loop=loop)
            except Exception as e:
                logging.error("SynapseZmqIPC:{}:_recv_loop: {}".format(topic, e))
                continue


class SynapseZmqEPGM(SynapseBase, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 multicast_address: Union[IPv4Address, IPv6Address],
                 bind_interface: str = None,
                 port: int = 5560,
                 receptors: Iterable[Callable[[Union[ByteString, UnencodedDataType]], Any]] = (),
                 loop=None) -> None:
        super(SynapseZmqEPGM, self).__init__(topic, receptors, loop=loop)

        if not multicast_address.is_multicast:
            raise Exception("Specified ip_address is not a multicast ip address")

        if not bind_interface:
            bind_interface = get_primary_ip()

        self.bind_interface = bind_interface
        logging.debug("SynapseZmqEPGM:{}:Binding to interface {}".format(topic, bind_interface))
        self.multicast_address = multicast_address
        logging.debug("SynapseZmqEPGM:{}:Binding to multicast_address {}".format(topic, multicast_address))
        self.port = port
        logging.debug("SynapseZmqEPGM:{}:Binding to port {}".format(topic, port))

        zmq_context = zmq.asyncio.Context()
        self._zmq_context = zmq_context

        # noinspection PyUnresolvedReferences
        self._socket_pub = zmq_context.socket(zmq.PUB, io_loop=loop)
        self._socket_pub.connect("epgm://{};{}:{}".format(
            bind_interface,
            multicast_address.compressed,
            port)
        )

        # noinspection PyUnresolvedReferences
        self._socket_sub = zmq_context.socket(zmq.SUB, io_loop=loop)
        # noinspection PyUnresolvedReferences
        self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, "")
        self._socket_sub.bind("epgm://{};{}:{}".format(
            bind_interface,
            multicast_address.compressed,
            port)
        )

        self._add_task(loop.create_task(self._recv_loop()))

    def close(self):
        try:
            super(SynapseZmqEPGM, self).close()
        finally:
            if self._socket_sub:
                self._socket_sub.close()
            if self._socket_pub:
                self._socket_pub.close()

    async def transmit(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        return await self._socket_pub.send(data)

    async def _recv_loop(self):
        topic = self.topic
        loop = self._loop
        socket_sub = self._socket_sub

        while True:
            try:
                data = await socket_sub.recv()
                await asyncio.wait([receptor(data) for receptor in self.receptors], loop=loop)
            except Exception as e:
                logging.error("SynapseZmqEPGM:{}:_recv_loop: {}".format(topic, e))
                continue


class SynapseInproc(SynapseBase, Generic[UnencodedDataType]):
    async def transmit(self, data: UnencodedDataType) -> Tuple[Set[Future], Set[Future]]:
        return await asyncio.wait([receptor(data) for receptor in self.receptors], loop=self._loop)
