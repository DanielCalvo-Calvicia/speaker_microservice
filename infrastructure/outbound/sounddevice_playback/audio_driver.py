"""What the sounddevice adapter needs from the audio driver (the seam faked in tests)."""

from dataclasses import dataclass
from typing import Any, Protocol

from domain.value_objects.playback_format import PlaybackFormat


@dataclass(slots=True, frozen=True)
class DeviceInfo:
    index: int
    name: str
    max_output_channels: int


class RawOutput(Protocol):
    @property
    def active(self) -> bool: ...

    def write(self, data: bytes) -> Any: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


class AudioDriver(Protocol):
    def output_devices(self) -> list[DeviceInfo]:
        """Every device the driver knows, inputs and outputs."""
        ...

    def default_output_index(self) -> int | None: ...

    def device_info(self, index: int) -> DeviceInfo:
        """Raises if ``index`` is not a valid device."""
        ...

    def open_output(self, index: int, audio_format: PlaybackFormat) -> RawOutput:
        """Open and start an int16 output stream; raises if the format is unsupported."""
        ...
