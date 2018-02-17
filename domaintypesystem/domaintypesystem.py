import asyncio
import functools
import logging
import socket
import struct


GROUP = "224.0.0.1"
PORT = 5555


class DiscoveryClientProtocol:
    def __init__(self, loop, addr):
        self.loop = loop
        self.transport = None
        self.addr = addr

    def connection_made(self, transport):
        self.transport = transport
        sock = self.transport.get_extra_info('socket')
        sock.settimeout(3)
        addrinfo = socket.getaddrinfo(self.addr, None)[0]
        if addrinfo[0] == socket.AF_INET: # IPv4
            ttl = struct.pack('@i', 1)
            sock.setsockopt(socket.IPPROTO_IP,
                socket.IP_MULTICAST_TTL, ttl)
        else:
            ttl = struct.pack('@i', 2)
            sock.setsockopt(socket.IPPROTO_IPV6,
                socket.IPV6_MULTICAST_HOPS, ttl)

        #self.transport.sendto(sys.argv[1].encode("ascii"), (self.addr, PORT))

    def datagram_received(self, data, addr):
        print("Reply from {}: {!r}".format(addr, data))
        # Don't close the socket as we might get multiple responses.

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Socket closed, stop the event loop")
        self.loop.stop()


class MulticastServerProtocol:
    def __init__(self, handler):
        print("init function")
        handler()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print('Received {!r} from {!r}'.format(data, addr))
        data = "I received {!r}".format(data).encode("ascii")
        print('Send {!r} to {!r}'.format(data, addr))
        # Handle the data somehow


class DomainTypeSystem:

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.loop.set_debug(True)
        logging.basicConfig(level=logging.DEBUG)

        addrinfo = socket.getaddrinfo(GROUP, None)[0]
        print(addrinfo)
        sock = socket.socket(addrinfo[0], socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])

        if addrinfo[0] == socket.AF_INET:  # IPv4
            #sock.bind((GROUP, PORT))
            sock.bind(('', PORT))
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, mreq)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        else:
            #sock.bind((GROUP, PORT))
            sock.bind(('', PORT))
            mreq = group_bin + struct.pack('@I', 0)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        listen = self.loop.create_datagram_endpoint(
            functools.partial(MulticastServerProtocol, lambda: print("In handler")),
            sock=sock,
        )

        #client_listener = self.loop.create_datagram_endpoint(
        #    lambda: DiscoveryClientProtocol(self.loop, GROUP),
        #    sock=sock,
        #)

        self.transport, self.protocol = self.loop.run_until_complete(listen)
        #self.client_transport, self.client_protocol = self.loop.run_until_complete(client_listener)
        #self.transport.sendto(b"Hello world")

    async def send(self):
        while True:
            await asyncio.sleep(1)
            print("Sending data")
            self.transport.sendto(b"Hello world", (GROUP, PORT))

    def register_type(self, capnproto_struct):
        pass


class DomainTypeSystemQuery:
    def __init__(self):
        raise NotImplementedError


class DomainTypeSystemStruct:
    def __init__(self):
        raise NotImplementedError


class DomainTypeSystemRegistration:
    def __init__(self, type):
        self.type = type

        # query for type on multicast address
        # if response, use existing multicast group for type
        # if no response, register multicast group for type

    def handle(self, handlers):
        raise NotImplementedError

    def send(self, struct):
        raise NotImplementedError
