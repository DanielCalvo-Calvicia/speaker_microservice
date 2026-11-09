# Requirements

Status as of 2026-11-05. **Done** means implemented and covered by the tests in the repository (92 tests, all with a fake audio driver; the fix of R-6 was also run once on a real device on 2026-11-09, outside the test suite); **Needs hardware** means the behaviour depends on a real output device and was not run in the last pass; **Proposed** means suggested in the deployment audit and not decided or built.

Sources: the role of the service in `../CLAUDE.md` and `README.md`; the contracts `contracts.stream` (`SPEAKER_INBOUND`, `SPEAKER_OUTBOUND`) and `contracts.api`; the deployment audit [`docs/deployment_audit/speaker.md`](../deployment_audit/speaker.md) (2026-11-04); the decisions in [`docs/decisions/`](../decisions/README.md).

## Functional

| ID | Requirement | Status | Record |
|---|---|---|---|
| FR-1 | Play raw signed 16-bit PCM audio, streamed by a client, on the local output device (`sounddevice` / PortAudio) | Done (fake driver); Needs hardware | ADR-001 |
| FR-2 | `POST /process/stream/set?sample_rate=24000&channels=1`: the body is raw PCM, or `SPEAKER_INBOUND` NDJSON events when the content type is `application/x-ndjson`; both formats are played while they arrive | Done | ADR-003 |
| FR-3 | A NDJSON body is decoded with the shared codec of `contracts.stream`: `stream_started` must announce the requested format, `partial` carries strictly validated base64 PCM, `completed` and `heartbeat` are ignored, `error` fails the playback | Done | ADR-003 |
| FR-4 | The answer is an NDJSON stream of `SPEAKER_OUTBOUND` events: `stream_started` once the device is open, then `completed` (`end_of_input`, chunk and byte counts) or `error` (`request_stream_failed`, `playback_failed`, `stream_failed`); the answer does not wait for the audio to finish | Done | ADR-003 |
| FR-5 | Optional heartbeats after `completed` (`keep_open_after_completed`, `heartbeat_interval_seconds`, `max_heartbeats_after_completed`) | Done | |
| FR-6 | Failures before the stream starts have natural statuses: `422` non-positive format, `503` device cannot be opened, `500` anything else; a failure after the stream starts is an `error` event | Done | ADR-007 |
| FR-7 | One playback at a time: a new request supersedes the running one, which ends with `completed` and the superseded message | Done | ADR-008 |
| FR-8 | The audio is played at the rate it was sent. Only if the device refuses that rate is it reopened at 44.1 kHz and the audio resampled (linear interpolation) so the pitch and speed stay right | Done; Needs hardware | ADR-006 |
| FR-9 | Output device: `SPEAKER_DEVICE_INDEX`, else the first device whose name matches `SPEAKER_DEVICE_KEYWORDS`, else the OS default output | Done; Needs hardware | |
| FR-10 | `GET /health`, `GET /ready` and `GET /available` in the common envelope; `/ready` and `/available` probe the device without opening a stream | Done | |
| FR-11 | On SIGINT or SIGTERM the playback stops and the device is released | Done (by code and tests); Docker path unproven | |
| FR-12 | Configuration only through environment variables (and `.env`), documented in `.env.example` | Done | |
| FR-13 | Logging through `shared_logging` with trace continuation (`traceparent`, `x-trace-id`) | Done | ADR-010 |
| FR-14 | CORS from `ALLOWED_ORIGINS` | Done | |
| FR-15 | A `null` sink backend (`SPEAKER_BACKEND=real\|null`) behind `AudioPlaybackPort`, chosen before `sounddevice` is imported, that drains the stream and paces itself to real time, so a machine without a sound card or PortAudio can run the service | **Proposed** (audit, 2026-11-04) | R-1, R-2 |
| FR-16 | `/available` reports which backend is active (a `backend` field in `AvailabilityResponse`, which means a new `contracts` version) | **Proposed** | R-4 |
| FR-17 | Device selection in the per-machine hardware configuration of the deploy tool (keywords per machine, index when known) | **Proposed** | R-3 |
| FR-18 | A reply is played in full: after the body ends the service waits for the device up to the duration of the queued audio plus 2 s (`_DRAIN_MARGIN_SECONDS`), not a fixed 3 s | Done (2026-11-09): a fake real-time device, and a real device (a 7.12 s reply written in full) | R-6, `test_a_reply_longer_than_the_old_three_second_limit_is_played_in_full` |

## Non-functional

| ID | Requirement | Status | Record |
|---|---|---|---|
| NFR-1 | Brain is the only caller; this service calls nobody | Done (it has no outbound HTTP) | ADR-002 |
| NFR-2 | Layered structure `main.py` → `main_flow/` → `composition_root/` → `application/` → `domain/` → `infrastructure/`, dependencies pointing inward, enforced by `tests/architecture/test_dependency_rules.py` | Done | ADR-001 |
| NFR-3 | Audio is PCM16 mono or interleaved in `bytes_base64` / raw bytes and is never converted between services | Done | ADR-006 |
| NFR-4 | Blocking driver calls (open the device, probe, write) never block the event loop (`asyncio.to_thread`) | Done | |
| NFR-5 | Every endpoint but the playback answer uses the envelope `action / status / status_code / message / timestamp / data` | Done | |
| NFR-6 | No authentication in this service; a common scheme for all services comes later | Known gap | ADR-004 |
| NFR-7 | The logs hold counts, never audio | Done | |
| NFR-8 | No secret in the repository, the documents or the tests | Done | |
| NFR-9 | The service builds on its own: `contracts` is vendored (`vendor/`), `shared-logging` is a sibling checkout | Done | |
| NFR-10 | Tests do not need hardware; the end-to-end script `tests/simple.py` does | Done (92 pass); `simple.py` not run | |
