# HTTP API of the service

What `python main.py` answers today. Everything here was checked against the code (`infrastructure/inbound/http/`, `application/`, `infrastructure/outbound/sounddevice_playback/`) and the tests; whatever is not built is marked **Proposed**. Only Brain calls this service. There is **no authentication** (see [security](../security/security.md)).

The service has four routes and nothing else. CORS is on (`ALLOWED_ORIGINS`, default `*`).

## Routes

| Method and path | Purpose | State |
|---|---|---|
| `POST /process/stream/set` | Play a streamed PCM16 audio request on the output device; answers an NDJSON event stream | Built |
| `GET /health` | Liveness: `200` whenever the process answers; touches no device | Built |
| `GET /ready` | `200` with `is_ready` true when the selected device has output channels, false otherwise (a probe, no stream is opened) | Built |
| `GET /available` | Same probe as `/ready`, answered as `AvailabilityResponse`; it does **not** mean "a playback is running" | Built |

Another method on a known path answers `405`; an unknown path `404` (FastAPI defaults). The interactive documentation of FastAPI (`/docs`, `/openapi.json`) is on, because the service does not turn it off.

## Probes: the envelope

`/health`, `/ready` and `/available` answer `200` with the common envelope `contracts.api.common.envelope.ApiEnvelope` (`action`, `status`, `status_code`, `message`, `timestamp`, `data`):

| Route | `action` | `data` |
|---|---|---|
| `/health` | `health_check` | `{"healthy": true}` |
| `/ready` | `check_readiness` | `{"is_ready": bool, "pending_reason": str or null}` |
| `/available` | `check_availability` | `{"is_available": bool, "reason": str or null}` |

`/ready` and `/available` are always `200`: a device that cannot be used is `is_ready` / `is_available` false with the reason (`Selected device has no output channels.` or the error of the driver), not a `5xx`. The reason is `null` when the device is usable. The probes run the driver call in a thread (`asyncio.to_thread`).

An unreachable output device at **start-up** is different: the process does not start at all (see [risks](../risks/risks-and-debt.md), R-1), so these routes never answer in that case.

## Playback request: `POST /process/stream/set`

Brain streams the audio it got from TTS. The body is read while it is played: the request may last as long as the speech.

| Query parameter | Default | Meaning |
|---|---|---|
| `sample_rate` | `24000` | Sample rate of the audio, in Hz. Must be positive |
| `channels` | `1` | Number of channels. Must be positive |
| `keep_open_after_completed` | `false` | When `true`, `heartbeat` events follow `completed` until the client closes the response |
| `heartbeat_interval_seconds` | `15` | Seconds between heartbeats (never less than 0.1) |
| `max_heartbeats_after_completed` | none (unlimited) | Stop after this many heartbeats |

### Request body

The `Content-Type` decides how the body is read:

| `Content-Type` | Body |
|---|---|
| contains `application/x-ndjson` | `contracts.stream` events (`SPEAKER_INBOUND`), one JSON object per line, decoded with the shared codec |
| anything else | raw PCM: signed 16-bit little-endian, interleaved, in the format of the query |

Audio is **never converted between services**: the format is the one the request names.

`SPEAKER_INBOUND` events (sequence numbers `1..n`, `stream_started` first and only once; the codec of `contracts.stream` enforces the rules):

| Event | Effect |
|---|---|
| `stream_started` | Must announce the same `sample_rate` and `channels` as the query, or the stream fails |
| `partial` | `payload.bytes_base64`: PCM16 audio, decoded strictly (invalid base64 fails the stream) and played |
| `completed` | End of one spoken text; nothing is done, playback goes on |
| `heartbeat` | Ignored |
| `error` | The sender failed, so this playback fails too (`error` event with `request_stream_failed`) |

The audio of a request ends when the body ends (or the client disconnects, which finishes the playback normally).

### Answer

Before the stream starts, a plain `application/json` answer:

| Status | When | Body |
|---|---|---|
| `422` | `sample_rate` or `channels` is not positive | envelope with `action: set_stream_http` |
| `503` | The output device could not be opened (`Hardware stream open failure: ...`) | envelope with the reason |
| `500` | Any other failure before the stream; an unhandled exception answers `{"message": "An internal error occurred"}` | envelope or that message |

Once the device is open the answer is `200`, `Content-Type: application/x-ndjson`, `Cache-Control: no-cache`, `X-Content-Type-Options: nosniff`, with `SPEAKER_OUTBOUND` events (numbered `1, 2, 3...` per response). The answer starts as soon as the device is ready; it does not wait for the audio.

| Event | When | Payload |
|---|---|---|
| `stream_started` | First, once the device is open | `message` (`Playback stream started`), `sample_rate`, `channels` (the **requested** ones) |
| `completed` | The audio ended and the playback was finalised | `reason: end_of_input`, `chunk_count`, `byte_count` (what was read from the request), `message`, `output` (empty) |
| `error` | The playback failed after it started | `code`, `message`, `recoverable: true` |
| `heartbeat` | Only with `keep_open_after_completed=true`, after `completed` | none |

`error` codes: `request_stream_failed` (the body could not be read or decoded: invalid NDJSON, a violation of the contract, a wrong announced format, an `error` event from the sender), `playback_failed` (the device failed while playing), `stream_failed` (anything else while the response was produced). After an `error` no `completed` follows.

The `message` of `completed` is `Playback session finalized successfully`, or `Playback session superseded by new request` when another request took the device (see below).

### Behaviour worth knowing

- **A new request supersedes a running one.** The running playback stops consuming its audio and finishes with `completed` and the superseded message; the new one opens the device. There is one device and one playback at a time.
- **Device rate.** If the device refuses the requested rate, it is reopened at 44.1 kHz and the audio is resampled to that rate (linear interpolation, `domain/operations/resample.py`); a warning is logged. The events still announce the requested rate.
- **End of the audio.** After the body ends the service waits at most 3 seconds for the queued audio to be written; what is still queued after that is dropped (`Playback queue cleanup timed out; truncating` in the log). See [risks](../risks/risks-and-debt.md), R-6.
- **Shutdown.** The playback is stopped and the device released on SIGINT or SIGTERM.
