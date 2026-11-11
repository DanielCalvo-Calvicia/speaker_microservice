"""The NDJSON events the speaker answers ``POST /process/stream/set`` with (Speaker outbound contract)."""

from contracts.stream.codec import EventSequencer, encode_ndjson
from contracts.stream.common.error import ErrorEvent, ErrorEventDTO
from contracts.stream.common.heartbeat import HeartbeatEvent
from contracts.stream.microservices.speaker.outbound.completed import (
    SpeakerCompletedOutboundEvent,
    SpeakerCompletedOutboundEventDTO,
)
from contracts.stream.microservices.speaker.outbound.stream_started import (
    SpeakerStreamStartedEvent,
    SpeakerStreamStartedEventDTO,
)


class NdjsonEventStream:
    """Builds the response events of one playback with stream-local sequencing (1, 2, 3...)."""

    def __init__(self) -> None:
        self._events = EventSequencer()

    def stream_started(self, message: str, sample_rate: int, channels: int) -> str:
        return self._line(
            SpeakerStreamStartedEvent,
            SpeakerStreamStartedEventDTO(message=message, sample_rate=sample_rate, channels=channels),
        )

    def completed(
        self, *, reason: str, chunk_count: int, byte_count: int, message: str, output: str = ""
    ) -> str:
        return self._line(
            SpeakerCompletedOutboundEvent,
            SpeakerCompletedOutboundEventDTO(
                reason=reason,
                output=output,
                chunk_count=chunk_count,
                byte_count=byte_count,
                message=message,
            ),
        )

    def error(self, code: str, message: str, *, recoverable: bool = True) -> str:
        return self._line(ErrorEvent, ErrorEventDTO(code=code, message=message, recoverable=recoverable))

    def heartbeat(self) -> str:
        return self._line(HeartbeatEvent, None)

    def _line(self, event_cls, payload) -> str:  # noqa: ANN001
        return encode_ndjson(self._events.next(event_cls, payload)).decode("utf-8")
