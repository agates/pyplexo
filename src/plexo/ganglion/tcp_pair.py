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
import pickle
from typing import Iterable, Optional, Tuple, Type

import zmq
import zmq.asyncio
from zmq.asyncio import Socket

from plexo.codec.plexo_codec import plexo_message_codec
from plexo.exceptions import SynapseExists, NeuronNotFound

from plexo.ganglion.external import GanglionExternalBase
from plexo.host_information import get_primary_ip
from plexo.neuron.neuron import Neuron
from plexo.schema.plexo_message import PlexoMessage
from plexo.synapse.zeromq_basic import SynapseZmqBasic
from plexo.typing import UnencodedSignal, IPAddress
from plexo.typing.reactant import Reactant, RawReactant
from plexo.typing.synapse import SynapseExternal


class GanglionZmqTcpPair(GanglionExternalBase):
    def __init__(
        self,
        bind_interface: Optional[str] = None,
        port: int = 5580,
        peer: Optional[Tuple[IPAddress, int]] = None,
        relevant_neurons: Iterable[Neuron] = (),
        ignored_neurons: Iterable[Neuron] = (),
        allowed_codecs: Iterable[Type] = (),
    ) -> None:
        super().__init__(
            relevant_neurons=relevant_neurons,
            ignored_neurons=ignored_neurons,
            allowed_codecs=allowed_codecs,
        )
        self.bind_interface = None
        self.port = None
        self.peer = peer
        self.connection_string = None
        self.peer = None

        # Unique id for the current instance, first 64 bits of uuid1
        # Not random but should include the current time and be unique enough
        # self.instance_id = uuid.uuid1().int >> 64

        self._zmq_context = zmq.asyncio.Context()
        self._socket: Optional[Socket] = None

        self._recv_loop_running = False
        self._recv_loop_running_lock = asyncio.Lock()

        if peer is None:
            if not bind_interface:
                bind_interface = get_primary_ip()
            self.bind_interface = bind_interface
            logging.debug(f"GanglionZmqTcpPair:bind_interface {bind_interface}")
            self.port = port
            logging.debug(f"GanglionZmqTcpPair:port {port}")
            self.connection_string = "tcp://{}:{}".format(
                self.bind_interface, self.port
            )
            logging.debug(
                f"GanglionZmqTcpPair:connection_string {self.connection_string}"
            )

            self.bind_to_socket(self.connection_string)
        else:
            logging.debug(
                f"GanglionZmqTcpPair:connection_string not set, connecting to peer"
            )
            self.connect_to_peer(*peer)

    def close(self):
        try:
            super().close()
        finally:
            if self._socket:
                self._socket.close()

    def _create_socket(self):
        logging.debug(f"GanglionZmqTcpPair:Creating pair socket")
        self._socket = self._zmq_context.socket(zmq.PAIR)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.setsockopt(zmq.IMMEDIATE, 1)

    def bind_to_socket(self, connection_string: str):
        logging.debug(f"GanglionZmqTcpPair:bind_to_socket {connection_string}")
        self.socket.bind(connection_string)

    def connect_to_peer(self, address: IPAddress, port: int):
        connection_string = f"tcp://{address.compressed}:{port}"
        logging.debug(f"GanglionZmqTcpPair:connect_to_peer {connection_string}")
        self.socket.connect(connection_string)

    @property
    def socket(self):
        if not self._socket:
            self._create_socket()

        return self._socket

    async def _create_synapse_by_name(self, neuron: Neuron[UnencodedSignal], name: str):
        if name in self._synapses:
            raise SynapseExists(f"Synapse for {name} already exists.")

        logging.debug(f"GanglionZmqTcpPair:Creating synapse for type {name}")

        synapse: SynapseZmqBasic = SynapseZmqBasic(neuron=neuron, socket=self.socket)

        async with self._synapses_lock:
            self._synapses = self._synapses.set(name, synapse)

        return synapse

    async def _create_synapse(self, neuron: Neuron[UnencodedSignal]):
        return await self._create_synapse_by_name(neuron, neuron.name)

    async def _start_recv_loop_if_needed(self):
        async with self._recv_loop_running_lock:
            if not self._recv_loop_running:
                if len(self._synapses):
                    logging.debug("GanglionZmqTcpPair:Starting _recv_loop")
                    self._recv_loop_running = True
                    self._add_task(asyncio.create_task(self._recv_loop()))
                else:
                    logging.debug(
                        "GanglionZmqTcpPair:Not starting _recv_loop - no synapses found"
                    )
            else:
                logging.debug(
                    "GanglionZmqTcpPair:Not starting _recv_loop - _recv_loop is already running"
                )

    async def _recv_loop(self):
        async with self._recv_loop_running_lock:
            self._recv_loop_running = True
        while True:
            try:
                data = await self.socket.recv()
                message: PlexoMessage = plexo_message_codec.decode(data)
                synapse: SynapseExternal = await self.get_synapse_by_name(
                    message.type_name.decode("UTF-8")
                )
                await synapse.transduce(message.payload)
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
                logging.warning(f"GanglionZmqTcpPair:_recv_loop: {e}")
            except Exception as e:
                logging.exception(f"GanglionZmqTcpPair:_recv_loop: {e}")

    async def adapt(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Optional[Iterable[Reactant[UnencodedSignal]]] = None,
        raw_reactants: Optional[Iterable[RawReactant[UnencodedSignal]]] = None,
    ):
        await super().adapt(neuron, reactants=reactants, raw_reactants=raw_reactants)

        await self._start_recv_loop_if_needed()
