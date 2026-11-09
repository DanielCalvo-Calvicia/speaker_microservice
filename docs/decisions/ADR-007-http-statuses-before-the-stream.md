# ADR-007 — Natural HTTP statuses before the stream starts; `error` events after

**Status:** Accepted (after commit `eacddae`, 2026-09-20; recorded 2026-11-05).
**Related:** [ADR-003](ADR-003-stream-contract-ndjson.md)

## Context

Once the NDJSON answer starts the status line is `200` and cannot change, but a failure can happen before (a bad format, no device) or after (a broken body, a device error).

## Decision

Before the stream: `422` for a non-positive `sample_rate` or `channels`, `503` when the output device cannot be opened, `500` for anything else (`http_error_mapper.map_error`, the handler). The answer starts only after the device is acknowledged, so these statuses are possible. After it starts, a failure is an `error` event (`request_stream_failed`, `playback_failed`, `stream_failed`) and no `completed` follows.

## Consequences

- Positive: Brain can tell "the speaker cannot play" (`503`) from "the speech failed halfway" (an event).
- Negative: a device that fails after opening is reported only in the stream.
