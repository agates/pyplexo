import asyncio
import functools
import gzip
import hashlib
import ipaddress
import logging
import socket
import struct

from .schema.domain_type_group_membership import DomainTypeGroupMembership
from .schema.domain_type_group_message import DomainTypeGroupMessage


class MulticastServerProtocol:
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.ensure_future(self.queue.put((data, addr)))


class DomainTypeGroupPathway:
    def __init__(self, capnproto_struct,
                 multicast_group=socket.inet_aton('239.255.0.1'),
                 port=5555):
        self.capnproto_struct = capnproto_struct
        self.multicast_group = socket.inet_ntoa(multicast_group)
        self.port = port
        self.send_addr = (self.multicast_group, self.port)
        self.transport = None

        # Store the hashed machine id as bytes
        with open("/var/lib/dbus/machine-id", "rb") as machine_id_file:
            machine_id_hex = machine_id_file.read()
        self.machine_id = hashlib.sha1(machine_id_hex.rstrip()).digest()

        addrinfo = socket.getaddrinfo(self.multicast_group, None)[0]
        sock = socket.socket(addrinfo[0], socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])

        if addrinfo[0] == socket.AF_INET:  # IPv4
            sock.bind((self.multicast_group, port))
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, mreq)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        else:
            sock.bind((self.multicast_group, port))
            mreq = group_bin + struct.pack('@I', 0)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 0)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, mreq)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        self.queue = asyncio.Queue()

        listen = asyncio.get_event_loop().create_datagram_endpoint(
            functools.partial(MulticastServerProtocol, self.queue),
            sock=sock
        )

        def listen_done(future):
            self.transport, self.protocol = future.result()

        listen_future = asyncio.ensure_future(listen)
        listen_future.add_done_callback(listen_done)

    async def send(self, message):
        self.transport.sendto(gzip.compress(message, compresslevel=4), self.send_addr)
        logging.debug("Message sent: {}".format(message))

    async def send_struct(self, capnproto_object):
        message = DomainTypeGroupMessage(host_id=self.machine_id,
                                         struct=capnproto_object.dumps())
        logging.debug("Sending struct: {}".format(message))
        await self.send(message.dumps())

    async def query(self):
        message = DomainTypeGroupMessage(host_id=self.machine_id,
                                         query=None)
        logging.debug("Sending query: {}".format(message))
        await self.send(message.dumps())

    async def handle_queue(self, query_handlers=tuple(), data_handlers=tuple()):
        while True:
            data, addr = await self.queue.get()
            message = DomainTypeGroupMessage.loads(gzip.decompress(data))
            try:
                capnproto_object = self.capnproto_struct.loads(message.struct)
                logging.debug("Handling struct data from host: {}, host_id: {}".format(
                    addr,
                    message.host_id
                ))
                await asyncio.gather(*[handler(capnproto_object) for handler in data_handlers])
            except ValueError:
                logging.debug("Handling query from host: {}, host_id: {}".format(
                    addr,
                    message.host_id
                ))
                await asyncio.gather(*[handler(None) for handler in query_handlers])
            finally:
                self.queue.task_done()

    async def handle(self, query_handlers=tuple(), data_handlers=tuple()):
        asyncio.ensure_future(self.handle_queue(query_handlers, data_handlers))


