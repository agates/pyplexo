#  pyplexo
#   Copyright © 2018-2020  Alecks Gates
#
#  pyplexo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  pyplexo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with pyplexo.  If not, see <https://www.gnu.org/licenses/>.
import hashlib
import socket


def get_primary_ip():
    # from https://stackoverflow.com/a/28950776
    _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # noinspection PyBroadException
    try:
        # doesn't even have to be reachable
        _socket.connect(("10.255.255.255", 1))
        ip_address = _socket.getsockname()[0]
    except Exception:
        ip_address = "127.0.0.1"
    finally:
        _socket.close()

    return ip_address


def get_hashed_primary_ip():
    return hashlib.sha1(get_primary_ip().encode("UTF-8")).digest()


def get_machine_id():
    with open("/etc/machine-id", "rb") as machine_id_file:
        machine_id_hex = machine_id_file.read()
    return machine_id_hex.rstrip()


def get_hashed_machine_id():
    return hashlib.sha1(get_machine_id()).digest()
