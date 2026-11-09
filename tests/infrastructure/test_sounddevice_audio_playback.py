"""SoundDeviceAudioPlayback and DeviceSelector against a fake ``AudioDriver``; no hardware."""

import asyncio
import time
from typing import Any

import pytest

from application.dtos.playback_outbound import PlaybackOutboundDTO
from application.errors import SpeakerUnavailable
from domain.value_objects.playback_format import PlaybackFormat
from infrastructure.outbound.sounddevice_playback import (
    sounddevice_audio_playback as playback_module,
)
from infrastructure.outbound.sounddevice_playback.audio_driver import DeviceInfo
from infrastructure.outbound.sounddevice_playback.sounddevice_audio_playback import (
    SoundDeviceAudioPlayback,
)
from infrastructure.outbound.sounddevice_playback.sounddevice_device_selector import (
    DeviceSelector,
)

FORMAT = PlaybackFormat(sample_rate=24000, channels=1)


class FakeRawOutput:
    def __init__(self) -> None:
        self.active = True
        self.written: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> Any:
        self.written.append(data)

    def stop(self) -> None:
        self.active = False

    def close(self) -> None:
        self.closed = True


class FakeDriver:
    def __init__(
        self,
        devices: list[DeviceInfo] | None = None,
        default_output: int | None = 1,
        unsupported_rates: tuple[int, ...] = (),
    ) -> None:
        self.devices = (
            devices
            if devices is not None
            else [
                DeviceInfo(0, "Mic", 0),
                DeviceInfo(1, "Speakers", 2),
            ]
        )
        self.default_output = default_output
        self.unsupported_rates = unsupported_rates
        self.opened: list[tuple[int, PlaybackFormat]] = []
        self.streams: list[FakeRawOutput] = []

    def output_devices(self) -> list[DeviceInfo]:
        return self.devices

    def default_output_index(self) -> int | None:
        return self.default_output

    def device_info(self, index: int) -> DeviceInfo:
        return self.devices[index]

    def open_output(self, index: int, audio_format: PlaybackFormat) -> FakeRawOutput:
        self.opened.append((index, audio_format))
        if audio_format.sample_rate in self.unsupported_rates:
            raise OSError(f"unsupported rate {audio_format.sample_rate}")
        stream = FakeRawOutput()
        self.streams.append(stream)
        return stream


def make_playback(
    driver: FakeDriver | None = None, **selector_args: Any
) -> SoundDeviceAudioPlayback:
    driver = driver or FakeDriver()
    return SoundDeviceAudioPlayback(driver, DeviceSelector(driver, **selector_args))


async def _audio(*chunks: bytes):
    for chunk in chunks:
        yield chunk


# ---- DeviceSelector -------------------------------------------------------------------------


def test_selector_prefers_the_configured_index():
    assert DeviceSelector(FakeDriver(), ("speak",), device_index=7).select() == 7


def test_selector_picks_first_output_device_matching_a_keyword():
    driver = FakeDriver(
        devices=[
            DeviceInfo(0, "Mic USB", 0),
            DeviceInfo(1, "Other", 2),
            DeviceInfo(2, "USB DAC", 2),
        ]
    )
    assert DeviceSelector(driver, ("usb",)).select() == 2


def test_selector_falls_back_to_the_default_output():
    assert DeviceSelector(FakeDriver(default_output=1), ("nomatch",)).select() == 1


def test_selector_fails_when_there_is_no_default_output():
    with pytest.raises(RuntimeError, match="No valid output devices discovered"):
        DeviceSelector(FakeDriver(default_output=None), ()).select()


def test_bootstrap_failure_is_reported_as_speaker_unavailable():
    with pytest.raises(SpeakerUnavailable, match="sounddevice bootstrap failed"):
        make_playback(FakeDriver(default_output=None))


# ---- readiness / availability ---------------------------------------------------------------


def test_ready_when_device_has_output_channels():
    async def run() -> None:
        result = await make_playback().check_readiness()
        assert result.is_ready is True and result.message is None

    asyncio.run(run())


