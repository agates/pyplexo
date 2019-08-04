# -*- coding: utf-8 -*-

#    domaintypesystem
#    Copyright (C) 2018  Alecks Gates
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
from collections import deque
from datetime import datetime, timezone
import functools
import hashlib
import logging
import signal
import socket
import struct
from timeit import default_timer as timer
import uuid

import blosc
import capnpy

import domaintypesystem.multicastgroups as multicastgroups

DomainTypeGroupMembership = capnpy.load_schema(
    'domaintypesystem.schema.domain_type_group_membership', pyx=False).DomainTypeGroupMembership
DomainTypeGroupMessage = capnpy.load_schema(
    'domaintypesystem.schema.domain_type_group_message', pyx=False).DomainTypeGroupMessage

# Store the hashed machine id as bytes
with open("/var/lib/dbus/machine-id", "rb") as machine_id_file:
    machine_id_hex = machine_id_file.read()
machine_id = hashlib.sha1(machine_id_hex.rstrip()).digest()


def current_timestamp():
    # returns floating point timestamp in seconds
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()


def current_timestamp_nanoseconds():
    return current_timestamp() * 1e9


class MulticastServerProtocol:
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.ensure_future(self.queue.put((data, addr, int(current_timestamp_nanoseconds()))))


class DomainTypeGroupPathway:
    def __init__(self, capnproto_struct=None, struct_name=None,
                 multicast_group=socket.inet_aton('239.255.0.1'),
                 port=5555,
                 loop=None):
        self.capnproto_struct = capnproto_struct
        self.struct_name = None
        self.multicast_group = socket.inet_ntoa(multicast_group)
        self.port = port
        self.send_addr = (self.multicast_group, self.port)
        self.transport = None
        self._raw_handlers = deque()
        self._data_handlers = deque()
        self._query_handlers = deque()
        self._handlers_lock = asyncio.Lock()

        self.tasks = []

        # Unique id for the current DTS instance
        self.instance_id = uuid.uuid1().int >> 64

        if struct_name:
            self.struct_name = bytes(struct_name, "UTF-8")
        else:
            self.struct_name = bytes(self.capnproto_struct.__name__, "UTF-8")

        addrinfo = socket.getaddrinfo(self.multicast_group, None)[0]
        sock = socket.socket(addrinfo[0], socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])

        if addrinfo[0] == socket.AF_INET:  # IPv4
            sock.bind((self.multicast_group, port))
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, mreq)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        else:
            sock.bind((self.multicast_group, port))
            mreq = group_bin + struct.pack('@I', 0)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, mreq)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        self.queue = asyncio.Queue()

        if not loop:
            loop = asyncio.get_event_loop()

        endpoint_task = loop.create_task(loop.create_datagram_endpoint(
            functools.partial(MulticastServerProtocol, self.queue),
            sock=sock
        ))

        self.tasks.append(endpoint_task)

        async def endpoint_done():
            self.transport, self.protocol = await endpoint_task

        self.tasks.append(loop.create_task(endpoint_done()))
        self.tasks.append(loop.create_task(self.handle_queue()))

        self.loop = loop

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self.tasks:
                task.cancel()
        except RuntimeError:
            pass

    async def send(self, message):
        self.transport.sendto(blosc.compress(message), self.send_addr)
        logging.debug("Message sent: {}".format(message))

    async def send_struct(self, capnproto_object):
        message = DomainTypeGroupMessage(struct_name=self.struct_name,
                                         host_id=machine_id,
                                         instance_id=self.instance_id,
                                         timestamp=int(current_timestamp_nanoseconds()),
                                         struct=capnproto_object.dumps())
        await self.send(message.dumps())

    async def query(self, query=None):
        if query:
            query = bytes(query, 'UTF-8')
        message = DomainTypeGroupMessage(struct_name=self.struct_name,
                                         host_id=machine_id,
                                         instance_id=self.instance_id,
                                         timestamp=int(current_timestamp_nanoseconds()),
                                         query=query)
        await self.send(message.dumps())

    async def handle_queue(self):
        loop = self.loop
        queue = self.queue
        handlers_lock = self._handlers_lock
        capnproto_struct = self.capnproto_struct
        struct_name = self.struct_name
        instance_id = self.instance_id
        raw_handlers = self._raw_handlers
        data_handlers = self._data_handlers
        query_handlers = self._query_handlers
        handlers = deque()

        while True:
            data, addr, received_timestamp_nanoseconds = await queue.get()

            try:
                message = DomainTypeGroupMessage.loads(blosc.decompress(data))
            except Exception as e:
                logging.debug("{}:handle_queue: {}".format(struct_name, e))
                queue.task_done()
                continue

            if message.host_id == machine_id and message.instance_id == instance_id:
                # Ignore messages from current instance
                queue.task_done()
                continue
            logging.debug("Handling message from host: {}".format(
                addr,
            ))

            async with handlers_lock:
                if raw_handlers:
                    logging.debug("Have {} raw_handlers".format(len(raw_handlers)))
                    handlers.extend(handler(message, addr, received_timestamp_nanoseconds)
                                    for handler in raw_handlers)
                try:
                    if data_handlers:
                        capnproto_object = capnproto_struct.loads(message.struct)
                        logging.debug("Handling struct data from host: {}, host_id: {}".format(
                            addr,
                            message.host_id
                        ))
                        logging.debug("Have {} data_handlers".format(len(data_handlers)))
                        handlers.extend(handler(capnproto_object, addr, received_timestamp_nanoseconds)
                                        for handler in data_handlers)
                except ValueError:
                    if query_handlers:
                        logging.debug("Handling query from host: {}, host_id: {}".format(
                            addr,
                            message.host_id
                        ))
                        if message.query:
                            query = message.query.decode("UTF-8")
                        else:
                            query = None
                        logging.debug("Have {} query_handlers".format(len(query_handlers)))
                        handlers.extend(handler(query, addr, received_timestamp_nanoseconds)
                                        for handler in query_handlers)
            logging.debug("Awaiting {} handlers: {}".format(len(handlers), handlers))
            await asyncio.wait(handlers, loop=loop)
            logging.debug("Finished awaiting handlers")
            handlers.clear()
            queue.task_done()

    async def handle(self, query_handlers=tuple(), data_handlers=tuple(), raw_handlers=tuple(), capnproto_struct=None):
        if capnproto_struct and not self.capnproto_struct:
            self.capnproto_struct = capnproto_struct
        async with self._handlers_lock:
            self._data_handlers.extend(data_handlers)
            self._query_handlers.extend(query_handlers)
            self._raw_handlers.extend(raw_handlers)


