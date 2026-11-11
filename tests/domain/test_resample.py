import array
import math

import pytest

from domain.errors import InvalidPlaybackFormat
from domain.operations.resample import LinearResampler


def _pcm(samples: list[int]) -> bytes:
    return array.array("h", samples).tobytes()


def _samples(pcm: bytes) -> list[int]:
    out = array.array("h")
    out.frombytes(pcm)
    return list(out)


def _tone(rate: int, seconds: float, frequency: int = 440) -> list[int]:
    return [round(8000 * math.sin(2 * math.pi * frequency * n / rate)) for n in range(int(rate * seconds))]


def test_output_length_follows_the_rate_ratio():
    resampler = LinearResampler(24000, 44100, channels=1)

    out = resampler.process(_pcm([100] * 24000))

    assert abs(len(out) // 2 - 44100) <= 2
    assert set(_samples(out)) == {100}  # a constant signal stays constant


def test_pitch_is_preserved_when_played_at_the_device_rate():
    source = _tone(24000, 1.0)
    out = _samples(LinearResampler(24000, 44100, channels=1).process(_pcm(source)))

    rising = sum(1 for a, b in zip(out, out[1:], strict=False) if a < 0 <= b)
    assert abs(rising - 440) <= 2  # one second of audio still holds ~440 cycles


def test_chunk_boundaries_do_not_change_the_result():
    pcm = _pcm(_tone(24000, 0.5))
    whole = LinearResampler(24000, 44100, channels=1).process(pcm)

    chunked = LinearResampler(24000, 44100, channels=1)
    pieces = [chunked.process(pcm[i : i + 333]) for i in range(0, len(pcm), 333)]  # odd, even splits

    assert b"".join(pieces) == whole


def test_stereo_channels_stay_separate():
    left, right = [1000] * 100, [-1000] * 100
    interleaved = [value for pair in zip(left, right, strict=True) for value in pair]

    out = _samples(LinearResampler(8000, 16000, channels=2).process(_pcm(interleaved)))

    assert set(out[0::2]) == {1000} and set(out[1::2]) == {-1000}


def test_empty_and_partial_frames_produce_no_output_but_are_not_lost():
    resampler = LinearResampler(8000, 16000, channels=1)
    assert resampler.process(b"") == b""
    assert resampler.process(b"\x10") == b""  # half a sample is held back
    assert len(resampler.process(b"\x00" + _pcm([5] * 10))) > 0


def test_invalid_parameters_are_rejected():
    with pytest.raises(InvalidPlaybackFormat):
        LinearResampler(0, 44100, channels=1)
