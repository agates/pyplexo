#  pyplexo
#  Copyright © 2018-2023  Alecks Gates
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

from typing import Callable, Coroutine, Optional
from uuid import UUID

from plexo.neuron.neuron import Neuron
from plexo.typing import UnencodedType, EncodedType

Reactant = Callable[[UnencodedType, Neuron[UnencodedType], Optional[UUID]], Coroutine]

# Neuron on the reactant is necessary for when the reactant won't
# otherwise know the type of the data being reacted upon.
# Without this it's impossible to understand raw binary data or what to do with it
RawReactant = Callable[[EncodedType, Neuron[UnencodedType], Optional[UUID]], Coroutine]
