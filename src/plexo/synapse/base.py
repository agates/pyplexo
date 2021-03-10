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
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional
from uuid import UUID

from pyrsistent import PDeque, pdeque, pset

from plexo.typing.receptor import Receptor


class SynapseBase(ABC):
    def __init__(
        self, topic: str, receptors: Iterable[Receptor] = (), loop=None
    ) -> None:
        self.topic = topic
        self.topic_bytes = topic.encode("UTF-8")

        self._receptors = pset(receptors)
        self._receptors_write_lock = asyncio.Lock()

        self._tasks: PDeque = pdeque()

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            self._tasks = pdeque()

    def _add_task(self, task):
        self._tasks = self._tasks.append(task)

    @property
    def receptors(self):
        return self._receptors

    async def update_receptors(self, receptors: Iterable[Receptor]):
        async with self._receptors_write_lock:
            self._receptors = self._receptors.update(receptors)

    @abstractmethod
    async def transmit(self, data: Any, reaction_id: Optional[UUID] = None):
        ...
