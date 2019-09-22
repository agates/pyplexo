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

from domaintypesystem import create_receptor, create_synapse, create_transmitter


async def print_handler(data_type_group_message, address, received_timestamp):
    try:
        logging.debug("Print handler: {0}, address: {1}, timestamp: {2}".format(
            data_type_group_message.struct_name, address, received_timestamp))
    except Exception as e:
        logging.error(e)


def run(dts=None, loop=None):
    logging.basicConfig(level=logging.INFO)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    if not dts:  # pragma: no cover
        dts = DomainTypeSystem(loop=loop)

    handle_coro = asyncio.ensure_future(dts.react_to_all((print_handler,)))

    if not loop.is_running():  # pragma: no cover
        loop.run_until_complete(handle_coro)
        try:
            #signal.signal(signal.SIGINT, signal.default_int_handler)
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        return loop.create_task(handle_coro)

    if not dts:  # pragma: no cover
        dts.close()


if __name__ == "main":
    run()
