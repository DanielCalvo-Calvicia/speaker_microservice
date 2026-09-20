"""The speaker's two stream directions against the project contracts, built with the codec.

Inbound  : what Brain sends (Speaker inbound contract) must be accepted and played.
Outbound : what the speaker answers must decode with the Speaker outbound contract.
"""

import base64

from contracts.stream.codec import EventSequencer, NdjsonDecoder, encode_ndjson
from contracts.stream.common.base import EventType
from contracts.stream.common.error import ErrorEvent, ErrorEventDTO
from contracts.stream.common.heartbeat import HeartbeatEvent
from contracts.stream.microservices.speaker.inbound.stream_started import (
    SpeakerStreamStartedInboundEvent,
    SpeakerStreamStartedInboundEventDTO,
)
from contracts.stream.microservices.speaker.inbound.completed import (
    SpeakerCompletedInboundEvent,
    SpeakerCompletedInboundEventDTO,
)
from contracts.stream.microservices.speaker.inbound.partial import (
    SpeakerPartialInboundEvent,
    SpeakerPartialInboundEventDTO,
)
from contracts.stream.schemas import SPEAKER_OUTBOUND

from tests.infrastructure.test_http_handler import FakeSpeakerService, build_client, post_ndjson


STARTED = (
    SpeakerStreamStartedInboundEvent,
    SpeakerStreamStartedInboundEventDTO(sample_rate=24000, channels=1),
)


def _partial(audio: bytes) -> tuple:
    return SpeakerPartialInboundEvent, SpeakerPartialInboundEventDTO(
        bytes_base64=base64.b64encode(audio).decode("ascii")
    )


def _body(*items: tuple) -> bytes:
    sequence = EventSequencer()
    return b"".join(encode_ndjson(sequence.next(cls, payload)) for cls, payload in items)


def _outbound(response) -> list:
    return [*NdjsonDecoder(SPEAKER_OUTBOUND).feed(response.content)]


def test_a_brain_stream_is_played_and_answered_with_contract_events():
    service = FakeSpeakerService(message="Playback stream started")
    client = build_client(service)
    body = _body(
        STARTED,
        _partial(b"first"),
        (SpeakerCompletedInboundEvent, SpeakerCompletedInboundEventDTO()),  # one spoken text ends
        _partial(b"second"),
        (SpeakerCompletedInboundEvent, SpeakerCompletedInboundEventDTO()),
    )

    response = post_ndjson(client, body)

    assert service.received_chunks == [b"first", b"second"]
    events = _outbound(response)  # raises ContractViolation if the speaker breaks its contract
    assert [e.type for e in events] == [EventType.START_STREAM, EventType.COMPLETED]
    assert (events[0].payload.sample_rate, events[0].payload.channels) == (24000, 1)
    assert events[1].payload.reason == "end_of_input"
    assert (events[1].payload.chunk_count, events[1].payload.byte_count) == (2, 11)


def test_heartbeats_are_accepted_anywhere_after_stream_started():
    service = FakeSpeakerService()
    body = _body(STARTED, (HeartbeatEvent, None), _partial(b"x"), (HeartbeatEvent, None))

    events = _outbound(post_ndjson(build_client(service), body))

    assert service.received_chunks == [b"x"]
    assert events[-1].type is EventType.COMPLETED


def test_an_upstream_error_event_fails_the_playback_and_is_reported_as_an_error_event():
    service = FakeSpeakerService()
    body = _body(
        STARTED,
        _partial(b"partial-audio"),
        (ErrorEvent, ErrorEventDTO(code="tts_failed", message="engine gone", recoverable=False)),
    )

    events = _outbound(post_ndjson(build_client(service), body))

    assert events[-1].type is EventType.ERROR
    assert "tts_failed: engine gone" in events[-1].payload.message
    assert events[-1].payload.code == "request_stream_failed"


def test_the_response_sequence_is_gap_free_including_heartbeats():
    client = build_client(FakeSpeakerService())

    response = client.post(
        "/process/stream/set?keep_open_after_completed=true&heartbeat_interval_seconds=0.1"
        "&max_heartbeats_after_completed=2",
        content=_body(STARTED, _partial(b"x")),
        headers={"content-type": "application/x-ndjson"},
    )

    events = _outbound(response)  # the decoder validates 1..n
    assert [e.type for e in events] == [
        EventType.START_STREAM,
        EventType.COMPLETED,
        EventType.HEARTBEAT,
        EventType.HEARTBEAT,
    ]
