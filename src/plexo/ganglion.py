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
import random
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from functools import reduce
from ipaddress import IPv4Network, IPv6Network
from itertools import islice
from timeit import default_timer as timer
from typing import Union, Type, Callable, Any, ByteString

import capnpy
from plexo.timer import Timer
from pyrsistent import plist, pmap, pdeque, pvector

from plexo.exceptions import SynapseExists, TransmitterNotFound
from plexo.ip_lease import IpLeaseManager
from plexo.transmitter import create_transmitter
from plexo.typing import UnencodedDataType
from plexo.synapse import SynapseZmqEPGM
from plexo.receptor import create_receptor


PlexoApproval = capnpy.load_schema('plexo.schema.plexo_approval').PlexoApproval
PlexoHeartbeat = capnpy.load_schema('plexo.schema.plexo_heartbeat').PlexoHeartbeat
PlexoPreparation = capnpy.load_schema('plexo.schema.plexo_preparation').PlexoPreparation
PlexoPromise = capnpy.load_schema('plexo.schema.plexo_promise').PlexoPromise
PlexoProposal = capnpy.load_schema('plexo.schema.plexo_proposal').PlexoProposal
PlexoRejection = capnpy.load_schema('plexo.schema.plexo_rejection').PlexoRejection


def current_timestamp():
    # returns floating point timestamp in seconds
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()


def current_timestamp_nanoseconds():
    return current_timestamp() * 1e9


def ilen(iterable):
    return reduce(lambda count, element: count + 1, iterable, 0)


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
    async def create_synapse_by_name(self, type_name: str): ...

    @abstractmethod
    async def create_synapse(self, _type: Type): ...

    async def get_synapse(self, _type: Type):
        type_name = _type.__name__
        type_name_bytes = type_name.encode("UTF-8")
        if type_name_bytes not in self._synapses:
            try:
                return await self.create_synapse_by_name(type_name)
            except:
                pass

        return self._synapses[type_name_bytes]

    async def update_transmitter(self, _type: Type,
                                 encoder: Callable[[UnencodedDataType], ByteString]):
        synapse = await self.get_synapse(_type)

        transmitter = create_transmitter((synapse,), encoder, loop=self._loop)

        async with self._transmitters_lock:
            self._transmitters = self._transmitters.set(_type, transmitter)

        return transmitter

    def get_transmitter(self, data: UnencodedDataType):
        _type = type(data)
        try:
            return self._transmitters[_type]
        except KeyError:
            raise TransmitterNotFound("Transmitter for {} does not exist.".format(_type))

    async def react(self, data: UnencodedDataType,
                    reactant: Callable[[UnencodedDataType], Any],
                    decoder: Callable[[ByteString], UnencodedDataType]):
        synapse = await self.get_synapse(data)
        await synapse.update_receptors((create_receptor(reactants=(reactant,), decoder=decoder, loop=self._loop),))

    async def transmit(self, data: UnencodedDataType):
        transmitter = self.get_transmitter(data)

        return await transmitter(data)


class ReservedMulticastAddress(Enum):
    Heartbeat = 0
    Preparation = 1
    Promise = 2
    Rejection = 3
    Proposal = 4
    Approval = 5


def proposal_is_newer(old_proposal, new_proposal):
    return old_proposal.proposal_id < new_proposal.proposal_id and old_proposal.instance_id < new_proposal.instance_id


def newest_accepted_proposal(p1, p2):
    if p1.accepted_proposal_id > p2.accepted_proposal_id and p1.accepted_instance_id > p2.accepted_instance_id:
        return p1
    else:
        return p2


