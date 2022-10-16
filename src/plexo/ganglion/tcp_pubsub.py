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
from typing import Iterable, Optional, Tuple, Type

import zmq
import zmq.asyncio
from pyrsistent import pvector
from zmq.asyncio import Socket

from plexo.exceptions import SynapseExists, NeuronNotFound

from plexo.ganglion.external import GanglionExternalBase
from plexo.host_information import get_primary_ip
from plexo.neuron.neuron import Neuron
from plexo.synapse.zeromq_basic_pub import SynapseZmqBasicPub
from plexo.typing import UnencodedSignal, IPAddress
from plexo.typing.reactant import Reactant, RawReactant
from plexo.typing.synapse import SynapseExternal


class GanglionZmqTcpPubSub(GanglionExternalBase):
    def __init__(
        self,
        bind_interface: Optional[str] = None,
        port_pub: int = 5570,
        peers: Iterable[Tuple[IPAddress, int]] = (),
        relevant_neurons: Iterable[Neuron] = (),
        ignored_neurons: Iterable[Neuron] = (),
        allowed_codecs: Iterable[Type] = (),
    ) -> None:
        super().__init__(
            relevant_neurons=relevant_neurons,
            ignored_neurons=ignored_neurons,
            allowed_codecs=allowed_codecs,
        )
        if not bind_interface:
            bind_interface = get_primary_ip()
        self.bind_interface = bind_interface
        logging.debug(f"GanglionZmqTcpPubSub:bind_interface {bind_interface}")
        self.port_pub = port_pub
        logging.debug(f"GanglionZmqTcpPubSub:port_pub {port_pub}")
        self.peers = pvector(peers)

        # Unique id for the current instance, first 64 bits of uuid1
        # Not random but should include the current time and be unique enough
        # self.instance_id = uuid.uuid1().int >> 64

        self._zmq_context = zmq.asyncio.Context()
        self._socket_pub: Optional[Socket] = None
        self._socket_sub: Optional[Socket] = None
        self.connection_string_pub = "tcp://{}:{}".format(
            self.bind_interface, self.port_pub
        )
        logging.debug(
            f"GanglionZmqTcpPubSub:connection_string_pub {self.connection_string_pub}"
        )

        self._recv_loop_running = False
        self._recv_loop_running_lock = asyncio.Lock()

        self._create_socket_pub()

        for peer in peers:
            self.connect_to_peer(*peer)

    def close(self):
        try:
            super().close()
        finally:
            if self._socket_sub:
                self._socket_sub.close()
            if self._socket_pub:
                self._socket_pub.close()

    def _create_socket_pub(self):
        logging.debug(f"GanglionZmqTcpPubSub:Creating publisher")
        self._socket_pub = self._zmq_context.socket(zmq.PUB)

        # this conditional is only to satisfy mypy (I think it's a bug)
        if self._socket_pub is not None:
            self._socket_pub.bind(self.connection_string_pub)
            self._socket_pub.setsockopt(zmq.LINGER, 0)
            self._socket_pub.setsockopt(zmq.IMMEDIATE, 1)

    def _create_socket_sub(self):
        logging.debug(f"GanglionZmqTcpPubSub:Creating subscription")
        self._socket_sub = self._zmq_context.socket(zmq.SUB)

        # this conditional is only to satisfy mypy (I think it's a bug)
        if self._socket_sub is not None:
            # TODO: Maybe optimize this for specific topics, not sure if it will modify behavior
            self._socket_sub.setsockopt_string(zmq.SUBSCRIBE, "")
            self._socket_sub.setsockopt(zmq.LINGER, 0)
            self._socket_sub.setsockopt(zmq.IMMEDIATE, 1)

    def connect_to_peer(self, address: IPAddress, port: int):
        connection_string = f"tcp://{address.compressed}:{port}"
        self.socket_sub.connect(connection_string)
        logging.debug(f"GanglionZmqTcpPubSub:connect_to_peer {connection_string}")

    @property
    def socket_sub(self):
        if not self._socket_sub:
            self._create_socket_sub()

        return self._socket_sub

    async def _create_synapse_by_name(self, neuron: Neuron[UnencodedSignal], name: str):
        if name in self._synapses:
            raise SynapseExists(f"Synapse for {name} already exists.")

        logging.debug(f"GanglionZmqTcpPubSub:Creating synapse for type {name}")

        if self._socket_pub is not None:
            synapse: SynapseZmqBasicPub = SynapseZmqBasicPub(
                neuron=neuron, socket_pub=self._socket_pub
            )

            async with self._synapses_lock:
                self._synapses = self._synapses.set(name, synapse)

            return synapse

    async def _create_synapse(self, neuron: Neuron[UnencodedSignal]):
        return await self._create_synapse_by_name(neuron, neuron.name)

    async def _start_recv_loop_if_needed(self):
        async with self._recv_loop_running_lock:
            if not self._recv_loop_running:
                if len(self._synapses):
                    logging.debug("GanglionZmqTcpPubSub:Starting _recv_loop")
                    self._recv_loop_running = True
                    self._add_task(asyncio.create_task(self._recv_loop()))
                else:
                    logging.debug(
                        "GanglionZmqTcpPubSub:Not starting _recv_loop - no synapses found"
                    )
            else:
                logging.debug(
                    "GanglionZmqTcpPubSub:Not starting _recv_loop - _recv_loop is already running"
                )

    async def _recv_loop(self):
        async with self._recv_loop_running_lock:
            self._recv_loop_running = True
        while True:
            try:
                name, data = await self.socket_sub.recv_multipart()
                synapse: SynapseExternal = await self.get_synapse_by_name(
                    name.decode("UTF-8")
                )
                await synapse.transduce(data)
            except AttributeError:
                # Error/exit if the socket no longer exists
                async with self._recv_loop_running_lock:
                    self._recv_loop_running = False
                raise
            except asyncio.CancelledError:
                async with self._recv_loop_running_lock:
                    self._recv_loop_running = False
                raise
            except NeuronNotFound as e:
                logging.warning(f"GanglionZmqTcpPubSub:_recv_loop: {e}")
            except Exception as e:
                logging.exception(f"GanglionZmqTcpPubSub:_recv_loop: {e}")

    async def adapt(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Optional[Iterable[Reactant[UnencodedSignal]]] = None,
        raw_reactants: Optional[Iterable[RawReactant[UnencodedSignal]]] = None,
    ):
        await super().adapt(neuron, reactants=reactants, raw_reactants=raw_reactants)

        await self._start_recv_loop_if_needed()
