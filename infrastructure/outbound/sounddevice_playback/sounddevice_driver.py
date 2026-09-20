"""The only module that imports ``sounddevice``."""

from typing import Any, cast

import sounddevice as sd

from domain.value_objects.playback_format import PlaybackFormat
from infrastructure.outbound.sounddevice_playback.audio_driver import DeviceInfo, RawOutput


def _to_info(index: int, raw: Any) -> DeviceInfo:
    return DeviceInfo(
        index=index,
        name=str(raw.get("name")),
        max_output_channels=int(raw.get("max_output_channels", 0)),
    )


class SoundDeviceDriver:
    def output_devices(self) -> list[DeviceInfo]:
        return [_to_info(index, raw) for index, raw in enumerate(sd.query_devices())]

    def default_output_index(self) -> int | None:
        default_output = sd.default.device[1]
        return None if default_output is None else int(default_output)

    def device_info(self, index: int) -> DeviceInfo:
        return _to_info(index, sd.query_devices(index))

    def open_output(self, index: int, audio_format: PlaybackFormat) -> RawOutput:
        raw_stream: Any = sd.RawOutputStream(
            samplerate=audio_format.sample_rate,
            channels=audio_format.channels,
            dtype="int16",
            device=index,
        )
        try:
            raw_stream.start()
        except Exception:
            raw_stream.close()
            raise
        return cast(RawOutput, raw_stream)
