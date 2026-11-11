from domain.value_objects.playback_format import PlaybackFormat

FALLBACK_SAMPLE_RATE = 44100


def fallback_formats(
    requested: PlaybackFormat, fallback_rate: int = FALLBACK_SAMPLE_RATE
) -> tuple[PlaybackFormat, ...]:
    """Ordered list of formats to try when opening the output device.

    1. exactly what was requested;
    2. the same layout at the fallback sample rate (most drivers accept 44.1 kHz).

    A candidate that would repeat an earlier one is skipped.
    """
    candidates = [requested]

    at_fallback_rate = requested.with_sample_rate(fallback_rate)
    if at_fallback_rate != requested:
        candidates.append(at_fallback_rate)

    return tuple(candidates)
