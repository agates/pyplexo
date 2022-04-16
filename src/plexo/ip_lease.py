#  pyplexo
#  Copyright © 2018-2022  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.

from pyrsistent import pmap

from plexo.exceptions import IpLeaseExists, IpNotFound, IpNotLeased, IpsExhausted
from plexo.typing import IPAddress, IPNetwork


class IpLeaseManager:
    def __init__(self, ip_cidr: IPNetwork):
        self._ip_lease_map = pmap({ip_address: False for ip_address in ip_cidr})
        self._available_ips = set(self._ip_lease_map.keys())

    def lease_address(self, ip_address: IPAddress):
        if ip_address not in self._ip_lease_map:
            raise IpNotFound(f"ip_address {ip_address} not found")

        if self._ip_lease_map[ip_address]:
            raise IpLeaseExists(f"ip_address {ip_address} is already leased")

        self._ip_lease_map = self._ip_lease_map.set(ip_address, True)
        self._available_ips.discard(ip_address)

        return ip_address

    def release_address(self, ip_address: IPAddress):
        if ip_address not in self._ip_lease_map:
            raise IpNotFound(f"ip_address {ip_address} not found")

        if not self._ip_lease_map[ip_address]:
            raise IpNotLeased(f"ip_address {ip_address} is not leased")

        self._ip_lease_map = self._ip_lease_map.set(ip_address, False)
        self._available_ips.add(ip_address)

        return ip_address

    def address_is_leased(self, ip_address: IPAddress):
        if ip_address not in self._ip_lease_map:
            raise IpNotFound(f"ip_address {ip_address} not found")

        return self._ip_lease_map[ip_address]

    def get_address(self) -> IPAddress:
        try:
            ip_address = self._available_ips.pop()
        except KeyError:
            raise IpsExhausted("No more ip addresses are available")

        return self.lease_address(ip_address)