def test_not_ready_when_device_has_no_output_channels():
    async def run() -> None:
        driver = FakeDriver(devices=[DeviceInfo(0, "Input Only", 0)], default_output=0)
        result = await make_playback(driver).check_readiness()
        assert result.is_ready is False
        assert result.message == "Selected device has no output channels."

    asyncio.run(run())


def test_not_ready_when_the_probe_raises():
    async def run() -> None:
        driver = FakeDriver()
        playback = make_playback(driver)
        driver.devices = []  # the device disappears
        result = await playback.check_readiness()
        assert result.is_ready is False and result.message

    asyncio.run(run())


def test_is_playing_reflects_the_flag():
    playback = make_playback()
    assert playback.is_playing() is False
    playback._is_playing = True
    assert playback.is_playing() is True


# ---- playback ------------------------------------------------------------------------------


def test_play_writes_every_chunk_and_reports_start_then_completion():
    async def run() -> None:
        driver = FakeDriver()
        playback = make_playback(driver)
        started: list[PlaybackOutboundDTO] = []

        result = await playback.play(FORMAT, _audio(b"ab", b"", b"cd"), started.append)

        assert started == [PlaybackOutboundDTO(True, "Playback stream started")]
        assert result == PlaybackOutboundDTO(True, "Playback session finalized successfully")
        assert driver.streams[0].written == [b"ab", b"cd"]
        assert playback.is_playing() is False

    asyncio.run(run())


def test_unsupported_rate_falls_back_to_44100():
    async def run() -> None:
        driver = FakeDriver(unsupported_rates=(24000,))
        result = await make_playback(driver).play(FORMAT, _audio(b"ab"), lambda _: None)

        assert result.success is True
        assert [fmt.sample_rate for _, fmt in driver.opened] == [24000, 44100]

    asyncio.run(run())


def test_fallback_rate_playback_is_resampled_so_the_duration_is_preserved():
    async def run() -> None:
        driver = FakeDriver(unsupported_rates=(24000,))
        one_second = b"\x10\x00" * 24000  # 1 s of 24 kHz mono PCM16

        result = await make_playback(driver).play(
            FORMAT, _audio(one_second[:20000], one_second[20000:]), lambda _: None
        )

        assert result.success is True
        assert driver.opened[-1][1].sample_rate == 44100
        written_frames = sum(len(chunk) for chunk in driver.streams[-1].written) // 2
        assert abs(written_frames - 44100) <= 4  # 1 s at the device rate, not 24000 frames

    asyncio.run(run())


def test_native_rate_playback_is_written_untouched():
    async def run() -> None:
        driver = FakeDriver()
        await make_playback(driver).play(FORMAT, _audio(b"ab", b"cd"), lambda _: None)
        assert driver.streams[0].written == [b"ab", b"cd"]

    asyncio.run(run())


def test_open_failure_is_reported_through_on_started_and_the_result():
    async def run() -> None:
        driver = FakeDriver(unsupported_rates=(24000, 44100))
        started: list[PlaybackOutboundDTO] = []

        result = await make_playback(driver).play(FORMAT, _audio(b"ab"), started.append)

        assert result.success is False
        assert result.message.startswith("Hardware stream open failure")
        assert started == [result]

    asyncio.run(run())


def test_a_failing_input_stream_fails_the_playback():
    async def run() -> None:
        async def broken():
            yield b"ab"
            raise ConnectionError("client vanished")

        result = await make_playback().play(FORMAT, broken(), lambda _: None)

        assert result == PlaybackOutboundDTO(False, "client vanished")

    asyncio.run(run())


def test_close_cancels_the_active_worker_and_releases_the_stream():
    async def run() -> None:
        driver = FakeDriver()
        playback = make_playback(driver)
        cancelled = asyncio.Event()

        async def long_running() -> None:
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        playback._playback_task = asyncio.create_task(long_running())
        playback._is_playing = True
        playback._stream = driver.open_output(1, FORMAT)
        await asyncio.sleep(0)

        await playback.close()

        assert not playback.is_playing()
        assert playback._playback_task is None
        assert cancelled.is_set()
        assert driver.streams[0].closed is True

    asyncio.run(run())


