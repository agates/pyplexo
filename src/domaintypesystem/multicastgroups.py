import asyncio
import ipaddress
import sys

this = sys.modules[__name__]

this._available_groups = {ip_address.packed for ip_address in ipaddress.ip_network('239.255.0.0/16')
                          if 0 < int(ip_address) & 0xff < 255}
this._available_groups_lock = asyncio.Lock()


async def get_multicast_group():
    async with this._available_groups_lock:
        return this._available_groups.pop()


async def discard_multicast_group(multicast_group):
    async with this._available_groups_lock:
        this._available_groups.discard(multicast_group)


async def multicast_group_available(multicast_group):
    async with this._available_groups_lock:
        return multicast_group in this._available_groups
