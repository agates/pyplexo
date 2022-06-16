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

import asyncio
import logging
from typing import Iterable, Optional
from uuid import UUID

import zmq
import zmq.asyncio
from zmq.asyncio import Socket

from plexo.exceptions import IpAddressIsNotMulticast
from plexo.host_information import get_primary_ip
from plexo.neuron.neuron import Neuron
from plexo.synapse.base import SynapseExternalBase
from plexo.typing import EncodedSignal, IPAddress, UnencodedSignal
from plexo.typing.reactant import Reactant, RawReactant


class SynapseZmqPubSubEPGM(SynapseExternalBase):
    def __init__(
        self,
        neuron: Neuron[UnencodedSignal],
        multicast_address: IPAddress,
        bind_interface: Optional[str] = None,
        port: int = 5560,
        reactants: Iterable[Reactant[UnencodedSignal]] = (),
        raw_reactants: Iterable[RawReactant[UnencodedSignal]] = (),
    ) -> None:
        super().__init__(neuron, reactants, raw_reactants)

        if not bind_interface:
            bind_interface = get_primary_ip()
        self.bind_interface = bind_interface
        logging.debug(f"SynapseZmqPubSubEPGM:{neuron}:bind_interface {bind_interface}")
        self.port = port
        logging.debug(f"SynapseZmqPubSubEPGM:{neuron}:port {port}")

        self._startup(multicast_address)

    def _startup(self, multicast_address: IPAddress):
        topic = self.neuron.name
        self._startup_done = False
        if not multicast_address.is_multicast:
            raise IpAddressIsNotMulticast(
                "Specified ip_address is not a multicast ip address"
            )
        self.multicast_address = multicast_address
        logging.debug(
            f"SynapseZmqPubSubEPGM:{topic}:multicast_address {multicast_address}"
        )
        self._zmq_context = zmq.asyncio.Context()
        self._socket_pub: Optional[Socket] = None
        self._socket_sub: Optional[Socket] = None
        self.connection_string = "epgm://{};{}:{}".format(
            self.bind_interface, multicast_address.compressed, self.port
        )
        logging.debug(
            f"SynapseZmqPubSubEPGM:{topic}:connection_string {self.connection_string}"
        )
        self._create_socket_pub()
        self._start_recv_loop_if_needed()
        self._startup_done = True

    def close(self):
        try:
            super().close()
        finally:
            if self._socket_sub:
                self._socket_sub.close()
            if self._socket_pub:
                self._socket_pub.close()

    def update(self, multicast_address: IPAddress):
        self.close()
        self._startup(multicast_address)

    async def add_reactants(self, reactants: Iterable[Reactant[UnencodedSignal]]):
        await super().add_reactants(reactants)
        self._start_recv_loop_if_needed()

    def _create_socket_pub(self):
        logging.debug(f"SynapseZmqPubSubEPGM:{self.neuron}:Creating publisher")
        self._socket_pub = self._zmq_context.socket(zmq.PUB)

        # this conditional is only to satisfy mypy (I think it's a bug)
        if self._socket_pub is not None:
            self._socket_pub.bind(self.connection_string)

    def _create_socket_sub(self):
        logging.debug(f"SynapseZmqPubSubEPGM:{self.neuron}:Creating subscription")
        self._socket_sub = self._zmq_context.socket(zmq.SUB)

        # this conditional is only to satisfy mypy (I think it's a bug)
        if self._socket_sub is not None:
            self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, self.neuron.name)
            self._socket_sub.connect(self.connection_string)

    @property
    def socket_sub(self):
        if not self._socket_sub:
            self._create_socket_sub()

        return self._socket_sub

    async def transmit(
        self,
        data: EncodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        if self._socket_pub is not None:
            await self._socket_pub.send(self.topic_bytes, zmq.SNDMORE)
            await self._socket_pub.send(data)

    def _start_recv_loop_if_needed(self):
        if len(self._receptor.reactants):
            logging.debug(f"SynapseZmqPubSubEPGM:{self.neuron}:Starting _recv_loop")
            self._add_task(asyncio.create_task(self._recv_loop()))
        else:
            logging.debug(
                "SynapseZmqPubSubEPGM:{}:Not starting _recv_loop - no receptors found".format(
                    self.neuron
                )
            )

    async def _recv_loop(self):
        topic = self.neuron.name

        while True:
            try:
                data = (await self.socket_sub.recv_multipart())[1]
                await self.transduce(data)
            except AttributeError:
                # Error/exit if the socket no longer exists
                raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(
                    f"SynapseZmqPubSubEPGM:{topic}:_recv_loop: {e}", stack_info=True
                )
                continue
