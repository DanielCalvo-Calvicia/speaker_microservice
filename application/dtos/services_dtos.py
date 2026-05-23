from dataclasses import dataclass
from typing import AsyncIterator

@dataclass(slots=True, frozen=True)
class PlaybackStreamRequestDto:
    """Internal service DTO wrapping the decoupled audio playback task."""
    audio_stream: AsyncIterator[bytes]
    sample_rate: int
    channels: int

@dataclass(slots=True, frozen=True)
class PlaybackStreamResponseDto:
    """Core domain playback result."""
    success: bool
    message: str

@dataclass(slots=True, frozen=True)
class SpeakerCleanupResponseDto:
    """Agnostic domain container for device release operations."""
    success: bool