class DomainTypeSystem:

    def __init__(self):
        # List of available multicast groups
        self._available_groups = {socket.inet_aton(str(ip_address))
                                  for ip_address in ipaddress.ip_network('239.255.0.0/16').hosts()}
        self._available_groups_lock = asyncio.Lock()
        # Remove the first ip address, 239.255.0.0, since it's unusable
        self._available_groups.discard(socket.inet_aton('239.255.0.0'))

        self._type_group_pathways = dict()
        self._type_group_pathways_lock = asyncio.Lock()

        def handler_startup(future):
            pathway = future.result()

            def startup_query(_):
                async def temp_query():
                    logging.debug("Sending startup queries")
                    for i in range(3):
                        await pathway.query()
                        await asyncio.sleep(1.5)

                asyncio.ensure_future(temp_query())

            async def handle_membership(domain_type_group_membership):
                await self.discard_multicast_group(domain_type_group_membership.multicast_group)
                struct_name = domain_type_group_membership.struct_name.decode("UTF-8")
                with (await self._type_group_pathways_lock):
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
                    else:
                        logging.info("Multicast already group exists for pathway: {}:{}".format(
                            struct_name,
                            socket.inet_ntoa(domain_type_group_membership.multicast_group)
                        ))

            async def handle_query(_):
                with (await self._type_group_pathways_lock):
                    pathways = self._type_group_pathways
                for struct_name, value in pathways.items():
                    logging.debug("Responding to DomainTypeGroupMembership query: {}:{}".format(
                        struct_name,
                        socket.inet_ntoa(value[0])
                    ))
                    await pathway.send_struct(DomainTypeGroupMembership(
                        struct_name=bytes(struct_name, "UTF-8"),
                        multicast_group=value[0]
                    ))

            handle_future = asyncio.ensure_future(
                self.handle_type(DomainTypeGroupMembership,
                                 query_handlers=(
                                     handle_query,
                                 ),
                                 data_handlers=(
                                     handle_membership,
                                 )
                                 ))
            handle_future.add_done_callback(startup_query)

        register_future = asyncio.ensure_future(
            self.register_pathway(DomainTypeGroupMembership,
                                  multicast_group=socket.inet_aton('239.255.0.1')))

        register_future.add_done_callback(handler_startup)

    async def get_multicast_group(self):
        with (await self._available_groups_lock):
            return self._available_groups.pop()

    async def discard_multicast_group(self, multicast_group):
        with (await self._available_groups_lock):
            self._available_groups.discard(multicast_group)

    async def multicast_group_available(self, multicast_group):
        with (await self._available_groups_lock):
            return multicast_group in self._available_groups

    async def register_pathway(self, capnproto_struct, multicast_group=None):
        pathway = None
        struct_name = capnproto_struct.__name__
        with (await self._type_group_pathways_lock):
            if multicast_group is not None:
                if not (await self.multicast_group_available(multicast_group)):
                    if struct_name in self._type_group_pathways:
                        if self._type_group_pathways[struct_name][0] != multicast_group:
                            raise ValueError("Given multicast is assigned to another struct")
                        elif self._type_group_pathways[struct_name][1] is not None:
                            logging.warning("Requested pathway already registered: {}:{}".format(
                                struct_name,
                                socket.inet_ntoa(multicast_group)
                            ))
                            return
                logging.info("Registering pathway to requested multicast group: {}:{}".format(
                    struct_name,
                    socket.inet_ntoa(multicast_group)
                ))
            else:
                if struct_name not in self._type_group_pathways:
                    multicast_group = await self.get_multicast_group()
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

            pathway = DomainTypeGroupPathway(capnproto_struct, multicast_group=multicast_group)
            self._type_group_pathways[struct_name] = (
                multicast_group,
                pathway
            )
            logging.info("Registered pathway: {}:{}".format(
                struct_name, socket.inet_ntoa(multicast_group)
            ))

            while pathway.transport is None:
                await asyncio.sleep(.1)
            await pathway.send_struct(DomainTypeGroupMembership(
                struct_name=bytes(struct_name, "UTF-8"),
                multicast_group=multicast_group
            ))

        return pathway

    async def get_pathway(self, capnproto_struct):
        with (await self._type_group_pathways_lock):
            return self._type_group_pathways[capnproto_struct.__name__][1]

    async def handle_type(self, capnproto_struct, query_handlers=tuple(), data_handlers=tuple()):
        pathway = await self.get_pathway(capnproto_struct)
        await pathway.handle(query_handlers=query_handlers, data_handlers=data_handlers)
        logging.info("Registered handlers for {}".format(capnproto_struct.__name__))

    async def query_type(self, capnproto_struct):
        pathway = await self.get_pathway(capnproto_struct)
        await pathway.query()

    async def send_struct(self, capnproto_object):
        pathway = await self.get_pathway(type(capnproto_object))
        await pathway.send_struct(capnproto_object)
