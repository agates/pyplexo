#  pyplexo
#   Copyright (C) 2020  Alecks Gates
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import ipaddress
from typing import Type, Union

from pyrsistent import pmap


class ProposalManager:
    def __init__(self):
        self._proposal_map = pmap()
        self._temporary_proposal_map = pmap()

    def get_current_proposal(self, _type: Type):
        if _type not in self._proposal_map:
            return None

        return self._proposal_map[_type]

    def get_current_proposal_id(self, _type: Type):
        return self.get_current_proposal(_type)[0]

    def get_next_proposal_id(self, _type: Type):
        if _type not in self._proposal_map:
            return 0

        return self.get_current_proposal_id(_type) + 1

    def promise_proposal_id(self, _type: Type, proposal_id: int):
        current_proposal = self.get_current_proposal(_type)

        if current_proposal:
            if proposal_id <= current_proposal[0]:
                raise Exception("Cannot promise proposal_id less than or equal to existing proposal_id")
            ip_address = current_proposal[1]
        else:
            ip_address = None

        self._temporary_proposal_map.set(_type, (proposal_id, ip_address))

    def propose_proposal_id(self, _type: Type, proposal_id: int, ip_address: Union[ipaddress.IPv4Address,
                                                                                   ipaddress.IPv6Address]):
        current_proposal_id = self.get_current_proposal_id(_type)
        if proposal_id <= current_proposal_id:
            raise Exception("new proposal_id must be greater than existing proposal_id")

        self._temporary_proposal_map.set(_type, (proposal_id, ip_address))
