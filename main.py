#!/usr/bin/env python3

import asyncio
import logging

from domaintypesystem import DomainTypeSystem

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
#loop.set_debug(True)

dts = DomainTypeSystem()

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()