def test_concurrent_plays_are_serialized_by_the_lock():
    async def run() -> None:
        driver = FakeDriver(unsupported_rates=(24000, 44100))
        playback = make_playback(driver)

        results = await asyncio.gather(
            playback.play(FORMAT, _audio(), lambda _: None),
            playback.play(FORMAT, _audio(), lambda _: None),
        )

        assert all(r.success is False for r in results)
        assert len(driver.opened) == 4  # two sessions x (requested + fallback)

    asyncio.run(run())


def test_a_new_play_supersedes_the_running_one():
    async def run() -> None:
        playback = make_playback()
        gate = asyncio.Event()
        first_started = asyncio.Event()

        async def slow():
            yield b"a"
            await gate.wait()
            yield b"b"

        first = asyncio.create_task(playback.play(FORMAT, slow(), lambda _: first_started.set()))
        await first_started.wait()

        second = await playback.play(FORMAT, _audio(b"c"), lambda _: None)
        gate.set()

        assert (await first).message == "Playback session superseded by new request"
        assert second.message == "Playback session finalized successfully"

    asyncio.run(run())


# ---- the end of a playback: a reply longer than the old 3 s limit must be played in full (R-6) -------------


class RealTimeOutput(FakeRawOutput):
    """A device that takes as long to play a chunk as the chunk lasts (24 kHz mono PCM16, 48,000 bytes a second)."""

    def write(self, data: bytes) -> Any:
        time.sleep(len(data) / 48000)
        super().write(data)


class RealTimeDriver(FakeDriver):
    def open_output(self, index: int, audio_format: PlaybackFormat) -> FakeRawOutput:
        self.opened.append((index, audio_format))
        stream = RealTimeOutput()
        self.streams.append(stream)
        return stream


def _half_seconds(count: int) -> list[bytes]:
    """``count`` chunks of 0.5 s of audio: the whole reply is handed over at once, like tts does (faster than real time)."""
    return [b"\x10\x00" * 12000 for _ in range(count)]


def test_a_reply_longer_than_the_old_three_second_limit_is_played_in_full():
    async def run() -> None:
        driver = RealTimeDriver()
        chunks = _half_seconds(7)  # 3.5 s: the old fixed 3 s wait cut this reply off after 3 s

        result = await make_playback(driver).play(FORMAT, _audio(*chunks), lambda _: None)

        assert result == PlaybackOutboundDTO(True, "Playback session finalized successfully")
        assert sum(len(c) for c in driver.streams[0].written) == sum(len(c) for c in chunks)

    asyncio.run(run())


def test_a_device_that_never_finishes_does_not_hold_the_session_forever(monkeypatch):
    class StuckOutput(FakeRawOutput):
        def write(self, data: bytes) -> Any:
            time.sleep(1.2)

    class StuckDriver(FakeDriver):
        def open_output(self, index: int, audio_format: PlaybackFormat) -> FakeRawOutput:
            stream = StuckOutput()
            self.streams.append(stream)
            return stream

    monkeypatch.setattr(playback_module, "_DRAIN_MARGIN_SECONDS", 0.2)

    async def run() -> None:
        started = time.monotonic()
        result = await make_playback(StuckDriver()).play(FORMAT, _audio(*_half_seconds(1)), lambda _: None)

        assert result.success is True  # the existing behaviour: a truncated playback is logged, not failed
        assert time.monotonic() - started < 2.0  # bounded by the audio's own duration (0.5 s) plus the margin

    asyncio.run(run())


@pytest.mark.parametrize(
    ("queued_bytes", "sample_rate", "channels", "seconds"),
    [(0, 24000, 1, 0.0), (48000, 24000, 1, 1.0), (343068, 24000, 1, 343068 / 48000), (176400, 44100, 2, 1.0), (96000, 24000, 2, 1.0)],
)
def test_the_drain_wait_is_the_duration_of_the_queued_audio_plus_a_margin(queued_bytes, sample_rate, channels, seconds):
    timeout = playback_module._drain_timeout_seconds(queued_bytes, PlaybackFormat(sample_rate=sample_rate, channels=channels))

    assert timeout == pytest.approx(seconds + playback_module._DRAIN_MARGIN_SECONDS)


def test_the_margin_is_a_real_allowance_for_the_device_latency():
    assert 1.0 <= playback_module._DRAIN_MARGIN_SECONDS <= 10.0
