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
import asyncio
import ipaddress
import logging

from plexo.ganglion import GanglionMulticast

test_multicast_cidr = ipaddress.ip_network('239.255.0.0/16')
test_port = 5561


def run(loop=None):
    logging.basicConfig(level=logging.INFO)

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    ganglion = GanglionMulticast(multicast_cidr=test_multicast_cidr,
                                 port=test_port,
                                 heartbeat_interval_seconds=10,
                                 loop=loop)

    if not loop.is_running():  # pragma: no cover
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    ganglion.close()


if __name__ == "__main__":
    run()