class GanglionMulticast(GanglionBase):
    def __init__(self, bind_interface: str = None,
                 multicast_cidr: Union[IPv4Network, IPv6Network] = ipaddress.ip_network('239.0.0.0/16'),
                 port: int = 5560,
                 heartbeat_interval_seconds: int = 30,
                 proposal_timeout_seconds: int = 5,
                 loop=None) -> None:
        super(GanglionMulticast, self).__init__(loop=loop)
        self.bind_interface = bind_interface
        self.multicast_cidr = multicast_cidr
        self.port = port
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.proposal_timeout_seconds = proposal_timeout_seconds

        self._ip_lease_manager = IpLeaseManager(multicast_cidr)
        # First 32 addresses are reserved for the ganglion
        self._reserved_addresses = plist(islice((i for i in multicast_cidr), 0, 32))
        for address in self._reserved_addresses:
            self._ip_lease_manager.lease_address(address)

        # Unique id for the current instance, first 64 bits of uuid1
        # Not random but should include the current time and be unique enough
        self.instance_id = uuid.uuid1().int >> 64

        self._heartbeats = pmap()
        self._heartbeats_lock = asyncio.Lock()
        self._num_peers = 0

        self._proposals = pmap()
        self._proposals_lock = asyncio.Lock()

        self._preparation_timers = pmap()
        self._preparation_timers_lock = asyncio.Lock()

        self._preparation_promises = pmap()
        self._preparation_promises_lock = asyncio.Lock()
        self._preparation_rejections = pmap()
        self._preparation_rejections_lock = asyncio.Lock()

        self._proposal_timers = pmap()
        self._proposal_timers_lock = asyncio.Lock()

        self._proposal_approvals = pmap()
        self._proposal_approvals_lock = asyncio.Lock()

        self._startup_done = False
        asyncio.ensure_future(self._startup(), loop=loop)

    async def _heartbeat_loop(self):
        instance_id = self.instance_id
        try:
            half_interval = self.heartbeat_interval_seconds/2
            random_sleep_time = random.random() * half_interval + half_interval
        except Exception as e:
            logging.error(e)
            random_sleep_time = self.heartbeat_interval_seconds

        logging.debug("GanglionMulticast:{}:random_sleep_time - {}".format(instance_id, random_sleep_time))

        while True:
            try:
                logging.debug("GanglionMulticast:{}:Sending heartbeat".format(instance_id))
                heartbeat = PlexoHeartbeat(instance_id=instance_id)
                await self.transmit(heartbeat)
            except Exception as e:
                logging.error(e)
            finally:
                await asyncio.sleep(random_sleep_time)

    async def _num_peers_loop(self):
        heartbeat_interval_seconds = self.heartbeat_interval_seconds
        check_seconds = heartbeat_interval_seconds / 2

        while True:
            try:
                current_time = timer()
                self._num_peers = ilen(filter(
                    lambda heartbeat_time: current_time - heartbeat_time <= heartbeat_interval_seconds,
                    self._heartbeats.values()
                ))
                logging.debug("GanglionMulticast:{}:num_peers - {}".format(self.instance_id, self._num_peers))
            except Exception as e:
                logging.error(e)
            finally:
                await asyncio.sleep(check_seconds)

    async def _heartbeat_reaction(self, heartbeat: PlexoHeartbeat):
        logging.debug(
            "GanglionMulticast:{}:Received heartbeat from instance: {}".format(self.instance_id, heartbeat.instance_id)
        )
        async with self._heartbeats_lock:
            self._heartbeats = self._heartbeats.set(heartbeat.instance_id, timer())

    async def _preparation_reaction(self, preparation: PlexoPreparation):
        logging.debug("GanglionMulticast:{}:Received preparation: {}".format(self.instance_id, preparation))
        if preparation.instance_id == self.instance_id:
            logging.debug("GanglionMulticast:{}:"
                          "Preparation instance_id is from current instance. Ignoring.".format(self.instance_id))
            return

        async with self._proposals_lock:
            try:
                current_proposal = self._proposals[preparation.type_name]
            except KeyError:
                current_proposal = None

            if not current_proposal or proposal_is_newer(current_proposal, preparation):
                # instance will make newer proposal
                # promise not to accept any older proposals, sending current known value if possible
                current_multicast_ip = current_proposal.multicast_ip if current_proposal else None
                current_instance_id = current_proposal.instance_id if current_proposal else None
                current_proposal_id = current_proposal.proposal_id if current_proposal else None
                promise = PlexoPromise(multicast_ip=current_multicast_ip, accepted_instance_id=current_instance_id,
                                       accepted_proposal_id=current_proposal_id, instance_id=preparation.instance_id,
                                       proposal_id=preparation.proposal_id, type_name=preparation.type_name)
                proposal = PlexoProposal(instance_id=preparation.instance_id, proposal_id=preparation.proposal_id,
                                         type_name=preparation.type_name, multicast_ip=current_multicast_ip)
                self._proposals = self._proposals.set(proposal.type_name, proposal)
                logging.debug("GanglionMulticast:{}:Sending promise: ".format(promise))
                await self.transmit(promise)
            else:
                # send a rejection
                rejection = PlexoRejection(instance_id=preparation.instance_id, proposal_id=preparation.proposal_id,
                                           type_name=preparation.type_name)
                logging.debug("GanglionMulticast:{}:Sending rejection: ".format(rejection))
                await self.transmit(rejection)

    async def _promise_reaction(self, promise: PlexoPromise):
        logging.debug("GanglionMulticast:{}:Received promise: {}".format(self.instance_id, promise))

        if promise.instance_id != self.instance_id:
            logging.debug("GanglionMulticast:{}:"
                          "Promise instance_id is not from current instance. Ignoring.".format(self.instance_id))
            return

        type_name_bytes = promise.type_name
        async with self._preparation_promises_lock:
            try:
                current_promises = self._preparation_promises[type_name_bytes]
            except KeyError:
                current_promises = pvector()

            new_promises = current_promises.append(promise)
            new_promises_num = len(new_promises)
            self._preparation_promises = self._preparation_promises.set(type_name_bytes, new_promises)

        logging.debug("GanglionMulticast:{}:_promise_reaction:{}:"
                      "num_promises {}, num_peers {}".format(self.instance_id, promise, new_promises_num,
                                                             self._num_peers))
        if new_promises_num >= self._num_peers:
            # All of promises received, no reason to wait any longer
            logging.debug("GanglionMulticast:{}:_promise_reaction:{}:"
                          "All of promises received, cancelling timer".format(self.instance_id, promise))
            async with self._preparation_timers_lock:
                try:
                    self._preparation_timers[type_name_bytes].cancel()
                except KeyError:
                    pass

    async def _rejection_reaction(self, rejection: PlexoRejection):
        logging.debug("GanglionMulticast:{}:Received rejection: {}".format(self.instance_id, rejection))

        if rejection.instance_id != self.instance_id:
            logging.debug("GanglionMulticast:{}:"
                          "Rejection instance_id is not from current instance. Ignoring.".format(self.instance_id))
            return

        type_name_bytes = rejection.type_name
        async with self._preparation_rejections_lock:
            try:
                current_rejections_num = self._preparation_rejections[type_name_bytes]
            except KeyError:
                current_rejections_num = 0

            new_rejections_num = current_rejections_num + 1
            self._preparation_rejections = self._preparation_rejections.set(type_name_bytes, new_rejections_num)

        logging.debug("GanglionMulticast:{}:_rejection_reaction:{}:"
                      "num_rejections {}, num_peers {}".format(self.instance_id, rejection, new_rejections_num,
                                                               self._num_peers))
        if new_rejections_num > self._num_peers / 2:
            # Majority of rejections received, no reason to wait any longer
            logging.debug("GanglionMulticast:{}:_rejection_reaction:{}:"
                          "Majority of rejections received, cancelling timer".format(self.instance_id, rejection))
            async with self._preparation_timers_lock:
                try:
                    self._preparation_timers[type_name_bytes].cancel()
                except KeyError:
                    pass

    async def _proposal_reaction(self, proposal: PlexoProposal):
        logging.debug("GanglionMulticast:{}:Received proposal: {}".format(self.instance_id, proposal))

        async with self._proposals_lock:
            try:
                current_proposal = self._proposals[proposal.type_name]
            except KeyError:
                current_proposal = None

            if not current_proposal:
                raise Exception("No promise was made for proposal {}".format(proposal))

            if proposal_is_newer(proposal, current_proposal):
                raise Exception("A newer proposal was promised {}".format(current_proposal))

            self._proposals = self._proposals.set(proposal.type_name, proposal)

        approval = PlexoApproval(instance_id=proposal.instance_id, proposal_id=proposal.proposal_id,
                                 type_name=proposal.type_name, multicast_ip=proposal.multicast_ip)
        logging.debug("GanglionMulticast:{}:Sending approval: ".format(approval))
        await self.transmit(approval)
        await self._approval_reaction(approval)

    async def _approval_reaction(self, approval: PlexoApproval):
        logging.debug("GanglionMulticast:{}:Received approval: {}".format(self.instance_id, approval))

        type_name_bytes = approval.type_name
        type_proposal_key = (type_name_bytes, approval.proposal_id, approval.instance_id)
        async with self._proposal_approvals_lock:
            try:
                current_approvals_num = self._proposal_approvals[type_proposal_key]
            except KeyError:
                current_approvals_num = 0

            new_approvals_num = current_approvals_num + 1
            self._proposal_approvals = self._proposal_approvals.set(type_proposal_key, new_approvals_num)

        logging.debug("GanglionMulticast:{}:_approval_reaction:{}:"
                      "num_approvals {}".format(self.instance_id, approval, new_approvals_num))
        if new_approvals_num >= self._num_peers / 2:
            if approval.instance_id == self.instance_id:
                logging.debug("GanglionMulticast:{}:"
                              "Approval instance_id is from current instance. Canceling timer".format(self.instance_id))

                async with self._proposal_timers_lock:
                    try:
                        self._proposal_timers[type_name_bytes].cancel()
                    except KeyError:
                        pass
            else:
                # commit new value
                await self.create_or_update_synapse_by_name(type_name_bytes.decode("UTF-8"))

    async def _startup(self):
        await self.create_synapse(PlexoHeartbeat, ReservedMulticastAddress.Heartbeat)
        await self.react(PlexoHeartbeat, self._heartbeat_reaction, PlexoHeartbeat.loads, ignore_startup=True)
        await self.update_transmitter(PlexoHeartbeat, PlexoHeartbeat.dumps)
        self._add_task(self._loop.create_task(self._heartbeat_loop()))
        self._add_task(self._loop.create_task(self._num_peers_loop()))

        await self.create_synapse(PlexoPreparation, ReservedMulticastAddress.Preparation)
        await self.react(PlexoPreparation, self._preparation_reaction, PlexoPreparation.loads, ignore_startup=True)
        await self.update_transmitter(PlexoPreparation, PlexoPreparation.dumps)

        await self.create_synapse(PlexoPromise, ReservedMulticastAddress.Promise)
        await self.react(PlexoPromise, self._promise_reaction, PlexoPromise.loads, ignore_startup=True)
        await self.update_transmitter(PlexoPromise, PlexoPromise.dumps)

        await self.create_synapse(PlexoRejection, ReservedMulticastAddress.Rejection)
        await self.react(PlexoRejection, self._rejection_reaction, PlexoRejection.loads, ignore_startup=True)
        await self.update_transmitter(PlexoRejection, PlexoRejection.dumps)

        await self.create_synapse(PlexoProposal, ReservedMulticastAddress.Proposal)
        await self.react(PlexoProposal, self._proposal_reaction, PlexoProposal.loads, ignore_startup=True)
        await self.update_transmitter(PlexoProposal, PlexoProposal.dumps)

        await self.create_synapse(PlexoApproval, ReservedMulticastAddress.Approval)
        await self.react(PlexoApproval, self._approval_reaction, PlexoApproval.loads, ignore_startup=True)
        await self.update_transmitter(PlexoApproval, PlexoApproval.dumps)

        await asyncio.sleep(self.heartbeat_interval_seconds * 1.5)
        self._startup_done = True

    async def _send_preparation(self, type_name: str):
        instance_id = self.instance_id
        type_name_bytes = type_name.encode("UTF-8")

        async with self._proposals_lock:
            new_proposal_id = current_timestamp_nanoseconds()
            try:
                proposal = self._proposals[type_name_bytes]
                new_proposal = PlexoProposal.loads(proposal.dumps())
                new_proposal.proposal_id = new_proposal_id
                new_proposal.instance_id = instance_id
                if not proposal_is_newer(proposal, new_proposal):
                    raise Exception("Newer proposal for {} already exists".format(type_name))
            except KeyError:
                new_proposal = PlexoProposal(instance_id=instance_id, proposal_id=new_proposal_id,
                                             type_name=type_name_bytes, multicast_ip=None)
            self._proposals = self._proposals.set(type_name_bytes, new_proposal)

        preparation = PlexoPreparation(instance_id=instance_id, proposal_id=new_proposal_id, type_name=type_name_bytes)
        logging.debug("GanglionMulticast:{}:Sending preparation: {}".format(instance_id, preparation))
        await self.transmit(preparation)

        return preparation

    async def _send_proposal(self, preparation: PlexoPreparation,
                             multicast_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]):
        instance_id = preparation.instance_id
        proposal_id = preparation.proposal_id

        proposal = PlexoProposal(instance_id=instance_id, proposal_id=proposal_id, type_name=preparation.type_name,
                                 multicast_ip=multicast_address.packed)
        async with self._proposals_lock:
            self._proposals = self._proposals.set(preparation.type_name, proposal)

        logging.debug("GanglionMulticast:{}:Sending proposal: {}".format(instance_id, proposal))
        await self.transmit(proposal)

        return proposal

    async def _get_address_from_consensus(self, type_name: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
        # 2) If received quorum of rejections, do nothing (there is a higher number proposal in progress)
        # 3) Pending quorum of promises, send proposal
        #   a) if any promise had a value, use value from the highest returned proposal id
        #   b) if all promises had null values, choose a new value
        # 4) Pending quorum of approvals, commit value
        heartbeat_interval_seconds = self.heartbeat_interval_seconds
        type_name_bytes = type_name.encode("UTF-8")

        preparation_timer = Timer(heartbeat_interval_seconds)
        preparation_timer.start()
        async with self._preparation_timers_lock:
            self._preparation_timers = self._preparation_timers.set(type_name_bytes, preparation_timer)

        preparation = await self._send_preparation(type_name)

        try:
            await preparation_timer.wait()
        except asyncio.CancelledError:
            pass
        finally:
            async with self._preparation_timers_lock:
                self._preparation_timers = self._preparation_timers.discard(type_name_bytes)

        async with self._preparation_promises_lock:
            try:
                promises = self._preparation_promises[type_name_bytes]
            except KeyError:
                promises = []
                self._preparation_promises = self._preparation_promises.discard(type_name_bytes)

        async with self._preparation_rejections_lock:
            try:
                rejections_num = self._preparation_rejections[type_name_bytes]
            except KeyError:
                rejections_num = 0
                self._preparation_rejections = self._preparation_rejections.discard(type_name_bytes)

        half_num_peers = self._num_peers / 2
        logging.debug("GanglionMulticast:{}:_get_address_from_consensus:{}:"
                      "num_peers: {}, half_num_peers: {}, num_promises: {}, num_rejections: {}".format(
                          self.instance_id, preparation, self._num_peers, half_num_peers, len(promises), rejections_num)
                      )
        if len(promises) < half_num_peers or rejections_num > half_num_peers:
            raise Exception("Preparation for type {} rejected".format(type_name))

        promises_with_data = pvector(promise for promise in promises if promise.multicast_ip is not None)
        if len(promises_with_data):
            promise_with_highest_proposal_id = reduce(newest_accepted_proposal, promises_with_data)
            multicast_address = ipaddress.ip_address(promise_with_highest_proposal_id.multicast_ip)
        else:
            multicast_address = self._ip_lease_manager.get_address()

        proposal_timer = Timer(heartbeat_interval_seconds)
        proposal_timer.start()
        async with self._proposal_timers_lock:
            self._proposal_timers = self._proposal_timers.set(type_name_bytes, proposal_timer)

        proposal = await self._send_proposal(preparation, multicast_address)

        try:
            await proposal_timer.wait()
        except asyncio.CancelledError:
            pass
        finally:
            async with self._proposal_timers_lock:
                self._proposal_timers = self._proposal_timers.discard(type_name_bytes)

        type_proposal_key = (type_name_bytes, proposal.proposal_id, proposal.instance_id)
        async with self._proposal_approvals_lock:
            try:
                approvals_num = self._proposal_approvals[type_proposal_key]
            except KeyError:
                approvals_num = 0
                self._proposal_approvals = self._proposal_approvals.discard(type_proposal_key)

        half_num_peers = self._num_peers / 2
        if approvals_num >= half_num_peers:
            return multicast_address
        else:
            raise Exception("Consensus could not be agreed upon for the proposal.")

    async def acquire_address_for_type(self, type_name: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
        address = None

        type_name_bytes = type_name.encode("UTF-8")
        while address is None:
            if type_name_bytes in self._synapses:
                raise ValueError("Type {} already has an address".format(type_name))

            try:
                address = await self._get_address_from_consensus(type_name)
            except:
                pass

        return address

    async def create_synapse_by_name(self, type_name: str,
                                     reserved_address: ReservedMulticastAddress = None,
                                     multicast_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address] = None):
        type_name_bytes = type_name.encode("UTF-8")
        if type_name_bytes in self._synapses:
            raise SynapseExists("Synapse for {} already exists.".format(type_name))
        
        # TODO: Add check for existing multicast address in use
        
        multicast_address = self._reserved_addresses[reserved_address.value] if reserved_address \
            else multicast_address if multicast_address \
            else (await self.acquire_address_for_type(type_name))
        logging.debug("GanglionMulticast:{}:Creating synapse for type {} with multicast_address {}".format(
            self.instance_id, type_name, multicast_address
        ))
        synapse = SynapseZmqEPGM(topic=type_name,
                                 multicast_address=multicast_address,
                                 bind_interface=self.bind_interface,
                                 port=self.port,
                                 loop=self._loop
                                 )
        async with self._synapses_lock:
            self._synapses = self._synapses.set(type_name_bytes, synapse)

        return synapse

    async def create_synapse(self, _type: Type,
                             reserved_address: ReservedMulticastAddress = None,
                             multicast_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address] = None):
        return await self.create_synapse_by_name(_type.__name__, reserved_address, multicast_address)

    async def create_or_update_synapse_by_name(self, type_name: str,
                                               reserved_address: ReservedMulticastAddress = None,
                                               multicast_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address] = None):
        type_name_bytes = type_name.encode("UTF-8")
        if type_name_bytes in self._synapses:
            # TODO: Update existing synapse
            raise NotImplementedError("Updating an existing synapse is currently not supported: {}".format(type_name))
        else:
            return await self.create_synapse_by_name(type_name, reserved_address, multicast_address)

    async def react(self, data: UnencodedDataType,
                    reactant: Callable[[UnencodedDataType], Any],
                    decoder: Callable[[ByteString], UnencodedDataType],
                    ignore_startup=False):
        await self.wait_startup(ignore_startup)

        return await super(GanglionMulticast, self).react(data=data, reactant=reactant, decoder=decoder)

    async def transmit(self, data: UnencodedDataType, ignore_startup=False):
        await self.wait_startup(ignore_startup)

        return await super(GanglionMulticast, self).transmit(data=data)

    async def wait_startup(self, ignore_startup=False):
        if not ignore_startup:
            heartbeat_interval_seconds = self.heartbeat_interval_seconds
            while not self._startup_done:
                await asyncio.sleep(heartbeat_interval_seconds)

