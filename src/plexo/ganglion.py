#  pyplexo
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
import ipaddress
import logging
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from ipaddress import IPv4Network, IPv6Network
from itertools import islice
from random import random
from typing import Union, Type, Callable, Any, ByteString

import capnpy
from pyrsistent import plist, pmap, pdeque

from plexo.exceptions import SynapseExists, TransmitterNotFound
from plexo.host_information import get_hashed_primary_ip
from plexo.transmitter import create_transmitter
from plexo.typing import UnencodedDataType
from plexo.synapse import SynapseZmqEPGM
from plexo.receptor import create_receptor

PlexoHeartbeat = capnpy.load_schema('plexo.schema.plexo_heartbeat').PlexoHeartbeat


class GanglionBase(ABC):
    def __init__(self, loop=None):
        self._tasks = pdeque()

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._synapses = pmap()
        self._synapses_lock = asyncio.Lock()

        self._transmitters = pmap()
        self._transmitters_lock = asyncio.Lock()

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

    @abstractmethod
    async def create_synapse(self, _type: Type): ...

    async def get_synapse(self, _type: Type):
        if _type not in self._synapses:
            return await self.create_synapse(_type)

        return self._synapses[_type]

    async def update_transmitter(self, _type: Type,
                                 encoder: Callable[[UnencodedDataType], ByteString]):
        synapse = await self.get_synapse(_type)

        transmitter = create_transmitter((synapse,), encoder)

        async with self._transmitters_lock:
            self._transmitters = self._transmitters.set(_type, transmitter)

        return transmitter

    def get_transmitter(self, _type: Type):
        try:
            return self._transmitters[_type]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(_type))

    async def react(self, _type: Type,
                    reactant: Callable[[UnencodedDataType], Any],
                    decoder: Callable[[ByteString], UnencodedDataType]):
        synapse = await self.get_synapse(_type)
        await synapse.update_receptors(create_receptor(reactants=(reactant,), decoder=decoder))

    async def transmit(self, data: UnencodedDataType):
        _type = type(data)
        transmitter = self.get_transmitter(_type)

        return await transmitter(data)


class ReservedMulticastAddress(Enum):
    Heartbeat = 0
    Proposal = 1
    Approval = 2


class GanglionMulticast(GanglionBase):
    def __init__(self, bind_interface: str = None,
                 multicast_cidr: Union[IPv4Network, IPv6Network] = ipaddress.ip_network('239.0.0.0/16'),
                 port: int = 5560,
                 heartbeat_interval_seconds: int = 30,
                 loop=None) -> None:
        super(GanglionMulticast, self).__init__(loop=loop)
        self.bind_interface = bind_interface
        self.multicast_cidr = multicast_cidr
        self.port = port
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

        multicast_cidr_generator = (i for i in multicast_cidr)
        # First 10 addresses are reserved for the ganglion
        self._reserved_addresses = plist(islice(multicast_cidr_generator, 0, 10))

        self._usable_addresses = set(multicast_cidr_generator)
        self._usable_addresses_lock = asyncio.Lock()

        self.host_ip = get_hashed_primary_ip()
        # Unique id for the current instance
        self.instance_id = uuid.uuid1().int >> 64

        asyncio.ensure_future(self._startup(), loop=loop)

    async def _heartbeat_loop(self):
        half_interval = self.heartbeat_interval_seconds/2
        random_sleep_time = random.random() * half_interval + half_interval
        host_ip = self.host_ip
        instance_id = self.instance_id

        while True:
            await self.transmit(PlexoHeartbeat(host_ip=host_ip, instance_id=instance_id))
            await asyncio.sleep(random_sleep_time)

    async def _heartbeat_reaction(self, heartbeat):
        logging.info(heartbeat)

    async def _startup(self):
        await self.create_synapse(PlexoHeartbeat, ReservedMulticastAddress.Heartbeat)
        await self.react(PlexoHeartbeat, self._heartbeat_reaction, PlexoHeartbeat.loads)
        await self.update_transmitter(PlexoHeartbeat, PlexoHeartbeat.dumps)
        self._add_task(self._loop.create_task(
            self._heartbeat_loop()
        ))

    async def create_synapse(self, _type: Type,
                             reserved_address: ReservedMulticastAddress = None):
        if _type in self._synapses:
            raise SynapseExists("Synapse for {} already exists.".format(_type))
        topic = _type.__name__
        async with self._usable_addresses_lock:
            multicast_address = self._reserved_addresses[reserved_address.value] if reserved_address \
                else self._usable_addresses.pop()
        synapse = SynapseZmqEPGM(topic=topic,
                                 multicast_address=multicast_address,
                                 bind_interface=self.bind_interface,
                                 port=self.port,
                                 loop=self._loop
                                 )
        async with self._synapses_lock:
            self._synapses = self._synapses.set(_type, synapse)

        return synapse
