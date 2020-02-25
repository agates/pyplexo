#!/usr/bin/env python3
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
import ipaddress
import logging

from domaintypesystem.synapse import DTSZmqEpgmSynapse
from domaintypesystem.transmitter import DTSTransmitter, DTSTransmitterBase

test_ip_address = ipaddress.IPv4Address('239.255.0.1')
test_port = 6000


async def send_hello_str(transmitter: DTSTransmitterBase):
    i = 1
    while True:
        message = "Hello, DTS+EPGM {} …".format(i)
        print("Sending message: {}".format(message))
        await transmitter.transmit(message)
        i += i
        await asyncio.sleep(1/60)


def run(dts=None, loop=None):
    logging.basicConfig(level=logging.INFO)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    if not dts:  # pragma: no cover
        #dts = DomainTypeSystem(loop=loop)
        pass

    #handle_coro = asyncio.ensure_future(dts.react_to_all((print_handler,)))

    synapse = DTSZmqEpgmSynapse[str]("example_string",
                                     ip_address=test_ip_address,
                                     port=test_port,
                                     loop=loop)
    transmitter = DTSTransmitter[str](synapse, str.encode)

    send_hello_str_coro = loop.ensure_future(send_hello_str(transmitter))

    if not loop.is_running():  # pragma: no cover
        #loop.run_until_complete(handle_coro)
        try:
            #signal.signal(signal.SIGINT, signal.default_int_handler)
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        loop.create_task(send_hello_str_coro)

    if not dts:  # pragma: no cover
        #dts.close()
        pass


if __name__ == "main":
    run()
