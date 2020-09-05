#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#    plexo
#    Copyright (C) 2018-2020  Alecks Gates
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
from timeit import default_timer as timer

from plexo.synapse import SynapseZmqEPGM
from plexo.transmitter import create_transmitter

test_ip_address = ipaddress.IPv4Address('239.255.0.1')
test_port = 5561


async def send_hello_str(transmitter):
    i = 1
    while True:
        start_time = timer()
        message = "Hello, Plexo+EPGM {} …".format(i)
        logging.info("Sending message: {}".format(message))
        await transmitter(message)
        i += 1
        await asyncio.sleep(1-(start_time-timer()))


def run(loop=None):
    logging.basicConfig(level=logging.DEBUG)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    synapse = SynapseZmqEPGM[str]("example_string",
                                  multicast_address=test_ip_address,
                                  port=test_port,
                                  loop=loop)
    transmitter = create_transmitter((synapse,), str.encode)

    loop.create_task(send_hello_str(transmitter))

    if not loop.is_running():  # pragma: no cover
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    synapse.close()


if __name__ == "__main__":
    run()
