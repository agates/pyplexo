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


class Timer:
    def __init__(self, timeout, callback=None):
        self._timeout = timeout
        self._callback = callback
        self._task = None

    async def _job(self):
        await asyncio.sleep(self._timeout)
        if self._callback:
            await self._callback()

    def start(self):
        self._task = asyncio.ensure_future(self._job())

    async def wait(self):
        return await self._task

    def cancel(self):
        self._task.cancel()
