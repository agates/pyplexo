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
import ipaddress
import logging
import random
import uuid
from datetime import datetime, timezone
from enum import Enum
from functools import reduce
from itertools import islice
from timeit import default_timer as timer
from typing import Iterable, Optional, Tuple, cast, Type
from uuid import UUID

from pyrsistent import plist, pmap, pvector
from pyrsistent.typing import PMap
from zmq import ZMQError

from plexo.exceptions import (
    ConsensusNotReached,
    IpLeaseExists,
    PreparationRejection,
    ProposalNotLatest,
    ProposalPromiseNotMade,
    SynapseDoesNotExist,
    SynapseExists,
)
from plexo.ganglion.external import GanglionExternalBase
from plexo.ip_lease import IpLeaseManager
from plexo.neuron.neuron import Neuron
from plexo.neuron.plexo_neuron import (
    approval_neuron,
    heartbeat_neuron,
    preparation_neuron,
    promise_neuron,
    proposal_neuron,
    rejection_neuron,
)
from plexo.schema.plexo_approval import PlexoApproval
from plexo.schema.plexo_heartbeat import PlexoHeartbeat
from plexo.schema.plexo_preparation import PlexoPreparation
from plexo.schema.plexo_promise import PlexoPromise
from plexo.schema.plexo_proposal import PlexoProposal
from plexo.schema.plexo_rejection import PlexoRejection
from plexo.synapse.zeromq_pubsub_epgm import SynapseZmqPubSubEPGM
from plexo.timer import Timer
from plexo.typing import IPAddress, IPNetwork, UnencodedSignal, EncodedSignal
from plexo.typing.reactant import Reactant, RawReactant


def current_timestamp() -> float:
    # returns floating point timestamp in seconds
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()


def current_timestamp_nanoseconds() -> float:
    return current_timestamp() * 1e9


def ilen(iterable):
    return reduce(lambda count, element: count + 1, iterable, 0)


class ReservedMulticastAddress(Enum):
    Heartbeat = 0
    Preparation = 1
    Promise = 2
    Rejection = 3
    Proposal = 4
    Approval = 5


def proposal_is_newer(old_proposal, new_proposal):
    return (old_proposal.proposal_id, old_proposal.instance_id) < (
        new_proposal.proposal_id,
        new_proposal.instance_id,
    )


def proposal_is_equal(old_proposal, new_proposal):
    return (old_proposal.proposal_id, old_proposal.instance_id) == (
        new_proposal.proposal_id,
        new_proposal.instance_id,
    )


def newest_accepted_proposal(p1, p2):
    return (
        p1
        if (p1.accepted_proposal_id, p1.accepted_instance_id)
        > (p2.accepted_proposal_id, p2.accepted_instance_id)
        else p2
    )


