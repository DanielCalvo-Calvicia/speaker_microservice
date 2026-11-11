"""The null playback backend (T-01.3, ADR-012): drains the stream, takes the time the audio would take, plays nothing."""

import asyncio

import pytest

from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from domain.value_objects.playback_format import PlaybackFormat
from infrastructure.outbound.null_playback.null_audio_playback import (
    NULL_NOTE,
    NullAudioPlayback,
)

MONO_24K = PlaybackFormat(sample_rate=24000, channels=1)
BYTES_PER_SECOND = 24000 * 2


class FakeClock:
    """Time that only moves when somebody sleeps; each sleep also lets the other tasks run."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


def new_sink(clock: FakeClock, realtime: bool = True) -> NullAudioPlayback:
    return NullAudioPlayback(realtime=realtime, sleep=clock.sleep, monotonic=clock.monotonic)


async def audio(*chunks: bytes):
    for chunk in chunks:
        yield chunk


def seconds_of_audio(seconds: float) -> bytes:
    return bytes(int(seconds * BYTES_PER_SECOND))


def run(coro):
    return asyncio.run(coro)


def collect():
    started: list[PlaybackOutboundDTO] = []
    return started, started.append


def test_the_stream_is_drained_completely_however_fast_it_comes_and_the_result_says_it_finished():
    async def scenario():
        consumed = 0

        async def endless_fast_sender():
            nonlocal consumed
            for _ in range(1000):
                consumed += 1
                yield b"\x01\x00" * 100

        started, on_started = collect()
        result = await new_sink(FakeClock(), realtime=False).play(
            MONO_24K, endless_fast_sender(), on_started
        )
        assert consumed == 1000
        assert started == [PlaybackOutboundDTO(success=True, message="Playback stream started")]
        assert result == PlaybackOutboundDTO(
            success=True, message="Playback session finalized successfully"
        )

    run(scenario())


def test_the_call_lasts_as_long_as_the_audio_would_play_when_the_sender_is_faster_than_real_time():
    async def scenario():
        clock = FakeClock()
        start = clock.now
        sink = new_sink(clock)
        # 3 s of audio handed over at once, as tts does: the real device would still be playing it
        result = await sink.play(MONO_24K, audio(seconds_of_audio(3.0)), lambda dto: None)
        assert result.success is True
        assert clock.now - start == pytest.approx(3.0)
        assert sink.is_playing() is False

    run(scenario())


def test_without_pacing_the_call_returns_at_once():
    async def scenario():
        clock = FakeClock()
        await new_sink(clock, realtime=False).play(
            MONO_24K, audio(seconds_of_audio(3.0)), lambda dto: None
        )
        assert clock.sleeps == []

    run(scenario())


def test_the_duration_counts_the_channels_and_the_rate():
    async def scenario():
        clock = FakeClock()
        start = clock.now
        stereo_48k = PlaybackFormat(sample_rate=48000, channels=2)
        await new_sink(clock).play(
            stereo_48k, audio(bytes(48000 * 2 * 2 * 2)), lambda dto: None  # 2 s of stereo 16-bit
        )
        assert clock.now - start == pytest.approx(2.0)

    run(scenario())


def test_a_sender_slower_than_real_time_is_not_made_to_wait_more():
    async def scenario():
        clock = FakeClock()

        async def live_sender():
            for _ in range(3):
                await clock.sleep(1.0)  # one second of audio per second: the device is never ahead
                yield seconds_of_audio(1.0)

        start = clock.now
        await new_sink(clock).play(MONO_24K, live_sender(), lambda dto: None)
        assert clock.now - start == pytest.approx(3.0)  # no extra wait at the end

    run(scenario())


def test_empty_chunks_and_an_empty_body_end_at_once_with_success():
    async def scenario():
        clock = FakeClock()
        started, on_started = collect()
        result = await new_sink(clock).play(MONO_24K, audio(b"", b""), on_started)
        assert result.success is True and clock.sleeps == []
        assert len(started) == 1

    run(scenario())


def test_an_error_in_the_stream_is_reported_in_the_result_not_raised_and_is_not_paced():
    async def scenario():
        clock = FakeClock()

        async def broken():
            yield seconds_of_audio(5.0)
            raise RuntimeError("the sender went away")

        started, on_started = collect()
        result = await new_sink(clock).play(MONO_24K, broken(), on_started)
        assert result == PlaybackOutboundDTO(success=False, message="the sender went away")
        assert clock.sleeps == []
        assert started[0].success is True

    run(scenario())


def test_a_new_playback_supersedes_the_running_one_which_ends_early():
    async def scenario():
        clock = FakeClock()
        sink = new_sink(clock)
        first = asyncio.create_task(
            sink.play(MONO_24K, audio(seconds_of_audio(60.0)), lambda dto: None)
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert sink.is_playing() is True
        start = clock.now
        second = await sink.play(MONO_24K, audio(seconds_of_audio(1.0)), lambda dto: None)
        first_result = await first
        assert first_result == PlaybackOutboundDTO(
            success=True, message="Playback session superseded by new request"
        )
        assert second.message == "Playback session finalized successfully"
        assert clock.now - start < 5.0  # the 60 s playback did not run to its end
        assert sink.is_playing() is False

    run(scenario())


def test_close_stops_the_running_playback_and_is_idempotent():
    async def scenario():
        clock = FakeClock()
        sink = new_sink(clock)
        playing = asyncio.create_task(
            sink.play(MONO_24K, audio(seconds_of_audio(60.0)), lambda dto: None)
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        start = clock.now
        await sink.close()
        await sink.close()
        result = await playing
        assert result.success is True
        assert clock.now - start < 5.0
        assert sink.is_playing() is False

    run(scenario())


def test_close_without_a_playback_does_nothing():
    run(NullAudioPlayback().close())


def test_the_readiness_is_ready_and_carries_the_note_that_says_it_is_a_null_sink():
    readiness = run(NullAudioPlayback().check_readiness())
    assert readiness.is_ready is True
    assert readiness.message == NULL_NOTE
    assert "null" in NULL_NOTE and "SPEAKER_BACKEND" in NULL_NOTE


def test_the_default_is_paced_to_real_time():
    assert NullAudioPlayback()._realtime is True


def test_the_end_of_a_superseded_playback_does_not_end_the_newer_one():
    async def scenario():
        clock = FakeClock()
        sink = new_sink(clock)
        first = asyncio.create_task(
            sink.play(MONO_24K, audio(seconds_of_audio(60.0)), lambda dto: None)
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        gate = asyncio.Event()

        async def open_body():
            yield b"\x00\x00" * 10
            await gate.wait()

        second = asyncio.create_task(sink.play(MONO_24K, open_body(), lambda dto: None))
        await asyncio.sleep(0)
        await first  # the first one notices it was replaced and ends
        assert sink.is_playing() is True  # the newer playback is still going
        gate.set()
        await second
        assert sink.is_playing() is False

    run(scenario())


def test_a_playback_that_was_replaced_stops_reading_its_stream():
    async def scenario():
        clock = FakeClock()
        sink = new_sink(clock)
        produced = 0

        async def long_body():
            nonlocal produced
            for _ in range(50):
                produced += 1
                yield b"\x00\x00" * 10
                await asyncio.sleep(0)

        first = asyncio.create_task(sink.play(MONO_24K, long_body(), lambda dto: None))
        await asyncio.sleep(0)
        second = asyncio.create_task(sink.play(MONO_24K, audio(b"\x00\x00"), lambda dto: None))
        await first
        await second
        assert produced < 10  # it noticed it was replaced and stopped reading, it did not drain all 50

    run(scenario())


def test_a_duration_that_is_not_a_whole_number_of_polls_is_not_overshot():
    async def scenario():
        clock = FakeClock()
        start = clock.now
        await new_sink(clock).play(MONO_24K, audio(seconds_of_audio(0.25)), lambda dto: None)
        assert clock.now - start == pytest.approx(0.25)

    run(scenario())
