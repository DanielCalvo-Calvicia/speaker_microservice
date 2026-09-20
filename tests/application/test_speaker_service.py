import asyncio
from collections.abc import AsyncIterator, Callable

from application.dtos.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.playback_outbound import PlaybackOutboundDTO
from application.dtos.readiness_outbound import ReadinessOutboundDTO
from application.ports.outbound.audio_playback_port import AudioPlaybackPort
from application.services.speaker_service import SpeakerService
from domain.value_objects.playback_format import PlaybackFormat


class FakePlayback(AudioPlaybackPort):
    def __init__(self) -> None:
        self.played: list[PlaybackFormat] = []
        self.closed = 0
        self.playing = False

    async def play(
        self,
        audio_format: PlaybackFormat,
        audio_stream: AsyncIterator[bytes],
        on_started: Callable[[PlaybackOutboundDTO], None],
    ) -> PlaybackOutboundDTO:
        self.played.append(audio_format)
        on_started(PlaybackOutboundDTO(True, "started"))
        return PlaybackOutboundDTO(True, "done")

    async def close(self) -> None:
        self.closed += 1

    async def check_readiness(self) -> ReadinessOutboundDTO:
        return ReadinessOutboundDTO(is_ready=True)

    def is_playing(self) -> bool:
        return self.playing


async def _no_audio() -> AsyncIterator[bytes]:
    return
    yield b""


def _request(sample_rate: int = 24000, channels: int = 1, future=None) -> PlayStreamInboundDTO:
    return PlayStreamInboundDTO(
        audio_stream=_no_audio(), sample_rate=sample_rate, channels=channels, setup_future=future
    )


def test_play_forwards_the_validated_format_and_returns_the_device_result():
    async def run() -> None:
        playback = FakePlayback()
        future = asyncio.get_running_loop().create_future()

        result = await SpeakerService(playback).play(_request(future=future))

        assert result == PlaybackOutboundDTO(True, "done")
        assert playback.played == [PlaybackFormat(24000, 1)]
        assert future.result() == PlaybackOutboundDTO(True, "started")

    asyncio.run(run())


def test_invalid_sample_rate_is_rejected_and_acknowledged_without_touching_the_device():
    async def run() -> None:
        playback = FakePlayback()
        future = asyncio.get_running_loop().create_future()

        result = await SpeakerService(playback).play(_request(sample_rate=0, future=future))

        assert result == PlaybackOutboundDTO(False, "Invalid sample rate. Must be positive.")
        assert future.result() == result
        assert playback.played == []

    asyncio.run(run())


def test_invalid_channel_count_is_rejected():
    async def run() -> None:
        playback = FakePlayback()

        result = await SpeakerService(playback).play(_request(channels=0))

        assert result == PlaybackOutboundDTO(False, "Invalid channel count. Must be positive.")
        assert playback.played == []

    asyncio.run(run())


def test_stop_playback_closes_the_device():
    async def run() -> None:
        playback = FakePlayback()
        await SpeakerService(playback).stop_playback()
        assert playback.closed == 1

    asyncio.run(run())


def test_readiness_and_availability_come_from_the_device():
    async def run() -> None:
        playback = FakePlayback()
        service = SpeakerService(playback)

        assert (await service.check_readiness()).is_ready is True
        assert service.is_available() is False
        playback.playing = True
        assert service.is_available() is True

    asyncio.run(run())


def test_acknowledging_twice_or_without_a_future_is_harmless():
    async def run() -> None:
        request = _request(future=asyncio.get_running_loop().create_future())
        request.acknowledge_setup(PlaybackOutboundDTO(True, "first"))
        request.acknowledge_setup(PlaybackOutboundDTO(False, "second"))
        assert request.setup_future is not None and request.setup_future.result().message == "first"
        _request().acknowledge_setup(PlaybackOutboundDTO(True, "nobody listening"))

    asyncio.run(run())
