# ADR-003 — The playback request and its answer use the `contracts.stream` NDJSON events

**Status:** Accepted (introduced with the contract streams after commit `eacddae`, 2026-09-20; recorded 2026-11-05).
**Related:** [ADR-007](ADR-007-http-statuses-before-the-stream.md)

## Context

Brain streams TTS audio while it is still being produced and needs to know when the device is open and when the speech ended. Hand-written JSON on both sides drifts.

## Decision

`POST /process/stream/set` accepts raw PCM, or `SPEAKER_INBOUND` events when the content type is `application/x-ndjson`, and answers `SPEAKER_OUTBOUND` events (`stream_started`, `completed` or `error`, optional heartbeats). Every event is built and decoded with `contracts.stream` and its codec (`NdjsonDecoder`, `EventSequencer`, `encode_ndjson`); no event JSON is written by hand. A new event goes into `contracts` first, then the producers and the consumers, and `contracts` gets a new version (the speaker carries the wheel in `vendor/`). The answer starts as soon as the device is open and does not wait for the audio. The response class does not read the ASGI receive channel while it writes, because the playback task is reading the request body there (`RequestBodySafeStreamingResponse`).

## Consequences

- Positive: one definition of the wire format for Brain and the speaker; sequence and format errors are caught by the codec.
- Negative: a contract change means a new wheel in every service that bundles it.
