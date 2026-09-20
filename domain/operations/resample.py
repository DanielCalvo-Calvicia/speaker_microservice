"""Streaming sample-rate conversion of 16-bit little-endian PCM.

The speaker plays what it is sent (the format the stream announced) unless the output device
cannot open at that rate; then, and only then, the audio is converted to the device's rate so it
is heard at the right pitch and speed.
"""

from array import array
from sys import byteorder

from domain.errors import InvalidPlaybackFormat

_BYTES_PER_SAMPLE = 2


class LinearResampler:
    """Converts PCM16 chunks from ``src_rate`` to ``dst_rate`` with linear interpolation.

    It is stateful: samples and the fractional position at the end of one chunk carry over to the
    next, so chunk boundaries are inaudible and chunks may be any size (a sample split across two
    chunks is reassembled).
    """

    def __init__(self, src_rate: int, dst_rate: int, channels: int) -> None:
        if min(src_rate, dst_rate, channels) <= 0:
            raise InvalidPlaybackFormat("Sample rates and channel count must be positive.")
        self._step = src_rate / dst_rate
        self._channels = channels
        self._frame_bytes = channels * _BYTES_PER_SAMPLE
        self._pending = b""  # bytes of an incomplete frame
        self._tail: list[array] = [array("h") for _ in range(channels)]
        self._phase = 0.0  # position of the next output sample within ``_tail``

    def process(self, data: bytes) -> bytes:
        data = self._pending + data
        usable = len(data) - len(data) % self._frame_bytes
        self._pending = data[usable:]
        if usable == 0:
            return b""

        samples = array("h")
        samples.frombytes(data[:usable])
        if byteorder == "big":
            samples.byteswap()
        channels = [
            self._tail[c] + samples[c :: self._channels] for c in range(self._channels)
        ]

        available = len(channels[0])
        outputs: list[array] = [array("h") for _ in range(self._channels)]
        position = self._phase
        while int(position) + 1 < available:
            left = int(position)
            fraction = position - left
            for channel, out in zip(channels, outputs, strict=True):
                out.append(round(channel[left] * (1 - fraction) + channel[left + 1] * fraction))
            position += self._step

        keep_from = min(int(position), available)
        self._tail = [channel[keep_from:] for channel in channels]
        self._phase = position - keep_from

        frames = len(outputs[0])
        interleaved = array("h", bytes(frames * self._frame_bytes))
        for index, out in enumerate(outputs):
            interleaved[index :: self._channels] = out
        if byteorder == "big":
            interleaved.byteswap()
        return interleaved.tobytes()
