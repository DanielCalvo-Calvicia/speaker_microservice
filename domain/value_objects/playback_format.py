from dataclasses import dataclass, replace

from domain.errors import InvalidPlaybackFormat


@dataclass(slots=True, frozen=True)
class PlaybackFormat:
    """Describes a PCM (16-bit) playback: how fast and how many channels.

    Invariant: every field is strictly positive.
    """

    sample_rate: int
    channels: int

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise InvalidPlaybackFormat("Invalid sample rate. Must be positive.")
        if self.channels <= 0:
            raise InvalidPlaybackFormat("Invalid channel count. Must be positive.")

    def with_sample_rate(self, sample_rate: int) -> "PlaybackFormat":
        return replace(self, sample_rate=sample_rate)