class DomainTypeSystem:

    def __init__(self, loop=None):
        logging.info("machine_id: {0}".format(machine_id))
        # logging.info("instance_id: {0}".format(instance_id))

        self._type_group_pathways = dict()
        self._type_group_pathways_lock = asyncio.Lock()

        self._new_membership_handlers = []
        self._new_membership_handlers_lock = asyncio.Lock()

        self.tasks = []
        self.pathways = []

        async def startup_query():
            logging.debug("Sending startup queries")
            for i in range(3):
                start_time = timer()
                await (await pathway).query()
                await asyncio.sleep(.5 - (timer() - start_time))

        async def periodic_query():
            await asyncio.sleep(10, loop=loop)
            while True:
                start_time = timer()
                logging.debug("Sending periodic query")
                await (await pathway).query()
                await asyncio.sleep(10 - (timer() - start_time))

        async def handle_membership(domain_type_group_membership, address, received_timestamp_nanoseconds):
            await multicastgroups.discard_multicast_group(domain_type_group_membership.multicast_group)
            struct_name = domain_type_group_membership.struct_name.decode("UTF-8")
            new_group = False
            async with self._type_group_pathways_lock:
                if struct_name not in self._type_group_pathways \
                        or self._type_group_pathways[struct_name][0] \
                        != domain_type_group_membership.multicast_group:
                    logging.info("Adding new multicast group: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(domain_type_group_membership.multicast_group)
                    ))
                    self._type_group_pathways[struct_name] = (
                        domain_type_group_membership.multicast_group,
                        None
                    )
                    new_group = True
                else:
                    logging.debug("Multicast already group exists for pathway: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(domain_type_group_membership.multicast_group)
                    ))
            if new_group:
                logging.debug("Sending new multicast group {0}:{1} to new_membership_handlers")
                logging.debug("Acquiring _new_membership_handlers_lock")
                async with self._new_membership_handlers_lock:
                    logging.debug("Acquired _new_membership_handlers_lock")
                    handlers = [handler(struct_name)
                                for handler in self._new_membership_handlers]
                    logging.debug("Awaiting new_membership_handlers: {}".format(handlers))
                    await asyncio.wait(handlers, loop=loop, return_when=asyncio.ALL_COMPLETED)
                    logging.debug("Finished awaiting new_membership_handlers")

        async def handle_query(query, address, received_timestamp_nanoseconds):
            async with self._type_group_pathways_lock:
                pathways = self._type_group_pathways
                for struct_name, value in pathways.items():
                    logging.debug("Responding to DomainTypeGroupMembership query: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(value[0])
                    ))
                    await (await pathway).send_struct(DomainTypeGroupMembership(
                        struct_name=bytes(struct_name, "UTF-8"),
                        multicast_group=value[0]
                    ))

        self.announcement_queue = asyncio.Queue()

        async def announce_new_pathways():
            while True:
                new_pathway_struct, new_pathway_multicast_group = await self.announcement_queue.get()
                await (await pathway).send_struct(DomainTypeGroupMembership(
                    struct_name=bytes(new_pathway_struct, "UTF-8"),
                    multicast_group=new_pathway_multicast_group
                ))
                self.announcement_queue.task_done()

        if not loop:
            loop = asyncio.new_event_loop()

        pathway = loop.create_task(
            self.register_pathway(capnproto_struct=DomainTypeGroupMembership,
                                  multicast_group=socket.inet_aton('239.255.0.1')
                                  )
        )

        self.tasks.append(pathway)

        self.tasks.append(loop.create_task(
            self.handle_type(DomainTypeGroupMembership,
                             query_handlers=(
                                 handle_query,
                             ),
                             data_handlers=(
                                 handle_membership,
                             )
                             )
        ))

        self.tasks.append(loop.create_task(startup_query()))
        self.tasks.append(loop.create_task(periodic_query()))
        self.tasks.append(loop.create_task(announce_new_pathways()))

        logging.debug("DomainTypeSystem initialization complete")

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.__del__)

        self.loop = loop

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self.tasks:
                task.cancel()
            for pathway in (value[1] for value in self._type_group_pathways.values()):
                pathway.close()
        except RuntimeError:
            pass

    async def register_pathway(self, capnproto_struct=None, struct_name=None, multicast_group=None):
        pathway = None
        struct_name = struct_name or capnproto_struct.__name__
        async with self._type_group_pathways_lock:
            if multicast_group is not None:
                if not (await multicastgroups.multicast_group_available(multicast_group)):
                    if struct_name in self._type_group_pathways:
                        if self._type_group_pathways[struct_name][0] != multicast_group:
                            raise ValueError("Given multicast is assigned to another struct")
                        elif self._type_group_pathways[struct_name][1] is not None:
                            logging.warning("Requested pathway already registered: {}:{}".format(
                                struct_name,
                                socket.inet_ntoa(multicast_group)
                            ))
                            return
                await multicastgroups.discard_multicast_group(multicast_group)
                logging.info("Registering pathway to requested multicast group: {}:{}".format(
                    struct_name,
                    socket.inet_ntoa(multicast_group)
                ))
            else:
                if struct_name not in self._type_group_pathways:
                    multicast_group = await multicastgroups.get_multicast_group()
                    logging.info("Registering pathway to new multicast group: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(multicast_group)
                    ))
                elif self._type_group_pathways[struct_name][1] is not None:
                    logging.warning("Requested pathway already registered: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(self._type_group_pathways[struct_name][0])
                    ))
                    return
                else:
                    multicast_group = self._type_group_pathways[struct_name][0]
                    logging.info("Registering pathway to existing multicast group: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(multicast_group)
                    ))

            if capnproto_struct:
                pathway = DomainTypeGroupPathway(capnproto_struct=capnproto_struct, multicast_group=multicast_group,
                                                 loop=self.loop)
            else:
                pathway = DomainTypeGroupPathway(struct_name=struct_name, multicast_group=multicast_group,
                                                 loop=self.loop)

            self._type_group_pathways[struct_name] = (
                multicast_group,
                pathway
            )
            logging.info("Registered pathway: {}:{}".format(
                struct_name, socket.inet_ntoa(multicast_group)
            ))

            while pathway.transport is None:
                await asyncio.sleep(.01, loop=self.loop)
            await self.announcement_queue.put((struct_name, multicast_group))

        return pathway

    async def get_pathway(self, capnproto_struct):
        async with self._type_group_pathways_lock:
            return self._type_group_pathways[capnproto_struct.__name__][1]

    async def handle_type(self, capnproto_struct, query_handlers=tuple(), data_handlers=tuple(), raw_handlers=tuple()):
        pathway = await self.get_pathway(capnproto_struct)
        await pathway.handle(query_handlers=query_handlers, data_handlers=data_handlers, raw_handlers=raw_handlers,
                             capnproto_struct=capnproto_struct)
        logging.info("Registered handlers for {}".format(capnproto_struct.__name__))

    async def handle_any(self, raw_handlers=tuple()):
        async def handle_new_membership(raw_handlers, struct_name):
            new_pathway = await self.register_pathway(struct_name=struct_name)
            await new_pathway.handle(raw_handlers=raw_handlers)
            logging.info("Registered raw handlers for {}".format(struct_name))

        async with self._new_membership_handlers_lock:
            self._new_membership_handlers.append(functools.partial(handle_new_membership, raw_handlers))

        async with self._type_group_pathways_lock:
            type_group_pathways = self._type_group_pathways.items()

        for key, value in type_group_pathways:
            if value[1]:
                await value[1].handle(raw_handlers=raw_handlers)
            else:
                new_pathway = await self.register_pathway(struct_name=key)
                await new_pathway.handle(raw_handlers=raw_handlers)
            logging.info("Registered raw handlers for {}".format(key))

    async def query_type(self, capnproto_struct, query=None):
        pathway = await self.get_pathway(capnproto_struct)
        await pathway.query(query=query)

    async def send_struct(self, capnproto_object):
        pathway = await self.get_pathway(type(capnproto_object))
        await pathway.send_struct(capnproto_object)
