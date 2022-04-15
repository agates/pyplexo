from typing import Optional, Coroutine, Protocol
from uuid import UUID

from plexo.typing import UnencodedSignal, Signal


class EncoderTransmitter(Protocol):
    def __call__(
        self, data: UnencodedSignal, reaction_id: Optional[UUID] = None
    ) -> Coroutine:
        ...


class Transmitter(Protocol):
    def __call__(self, data: Signal, reaction_id: Optional[UUID] = None) -> Coroutine:
        ...
