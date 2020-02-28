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
import socket
from typing import Iterable, Set, Tuple, Union, ByteString, Generic

from pyrsistent import pvector
import zmq
import zmq.asyncio

from domaintypesystem.receptor import DTSReceptorBase, DTSReceptorInProcessBase
from domaintypesystem.typing import UnencodedDataType


def get_primary_ip():
    # from https://stackoverflow.com/a/28950776
    _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # noinspection PyBroadException
    try:
        # doesn't even have to be reachable
        _socket.connect(('10.255.255.255', 1))
        ip_address = _socket.getsockname()[0]
    except:
        ip_address = '127.0.0.1'
    finally:
        _socket.close()

    return ip_address


class DTSSynapseBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[DTSReceptorBase[UnencodedDataType]] = ()) -> None:
        self.topic = topic
        self.receptors = pvector(receptors)
        self.receptors_lock = asyncio.Lock()

    async def add_receptor(self, receptor: DTSReceptorBase[UnencodedDataType]) -> None:
        async with self.receptors_lock:
            self.receptors = self.receptors.append(receptor)

    @abstractmethod
    async def shift(self, data): ...


class DTSSynapseZmqIPC(DTSSynapseBase, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[DTSReceptorBase[UnencodedDataType]] = (),
                 directory: Path = None,
                 loop=None) -> None:
        super(DTSSynapseZmqIPC, self).__init__(topic, receptors)

        self._tasks = []

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

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._tasks.append(loop.create_task(self._recv_loop()))

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
            self._socket_sub.close()
            self._socket_pub.close()

    async def shift(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        return await self._socket_pub.send(data)

    async def _recv_loop(self):
        topic = self.topic
        loop = self._loop
        socket_sub = self._socket_sub

        while True:
            try:
                data = await socket_sub.recv()
                async with self.receptors_lock:
                    await asyncio.wait([receptor.activate(data) for receptor in self.receptors], loop=loop)
            except Exception as e:
                logging.debug("DTSSynapseZmqIPC:{}:_recv_loop: {}".format(topic, e))
                continue


class DTSSynapseZmqEPGM(DTSSynapseBase, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 multicast_address: Union[IPv4Address, IPv6Address],
                 bind_interface: str = None,
                 port: int = 5560,
                 receptors: Iterable[DTSReceptorBase[UnencodedDataType]] = (),
                 loop=None) -> None:
        super(DTSSynapseZmqEPGM, self).__init__(topic, receptors)

        self._tasks = []

        if not multicast_address.is_multicast:
            raise Exception("Specified ip_address is not a multicast ip address")

        if not bind_interface:
            bind_interface = get_primary_ip()

        self.bind_interface = bind_interface
        logging.info("DTSZmqEpgmSynapse:{}:Binding to interface {}".format(topic, bind_interface))
        self.multicast_address = multicast_address
        logging.info("DTSZmqEpgmSynapse:{}:Binding to multicast_address {}".format(topic, multicast_address))
        self.port = port
        logging.info("DTSZmqEpgmSynapse:{}:Binding to port {}".format(topic, port))

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

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._tasks.append(loop.create_task(self._recv_loop()))

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
            self._socket_sub.close()
            self._socket_pub.close()

    async def shift(self, data: ByteString) -> Tuple[Set[Future], Set[Future]]:
        return await self._socket_pub.send(data)

    async def _recv_loop(self):
        topic = self.topic
        loop = self._loop
        socket_sub = self._socket_sub

        while True:
            try:
                data = await socket_sub.recv()
                async with self.receptors_lock:
                    await asyncio.wait([receptor.activate(data) for receptor in self.receptors], loop=loop)
            except Exception as e:
                logging.debug("DTSZmqEpgmSynapse:{}:_recv_loop: {}".format(topic, e))
                continue


class DTSSynapseInProcessBase(ABC, Generic[UnencodedDataType]):
    def __init__(self, topic: str,
                 receptors: Iterable[DTSReceptorInProcessBase[UnencodedDataType]] = ()) -> None:
        self.topic = topic
        self.receptors = pvector(receptors)
        self.receptors_lock = asyncio.Lock()

    async def add_receptor(self, receptor: DTSReceptorInProcessBase[UnencodedDataType]) -> None:
        async with self.receptors_lock:
            self.receptors = self.receptors.append(receptor)

    @abstractmethod
    async def shift(self, data): ...


class DTSSynapseInProcess(DTSSynapseInProcessBase, Generic[UnencodedDataType]):
    async def shift(self, data: UnencodedDataType) -> Tuple[Set[Future], Set[Future]]:
        async with self.receptors_lock:
            return await asyncio.wait([receptor.activate(data) for receptor in self.receptors])
