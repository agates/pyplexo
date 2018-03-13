#!/usr/bin/env python3

import asyncio
import logging

from domaintypesystem import DomainTypeSystem

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
#loop.set_debug(True)

dts = DomainTypeSystem()


async def print_handler(data_type_group_message):
    logging.debug("Print handler: {0}, timestamp: {1}".format(data_type_group_message.struct_name, data_type_group_message.timestamp))

asyncio.ensure_future(dts.handle_any((print_handler,)))

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()
