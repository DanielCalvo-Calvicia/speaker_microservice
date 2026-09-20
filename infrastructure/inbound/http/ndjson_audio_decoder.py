"""Extracts the audio carried by a request body of Speaker inbound contract events (NDJSON)."""

import base64
import binascii
from collections.abc import Iterator

from contracts.stream.codec import NdjsonDecoder
from contracts.stream.common.base import BaseEvent, ContractViolation, EventType
from contracts.stream.schemas import SPEAKER_INBOUND


class NdjsonInputError(ValueError):
    """A streamed NDJSON playback request violates the input contract."""


class NdjsonAudioDecoder:
    """Stateful decoder of byte chunks into audio.

    The contract rules (sequence 1..n, ``stream_started`` first and only once, well-formed events)
    are enforced by the shared codec; this class only turns events into audio:

    * ``stream_started`` -> must announce the format playback was requested with
    * ``partial``     -> its decoded PCM
    * ``completed``   -> nothing (the end of one spoken text; playback goes on)
    * ``heartbeat`` -> nothing
    * ``error``       -> the sender failed, so playback of this stream fails too
    """

    def __init__(self, sample_rate: int, channels: int) -> None:
        self._decoder = NdjsonDecoder(SPEAKER_INBOUND)
        self._expected = (sample_rate, channels)

    def feed(self, chunk: bytes) -> Iterator[bytes]:
        try:
            for event in self._decoder.feed(chunk):
                yield from self._audio_of(event)
        except ContractViolation as error:
            raise NdjsonInputError(str(error)) from error

    def finish(self) -> Iterator[bytes]:
        try:
            for event in self._decoder.finish():
                yield from self._audio_of(event)
        except ContractViolation as error:
            raise NdjsonInputError(str(error)) from error

    def _audio_of(self, event: BaseEvent) -> Iterator[bytes]:
        if event.type is EventType.START_STREAM:
            announced = (event.payload.sample_rate, event.payload.channels)
            if announced != self._expected:
                raise NdjsonInputError(
                    f"Stream announces {announced[0]} Hz x {announced[1]} channel(s) but playback "
                    f"was requested as {self._expected[0]} Hz x {self._expected[1]} channel(s)."
                )
        elif event.type is EventType.PARTIAL:
            try:
                yield base64.b64decode(event.payload.bytes_base64, validate=True)
            except (binascii.Error, ValueError) as error:
                raise NdjsonInputError(
                    "NDJSON partial event payload.bytes_base64 is not valid base64."
                ) from error
        elif event.type is EventType.ERROR:
            raise NdjsonInputError(
                f"Upstream reported an error: {event.payload.code}: {event.payload.message}"
            )
