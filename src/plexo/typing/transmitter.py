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

from typing import Optional, Coroutine, Protocol
from uuid import UUID

from plexo.neuron.neuron import Neuron
from plexo.typing import UnencodedSignal, EncodedSignal


class ExternalTransmitter(Protocol):
    def __call__(
        self,
        data: EncodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ) -> Coroutine:
        ...


class Transmitter(Protocol):
    def __call__(
        self,
        data: UnencodedSignal,
        neuron: Optional[Neuron[UnencodedSignal]] = None,
        reaction_id: Optional[UUID] = None,
    ) -> Coroutine:
        ...
