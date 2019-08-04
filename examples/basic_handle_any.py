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
import logging
import signal

from domaintypesystem import DomainTypeSystem

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()

dts = DomainTypeSystem(loop=loop)


async def print_handler(data_type_group_message, address, received_timestamp):
    try:
        logging.debug("Print handler: {0}, address: {1}, timestamp: {2}".format(
            data_type_group_message.struct_name, address, received_timestamp))
    except Exception as e:
        logging.error(e)


asyncio.ensure_future(dts.handle_any((print_handler,)))

try:
    signal.signal(signal.SIGINT, signal.default_int_handler)
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()
