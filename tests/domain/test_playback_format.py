import pytest

from domain.errors import InvalidPlaybackFormat
from domain.operations.format_negotiation import fallback_formats
from domain.value_objects.playback_format import PlaybackFormat


def test_valid_format_keeps_its_values():
    fmt = PlaybackFormat(sample_rate=24000, channels=1)
    assert (fmt.sample_rate, fmt.channels) == (24000, 1)


@pytest.mark.parametrize(
    ("sample_rate", "channels", "message"),
    [
        (0, 1, "Invalid sample rate. Must be positive."),
        (-1, 1, "Invalid sample rate. Must be positive."),
        (24000, 0, "Invalid channel count. Must be positive."),
        (24000, -2, "Invalid channel count. Must be positive."),
    ],
)
def test_non_positive_values_are_rejected(sample_rate, channels, message):
    with pytest.raises(InvalidPlaybackFormat, match=message):
        PlaybackFormat(sample_rate=sample_rate, channels=channels)


def test_invalid_format_is_still_a_value_error():
    with pytest.raises(ValueError):
        PlaybackFormat(sample_rate=0, channels=1)


def test_with_sample_rate_returns_a_new_format():
    fmt = PlaybackFormat(sample_rate=24000, channels=2)
    assert fmt.with_sample_rate(44100) == PlaybackFormat(sample_rate=44100, channels=2)


def test_fallback_tries_requested_then_fallback_rate():
    requested = PlaybackFormat(sample_rate=24000, channels=1)
    assert fallback_formats(requested) == (requested, PlaybackFormat(44100, 1))


def test_fallback_skips_a_repeat_of_the_requested_format():
    requested = PlaybackFormat(sample_rate=44100, channels=2)
    assert fallback_formats(requested) == (requested,)
