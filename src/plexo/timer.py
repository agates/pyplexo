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

import asyncio
from asyncio import Future
from typing import Optional


class Timer:
    def __init__(self, timeout, callback=None):
        self._timeout = timeout
        self._callback = callback
        self._task: Optional[Future] = None

    async def _job(self):
        await asyncio.sleep(self._timeout)
        if self._callback:
            await self._callback()

    def start(self):
        self._task = asyncio.ensure_future(self._job())

    async def wait(self):
        if self._task:
            return await self._task

    def cancel(self):
        if self._task:
            self._task.cancel()