class GanglionPlexoMulticast(GanglionExternalBase):
    def __init__(
        self,
        bind_interface: Optional[str] = None,
        multicast_cidr: IPNetwork = ipaddress.ip_network("239.0.0.0/16"),
        port: int = 5560,
        heartbeat_interval_seconds: int = 30,
        proposal_timeout_seconds: int = 5,
        relevant_neurons: Iterable[Neuron] = (),
        ignored_neurons: Iterable[Neuron] = (),
        allowed_codecs: Iterable[Type] = (),
    ) -> None:
        super().__init__(
            relevant_neurons=relevant_neurons,
            ignored_neurons=ignored_neurons,
            allowed_codecs=allowed_codecs,
        )
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

        self._synapses_by_address: PMap = pmap()

        # Unique id for the current instance, first 64 bits of uuid1
        # Not random but should include the current time and be unique enough
        self.instance_id = uuid.uuid1().int >> 64

        self._heartbeats: PMap = pmap()
        self._heartbeats_lock = asyncio.Lock()
        self._num_peers = 0

        self._proposals: PMap = pmap()
        self._proposals_lock = asyncio.Lock()

        self._preparation_timers: PMap = pmap()
        self._preparation_timers_lock = asyncio.Lock()

        self._preparation_promises: PMap = pmap()
        self._preparation_promises_lock = asyncio.Lock()
        self._preparation_rejections: PMap = pmap()
        self._preparation_rejections_lock = asyncio.Lock()

        self._proposal_timers: PMap = pmap()
        self._proposal_timers_lock = asyncio.Lock()

        self._proposal_approvals: PMap = pmap()
        self._proposal_approvals_lock = asyncio.Lock()

        self._startup_done = False
        # asyncio.ensure_future(self._startup())#, loop=loop)

    async def _heartbeat_loop(self):
        instance_id = self.instance_id
        try:
            half_interval = self.heartbeat_interval_seconds / 2
            random_sleep_time = (  # nosec - This is not security related
                random.random() * half_interval + half_interval
            )
        except Exception as e:
            logging.error(e)
            random_sleep_time = self.heartbeat_interval_seconds

        logging.debug(
            "GanglionPlexoMulticast:{}:random_sleep_time - {}".format(
                instance_id, random_sleep_time
            )
        )

        heartbeat = PlexoHeartbeat(instance_id=instance_id)
        while True:
            try:
                logging.debug(f"GanglionPlexoMulticast:{instance_id}:Sending heartbeat")
                await self.transmit_ignore_startup(heartbeat)
            except Exception as e:
                logging.error(e)
            except asyncio.CancelledError:
                raise
            finally:
                await asyncio.sleep(random_sleep_time)

    async def _num_peers_loop(self):
        heartbeat_interval_seconds = self.heartbeat_interval_seconds
        check_seconds = heartbeat_interval_seconds / 2

        while True:
            try:
                current_time = timer()
                self._num_peers = ilen(
                    filter(
                        lambda heartbeat_time: current_time - heartbeat_time
                        <= heartbeat_interval_seconds,
                        self._heartbeats.values(),
                    )
                )
                logging.debug(
                    "GanglionPlexoMulticast:{}:num_peers - {}".format(
                        self.instance_id, self._num_peers
                    )
                )
            except Exception as e:
                logging.error(e)
            except asyncio.CancelledError:
                raise
            finally:
                await asyncio.sleep(check_seconds)

    async def _heartbeat_reaction(
        self,
        heartbeat: PlexoHeartbeat,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        logging.debug(
            "GanglionPlexoMulticast:{}:Received heartbeat from instance: {}".format(
                self.instance_id, heartbeat.instance_id
            )
        )
        async with self._heartbeats_lock:
            self._heartbeats = self._heartbeats.set(heartbeat.instance_id, timer())

    async def _preparation_reaction(
        self,
        preparation: PlexoPreparation,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        logging.debug(
            "GanglionPlexoMulticast:{}:Received preparation: {}".format(
                self.instance_id, preparation
            )
        )
        if preparation.instance_id == self.instance_id:
            logging.debug(
                "GanglionPlexoMulticast:{}:"
                "Preparation instance_id is from current instance. Ignoring.".format(
                    self.instance_id
                )
            )
            return

        async with self._proposals_lock:
            try:
                current_proposal = self._proposals[preparation.type_name]
            except KeyError:
                current_proposal = None

            logging.debug(
                "GanglionPlexoMulticast:{}:_preparation_reaction:{}:"
                "current_proposal {}".format(
                    self.instance_id, preparation, current_proposal
                )
            )
            if not current_proposal or proposal_is_newer(current_proposal, preparation):
                # instance will make newer proposal
                # promise not to accept any older proposals, sending current known value if possible
                current_multicast_ip = (
                    current_proposal.multicast_ip if current_proposal else None
                )
                current_instance_id = (
                    current_proposal.instance_id if current_proposal else 0
                )
                current_proposal_id = (
                    current_proposal.proposal_id if current_proposal else 0
                )
                promise = PlexoPromise(
                    multicast_ip=current_multicast_ip,
                    accepted_instance_id=current_instance_id,
                    accepted_proposal_id=current_proposal_id,
                    instance_id=preparation.instance_id,
                    proposal_id=preparation.proposal_id,
                    type_name=preparation.type_name,
                )
                proposal = PlexoProposal(
                    instance_id=preparation.instance_id,
                    proposal_id=preparation.proposal_id,
                    type_name=preparation.type_name,
                    multicast_ip=current_multicast_ip,
                )
                self._proposals = self._proposals.set(proposal.type_name, proposal)
                logging.debug(
                    "GanglionPlexoMulticast:{}:Sending promise: {}".format(
                        self.instance_id, promise
                    )
                )
                await self.transmit(promise)
            else:
                # send a rejection
                rejection = PlexoRejection(
                    instance_id=preparation.instance_id,
                    proposal_id=preparation.proposal_id,
                    type_name=preparation.type_name,
                )
                logging.debug(
                    "GanglionPlexoMulticast:{}:Sending rejection: {}".format(
                        self.instance_id, rejection
                    )
                )
                await self.transmit(rejection)

    async def _promise_reaction(
        self,
        promise: PlexoPromise,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        logging.debug(
            f"GanglionPlexoMulticast:{self.instance_id}:Received promise: {promise}"
        )

        if promise.instance_id != self.instance_id:
            logging.debug(
                "GanglionPlexoMulticast:{}:"
                "Promise instance_id is not from current instance. Ignoring.".format(
                    self.instance_id
                )
            )
            return

        name_bytes = promise.type_name
        async with self._preparation_promises_lock:
            try:
                current_promises = self._preparation_promises[name_bytes]
            except KeyError:
                current_promises = pvector()

            new_promises = current_promises.append(promise)
            new_promises_num = len(new_promises)
            self._preparation_promises = self._preparation_promises.set(
                name_bytes, new_promises
            )

        logging.debug(
            "GanglionPlexoMulticast:{}:_promise_reaction:{}:"
            "num_promises {}, num_peers {}".format(
                self.instance_id, promise, new_promises_num, self._num_peers
            )
        )
        if new_promises_num >= self._num_peers:
            # All of promises received, no reason to wait any longer
            logging.debug(
                "GanglionPlexoMulticast:{}:_promise_reaction:{}:"
                "All of promises received, cancelling timer".format(
                    self.instance_id, promise
                )
            )
            async with self._preparation_timers_lock:
                try:
                    self._preparation_timers[name_bytes].cancel()
                except KeyError:
                    pass

    async def _rejection_reaction(
        self,
        rejection: PlexoRejection,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        logging.debug(
            f"GanglionPlexoMulticast:{self.instance_id}:Received rejection: {rejection}"
        )

        if rejection.instance_id != self.instance_id:
            logging.debug(
                "GanglionPlexoMulticast:{}:"
                "Rejection instance_id is not from current instance. Ignoring.".format(
                    self.instance_id
                )
            )
            return

        name_bytes = rejection.type_name
        async with self._preparation_rejections_lock:
            try:
                current_rejections_num = self._preparation_rejections[name_bytes]
            except KeyError:
                current_rejections_num = 0

            new_rejections_num = current_rejections_num + 1
            self._preparation_rejections = self._preparation_rejections.set(
                name_bytes, new_rejections_num
            )

        logging.debug(
            "GanglionPlexoMulticast:{}:_rejection_reaction:{}:"
            "num_rejections {}, num_peers {}".format(
                self.instance_id, rejection, new_rejections_num, self._num_peers
            )
        )
        if new_rejections_num > self._num_peers / 2:
            # Majority of rejections received, no reason to wait any longer
            logging.debug(
                "GanglionPlexoMulticast:{}:_rejection_reaction:{}:"
                "Majority of rejections received, cancelling timer".format(
                    self.instance_id, rejection
                )
            )
            async with self._preparation_timers_lock:
                try:
                    self._preparation_timers[name_bytes].cancel()
                except KeyError:
                    pass

    async def _proposal_reaction(
        self,
        proposal: PlexoProposal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        logging.debug(
            f"GanglionPlexoMulticast:{self.instance_id}:Received proposal: {proposal}"
        )

        async with self._proposals_lock:
            try:
                current_proposal = self._proposals[proposal.type_name]
            except KeyError:
                current_proposal = None

            if not current_proposal:
                raise ProposalPromiseNotMade(
                    f"No promise was made for proposal {proposal}"
                )

            if not proposal_is_equal(current_proposal, proposal):
                raise ProposalNotLatest(
                    f"A newer proposal was promised {current_proposal}"
                )

            self._proposals = self._proposals.set(proposal.type_name, proposal)

        approval = PlexoApproval(
            instance_id=proposal.instance_id,
            proposal_id=proposal.proposal_id,
            type_name=proposal.type_name,
            multicast_ip=proposal.multicast_ip,
        )
        logging.debug(
            f"GanglionPlexoMulticast:{self.instance_id}:Sending approval: {approval}"
        )
        await self.transmit(approval)
        await self._approval_reaction(approval)

    async def _approval_reaction(
        self,
        approval: PlexoApproval,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        logging.debug(
            f"GanglionPlexoMulticast:{self.instance_id}:Received approval: {approval}"
        )

        name_bytes = approval.type_name
        type_proposal_key = (name_bytes, approval.proposal_id, approval.instance_id)
        async with self._proposal_approvals_lock:
            try:
                current_approvals_num = self._proposal_approvals[type_proposal_key]
            except KeyError:
                current_approvals_num = 0

            new_approvals_num = current_approvals_num + 1
            self._proposal_approvals = self._proposal_approvals.set(
                type_proposal_key, new_approvals_num
            )

        half_num_peers = self._num_peers / 2
        logging.debug(
            "GanglionPlexoMulticast:{}:_approval_reaction:{}:"
            "num_approvals {}, half_num_peers {}".format(
                self.instance_id, approval, new_approvals_num, half_num_peers
            )
        )
        if new_approvals_num > half_num_peers:
            if approval.instance_id == self.instance_id:
                logging.debug(
                    "GanglionPlexoMulticast:{}:"
                    "Approval instance_id is from current instance. Canceling timer".format(
                        self.instance_id
                    )
                )

                async with self._proposal_timers_lock:
                    try:
                        self._proposal_timers[name_bytes].cancel()
                    except KeyError:
                        pass
            else:
                logging.debug(
                    "GanglionPlexoMulticast:{}:"
                    "Approval instance_id is not from current instance. "
                    "Creating/updating synapse from approval {}".format(
                        self.instance_id, approval
                    )
                )
                # commit new value
                await self.create_or_update_synapse_with_address(
                    await self._get_neuron_by_name(name_bytes.decode("UTF-8")),
                    name_bytes.decode("UTF-8"),
                    multicast_address=ipaddress.ip_address(approval.multicast_ip),
                )
                async with self._proposal_approvals_lock:
                    self._proposal_approvals = self._proposal_approvals.discard(
                        type_proposal_key
                    )

    async def startup(self):
        try:
            await self.create_synapse_with_reserved_address(
                heartbeat_neuron, ReservedMulticastAddress.Heartbeat
            )
            await self.adapt_ignore_startup(
                heartbeat_neuron, reactants=(self._heartbeat_reaction,)
            )
            self._add_task(asyncio.create_task(self._heartbeat_loop()))
            self._add_task(asyncio.create_task(self._num_peers_loop()))

            neuron_reserved_addresses: Iterable[
                Tuple[Neuron, ReservedMulticastAddress]
            ] = (
                (preparation_neuron, ReservedMulticastAddress.Preparation),
                (promise_neuron, ReservedMulticastAddress.Promise),
                (rejection_neuron, ReservedMulticastAddress.Rejection),
                (proposal_neuron, ReservedMulticastAddress.Proposal),
                (approval_neuron, ReservedMulticastAddress.Approval),
            )

            neuron_reactions = (
                (preparation_neuron, self._preparation_reaction),
                (promise_neuron, self._promise_reaction),
                (rejection_neuron, self._rejection_reaction),
                (proposal_neuron, self._proposal_reaction),
                (approval_neuron, self._approval_reaction),
            )

            await asyncio.gather(
                *(
                    self.create_synapse_with_reserved_address(neuron, reserved_address)
                    for neuron, reserved_address in neuron_reserved_addresses
                )
            )

            await asyncio.gather(
                *(
                    self.adapt_ignore_startup(
                        cast(Neuron, neuron), reactants=(cast(Reactant, reactant),)
                    )
                    for neuron, reactant in neuron_reactions
                )
            )

            await asyncio.sleep(self.heartbeat_interval_seconds)
            self._startup_done = True
        except ZMQError as e:
            logging.error(
                f"GanglionPlexoMulticast:startup: epgm not supported on this system: {e}",
                stack_info=True,
            )

    async def wait_startup(self):
        heartbeat_interval_seconds = self.heartbeat_interval_seconds
        while not self._startup_done:
            await asyncio.sleep(heartbeat_interval_seconds)

    async def _send_preparation(self, name: str):
        instance_id = self.instance_id
        name_bytes = name.encode("UTF-8")

        new_proposal_id = int(current_timestamp_nanoseconds())

        preparation = PlexoPreparation(
            instance_id=instance_id, proposal_id=new_proposal_id, type_name=name_bytes
        )
        logging.debug(
            f"GanglionPlexoMulticast:{instance_id}:Sending preparation: {preparation}"
        )
        await self.transmit(preparation)

        return preparation

    async def _send_proposal(
        self, preparation: PlexoPreparation, multicast_address: IPAddress
    ):
        instance_id = preparation.instance_id
        proposal_id = preparation.proposal_id

        proposal = PlexoProposal(
            instance_id=instance_id,
            proposal_id=proposal_id,
            type_name=preparation.type_name,
            multicast_ip=multicast_address.packed,
        )
        async with self._proposals_lock:
            self._proposals = self._proposals.set(preparation.type_name, proposal)

        logging.debug(
            f"GanglionPlexoMulticast:{instance_id}:Sending proposal: {proposal}"
        )
        await self.transmit(proposal)

        return proposal

    async def _get_address_from_consensus(self, name: str) -> IPAddress:
        # 1) Send preparation with new proposal number
        # 2) If received quorum of rejections, do nothing (there is a higher number proposal in progress)
        # 3) Pending quorum of promises, send proposal
        #   a) if any promise had a value, use value from the highest returned proposal id
        #   b) if all promises had null values, choose a new value
        # 4) Pending quorum of approvals, commit value
        proposal_timeout_seconds = self.proposal_timeout_seconds
        name_bytes = name.encode("UTF-8")

        preparation = await self._send_preparation(name)

        preparation_timer = Timer(proposal_timeout_seconds)
        preparation_timer.start()
        async with self._preparation_timers_lock:
            self._preparation_timers = self._preparation_timers.set(
                name_bytes, preparation_timer
            )

        try:
            await preparation_timer.wait()
        except asyncio.CancelledError:
            pass
        finally:
            async with self._preparation_timers_lock:
                self._preparation_timers = self._preparation_timers.discard(name_bytes)

        async with self._preparation_promises_lock:
            try:
                promises = self._preparation_promises[name_bytes]
            except KeyError:
                promises = []
            self._preparation_promises = self._preparation_promises.discard(name_bytes)

        async with self._preparation_rejections_lock:
            try:
                rejections_num = self._preparation_rejections[name_bytes]
            except KeyError:
                rejections_num = 0
            self._preparation_rejections = self._preparation_rejections.discard(
                name_bytes
            )

        half_num_peers = self._num_peers / 2
        logging.debug(
            "GanglionPlexoMulticast:{}:_get_address_from_consensus:{}:"
            "num_peers: {}, half_num_peers: {}, num_promises: {}, num_rejections: {}".format(
                self.instance_id,
                preparation,
                self._num_peers,
                half_num_peers,
                len(promises),
                rejections_num,
            )
        )
        if len(promises) < half_num_peers or rejections_num > half_num_peers:
            raise PreparationRejection(
                f"Preparation for type {name} rejected: {preparation}"
            )

        promises_with_data = pvector(
            promise for promise in promises if promise.multicast_ip is not None
        )
        if len(promises_with_data):
            promise_with_highest_proposal_id = reduce(
                newest_accepted_proposal, promises_with_data
            )
            multicast_address = ipaddress.ip_address(
                promise_with_highest_proposal_id.multicast_ip
            )
        else:
            multicast_address = self._ip_lease_manager.get_address()

        proposal = await self._send_proposal(preparation, multicast_address)

        proposal_timer = Timer(proposal_timeout_seconds)
        proposal_timer.start()
        async with self._proposal_timers_lock:
            self._proposal_timers = self._proposal_timers.set(
                name_bytes, proposal_timer
            )

        try:
            await proposal_timer.wait()
        except asyncio.CancelledError:
            pass
        finally:
            async with self._proposal_timers_lock:
                self._proposal_timers = self._proposal_timers.discard(name_bytes)

        type_proposal_key = (name_bytes, proposal.proposal_id, proposal.instance_id)
        async with self._proposal_approvals_lock:
            try:
                approvals_num = self._proposal_approvals[type_proposal_key]
            except KeyError:
                approvals_num = 0
                self._proposal_approvals = self._proposal_approvals.discard(
                    type_proposal_key
                )

        half_num_peers = self._num_peers / 2
        logging.debug(
            "GanglionPlexoMulticast:{}:_get_address_from_consensus:{}:"
            "num_peers: {}, half_num_peers: {}, num_approval: {}".format(
                self.instance_id,
                proposal,
                self._num_peers,
                half_num_peers,
                approvals_num,
            )
        )
        if approvals_num >= half_num_peers:
            return multicast_address
        else:
            raise ConsensusNotReached(
                "Consensus could not be agreed upon for the proposal."
            )

    async def acquire_address_for_type(self, name: str) -> IPAddress:
        address: Optional[IPAddress] = None

        while address is None:
            if name in self._synapses:
                raise SynapseExists(f"Synapse for {name} already exists.")

            try:
                address = await self._get_address_from_consensus(name)
            except (PreparationRejection, ConsensusNotReached) as e:
                logging.debug(f"Unable to acquire new address for type {name}")
                logging.debug(e, exc_info=True)
            except Exception as e:
                logging.error(f"Unable to acquire new address for type {name}")
                logging.error(e, exc_info=True)
                raise e

        return address

    def try_lease_address(self, multicast_address):
        try:
            # Try to lease the address, it may have been leased before getting this far
            self._ip_lease_manager.lease_address(multicast_address)
        except IpLeaseExists as e:
            # If the address is currently leased, see if it exists in an known synapse
            # If it does, raise the error.  Otherwise, continue
            if multicast_address in self._synapses_by_address:
                raise e

    async def create_synapse_with_address(
        self, neuron: Neuron[UnencodedSignal], name: str, multicast_address: IPAddress
    ):
        if name in self._synapses:
            raise SynapseExists(f"Synapse for {name} already exists.")

        logging.debug(
            "GanglionPlexoMulticast:{}:Creating synapse for type {} with"
            " multicast_address {}".format(self.instance_id, name, multicast_address)
        )

        self.try_lease_address(multicast_address)

        synapse: SynapseZmqPubSubEPGM = SynapseZmqPubSubEPGM(
            neuron=neuron,
            multicast_address=multicast_address,
            bind_interface=self.bind_interface,
            port=self.port,
        )
        async with self._synapses_lock:
            self._synapses = self._synapses.set(name, synapse)
            self._synapses_by_address = self._synapses_by_address.set(
                multicast_address, synapse
            )

        return synapse

    async def update_synapse_with_address(
        self, name: str, multicast_address: IPAddress
    ):
        if name not in self._synapses:
            raise SynapseDoesNotExist(f"Synapse for {name} does not exist.")

        current_synapse = cast(SynapseZmqPubSubEPGM, self._synapses[name])
        current_multicast_address = current_synapse.multicast_address

        if current_multicast_address == multicast_address:
            logging.debug(
                "GanglionPlexoMulticast:{}:update_synapse_with_address:"
                "Synapse for type {} already exists with correct multicast_address {}".format(
                    self.instance_id, name, multicast_address
                )
            )
            return current_synapse
        else:
            logging.debug(
                "GanglionPlexoMulticast:{}:update_synapse_with_address:"
                "Synapse for type {} already exists with current_multicast_address {}, "
                "updating with new multicast_address {}".format(
                    self.instance_id, name, current_multicast_address, multicast_address
                )
            )

        self.try_lease_address(multicast_address)

        current_synapse.update(multicast_address)

        async with self._synapses_lock:
            self._synapses_by_address = self._synapses_by_address.set(
                multicast_address, current_synapse
            )
            self._synapses_by_address = self._synapses_by_address.discard(
                current_multicast_address
            )

        self._ip_lease_manager.release_address(current_multicast_address)

        return current_synapse

    async def create_synapse_with_reserved_address_by_name(
        self,
        neuron: Neuron[UnencodedSignal],
        name: str,
        reserved_address: ReservedMulticastAddress,
    ):
        multicast_address = self._reserved_addresses[reserved_address.value]
        return await self.create_synapse_with_address(neuron, name, multicast_address)

    async def create_synapse_with_reserved_address(
        self, neuron: Neuron, reserved_address: ReservedMulticastAddress
    ):
        return await self.create_synapse_with_reserved_address_by_name(
            neuron, neuron.name, reserved_address
        )

    async def _create_synapse_by_name(self, neuron: Neuron[UnencodedSignal], name: str):
        multicast_address = await self.acquire_address_for_type(name)
        return await self.create_synapse_with_address(neuron, name, multicast_address)

    async def _create_synapse(self, neuron: Neuron):
        return await self._create_synapse_by_name(neuron, neuron.name)

    async def create_or_update_synapse_with_address(
        self, neuron: Neuron[UnencodedSignal], name: str, multicast_address: IPAddress
    ):
        if name in self._synapses:
            return await self.update_synapse_with_address(name, multicast_address)
        else:
            logging.debug(
                "GanglionPlexoMulticast:{}:create_or_update_synapse_by_name:"
                "Synapse for type {} does not exist, creating with multicast_address {}".format(
                    self.instance_id, name, multicast_address
                )
            )
            return await self.create_synapse_with_address(
                neuron, name, multicast_address
            )

    async def react_raw_ignore_startup(
        self,
        neuron: Neuron[UnencodedSignal],
        raw_reactants: Iterable[RawReactant[UnencodedSignal]],
    ):
        return await super().react_raw(neuron, raw_reactants)

    async def react_raw(
        self,
        neuron: Neuron[UnencodedSignal],
        raw_reactants: Iterable[RawReactant[UnencodedSignal]],
    ):
        await self.wait_startup()
        return await super().react_raw(neuron, raw_reactants)

    async def react_ignore_startup(
        self, neuron: Neuron, reactants: Iterable[Reactant[UnencodedSignal]]
    ):
        return await super().react(neuron, reactants)

    async def react(
        self, neuron: Neuron, reactants: Iterable[Reactant[UnencodedSignal]]
    ):
        await self.wait_startup()
        return await super().react(neuron, reactants)

    async def transmit_encoded_ignore_startup(
        self,
        data: EncodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        return await super().transmit_encoded(data, neuron, reaction_id)

    async def transmit_encoded(
        self,
        data: EncodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        await self.wait_startup()
        return await super().transmit_encoded(data, neuron, reaction_id)

    async def transmit_ignore_startup(
        self,
        data: UnencodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        return await super().transmit(data, neuron, reaction_id)

    async def transmit(
        self,
        data: UnencodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ):
        await self.wait_startup()
        return await super().transmit(data, neuron, reaction_id)

    async def adapt_ignore_startup(
        self,
        neuron: Neuron,
        reactants: Optional[Iterable[Reactant]] = None,
        raw_reactants: Optional[Iterable[RawReactant[UnencodedSignal]]] = None,
    ):
        return await super().adapt(neuron, reactants, raw_reactants)

    async def adapt(
        self,
        neuron: Neuron[UnencodedSignal],
        reactants: Optional[Iterable[Reactant]] = None,
        raw_reactants: Optional[Iterable[RawReactant[UnencodedSignal]]] = None,
    ):
        await self.wait_startup()
        return await super().adapt(neuron, reactants, raw_reactants)
