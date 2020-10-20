#  pyplexo
#   Copyright © 2018-2020  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
import logging
from asyncio.futures import Future
from typing import Iterable, Any, Tuple, Set, Optional

import zmq
import zmq.asyncio

from plexo.exceptions import IpAddressIsNotMulticast
from plexo.host_information import get_primary_ip
from plexo.synapse.base import SynapseBase
from plexo.typing import E, Reactant, IPAddress


class SynapseZmqEPGM(SynapseBase):
    def __init__(self, topic: str,
                 multicast_address: IPAddress,
                 bind_interface: Optional[str] = None,
                 port: int = 5560,
                 receptors: Iterable[Reactant] = (),
                 loop=None) -> None:
        super(SynapseZmqEPGM, self).__init__(topic, receptors, loop=loop)

        if not bind_interface:
            bind_interface = get_primary_ip()
        self.bind_interface = bind_interface
        logging.debug("SynapseZmqEPGM:{}:bind_interface {}".format(topic, bind_interface))
        self.port = port
        logging.debug("SynapseZmqEPGM:{}:port {}".format(topic, port))

        self._startup(multicast_address)

    def _startup(self, multicast_address: IPAddress):
        topic = self.topic
        self._startup_done = False
        if not multicast_address.is_multicast:
            raise IpAddressIsNotMulticast("Specified ip_address is not a multicast ip address")
        self.multicast_address = multicast_address
        logging.debug("SynapseZmqEPGM:{}:multicast_address {}".format(topic, multicast_address))
        self._zmq_context = zmq.asyncio.Context()
        self._socket_pub: Optional[Any] = None
        self._socket_sub: Optional[Any] = None
        self.connection_string = "epgm://{};{}:{}".format(self.bind_interface, multicast_address.compressed, self.port)
        logging.debug("SynapseZmqEPGM:{}:connection_string {}".format(topic, self.connection_string))
        self._create_socket_pub()
        self._start_recv_loop_if_needed()
        self._startup_done = True

    def close(self):
        try:
            super(SynapseZmqEPGM, self).close()
        finally:
            if self._socket_sub:
                self._socket_sub.close()
            if self._socket_pub:
                self._socket_pub.close()

    def update(self, multicast_address: IPAddress):
        self.close()
        self._startup(multicast_address)

    async def update_receptors(self, receptors: Iterable[Reactant]):
        await super(SynapseZmqEPGM, self).update_receptors(receptors)
        self._start_recv_loop_if_needed()

    def _create_socket_pub(self):
        logging.debug("SynapseZmqEPGM:{}:Creating publisher".format(self.topic))
        # noinspection PyUnresolvedReferences
        self._socket_pub = self._zmq_context.socket(zmq.PUB, io_loop=self._loop)
        self._socket_pub.bind(self.connection_string)

    def _create_socket_sub(self):
        logging.debug("SynapseZmqEPGM:{}:Creating subscription".format(self.topic))
        # noinspection PyUnresolvedReferences
        self._socket_sub = self._zmq_context.socket(zmq.SUB, io_loop=self._loop)
        # noinspection PyUnresolvedReferences
        self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, self.topic)
        self._socket_sub.connect(self.connection_string)

    @property
    def socket_sub(self):
        if not self._socket_sub:
            self._create_socket_sub()

        return self._socket_sub

    async def transmit(self, data: E) -> Tuple[Set[Future], Set[Future]]:
        # noinspection PyUnresolvedReferences
        await self._socket_pub.send(self.topic_bytes, zmq.SNDMORE)  # type: ignore
        return await self._socket_pub.send(data)  # type: ignore

    def _start_recv_loop_if_needed(self):
        if len(self.receptors):
            logging.debug("SynapseZmqEPGM:{}:Starting _recv_loop".format(self.topic))
            self._add_task(self._loop.create_task(self._recv_loop()))
        else:
            logging.debug("SynapseZmqEPGM:{}:Not starting _recv_loop - no receptors found".format(self.topic))

    async def _recv_loop(self):
        loop = self._loop
        topic = self.topic

        while True:
            try:
                data = (await self.socket_sub.recv_multipart())[1]
                await asyncio.wait([receptor(data) for receptor in self.receptors], loop=loop)
            except AttributeError:
                # Error/exit if the socket no longer exists
                raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error("SynapseZmqEPGM:{}:_recv_loop: {}".format(topic, e), stack_info=True)
                continue
