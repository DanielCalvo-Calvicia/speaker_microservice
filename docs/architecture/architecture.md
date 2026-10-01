# Architecture

Speaker Microservice follows the same Clean Architecture layout as `microphone_microservice`.
It supersedes the docs in `docs/old/`. Reviewed against the code on 2026-10-01 (branch `feature_ai_claude_2`).

## Layers and dependency rule

```
composition_root  ──▶  infrastructure  ──▶  application  ──▶  domain
 (chooses concretes)    inbound/outbound     ports+services    value objects, operations
```

Source-code dependencies point inward only. Runtime calls go outward (HTTP → service → hardware)
through ports owned by `application`.

```
SpeakerHandler ──▶ SpeakerPlaybackPort ◀── SpeakerService ──▶ AudioPlaybackPort ◀── SoundDeviceAudioPlayback ──▶ sounddevice
(inbound)          (driving port)          (application)       (driven port)          (outbound)
                                                │
                                                ▼
                                   domain: PlaybackFormat, format_negotiation
```

`tests/architecture/test_dependency_rules.py` enforces this by parsing imports:

| Layer | May import | Must not import |
|---|---|---|
| `domain` | stdlib, `domain` | everything else |
| `application` | stdlib, `domain`, `application` | `infrastructure`, `composition_root`, fastapi/starlette/pydantic/uvicorn/sounddevice/numpy/httpx/dotenv |
| `infrastructure/inbound` | application, domain, frameworks | `infrastructure.outbound`, `composition_root` |
| `infrastructure/outbound` | application, domain, frameworks | `infrastructure.inbound`, `composition_root` |
| `composition_root` | everything | — |
| `main_flow` | `composition_root`, `infrastructure.config` | `infrastructure.inbound`, `infrastructure.outbound` |

## Layout

```
main.py                           calls main_flow.http.run_http()
main_flow/
  http.py                         .env -> config -> container -> uvicorn -> shutdown cleanup
domain/
  errors.py                       DomainError, InvalidPlaybackFormat
  value_objects/playback_format.py PlaybackFormat(sample_rate, channels) — all fields > 0
  operations/format_negotiation.py fallback_formats(requested): requested, then 44.1 kHz
  operations/resample.py          LinearResampler: PCM16 rate conversion, used only when the device rate differs from the stream's
application/
  errors.py                       ApplicationError, SpeakerUnavailable
  dtos/play_stream_inbound.py     PlayStreamInboundDTO (audio stream + optional setup future)
  dtos/playback_outbound.py       PlaybackOutboundDTO(success, message)
  dtos/readiness_outbound.py      ReadinessOutboundDTO(is_ready, message)
  ports/inbound/speaker_playback_port.py   SpeakerPlaybackPort (driving)
  ports/outbound/audio_playback_port.py    AudioPlaybackPort (driven)
  services/speaker_service.py     SpeakerService — validates the format, delegates, no rules of its own
infrastructure/
  config/                         ServerConfig, SpeakerConfig (env -> frozen dataclasses)
  inbound/http/                   http_handler.py (SpeakerHandler), http_envelope.py,
                                  http_error_mapper.py, request_audio_reader.py, ndjson_audio_decoder.py,
                                  ndjson_events.py, request_body_safe_streaming_response.py
  outbound/sounddevice_playback/  audio_driver.py (protocol), sounddevice_driver.py,
                                  sounddevice_device_selector.py, sounddevice_audio_playback.py
composition_root/
  dependencies/speaker_dependencies.py   new_audio_playback / new_speaker_service /
                                         new_http_app (CORS, tracing middleware; lifespan releases the speaker on shutdown)
  containers/http_container.py           HttpContainer, new_http_container
tests/  domain/ application/ infrastructure/ composition_root/ architecture/   (pytest)   +   simple.py (e2e)
```

## What changed from the previous layout

* `application/dtos/mapper/` is gone: the request/response DTO triples (inbound, service, outbound)
  were field-for-field copies. There is now one inbound DTO and small outbound result DTOs.
* `application/events/schema.py` (the NDJSON protocol) moved to `infrastructure/inbound/http`: it is
  transport, not an application concern.
* `runtime/` (custom logger with per-environment levels, VS Code launch-profile parsing) is replaced
  by the shared `shared_logging` package (`init_logging("speaker")` in `main_flow/http.py`); `LOG_LEVEL` decides. `APP_ENV` is no longer read.
* The 540-line `fastapi_adapter.py` is split into handler, request reader, NDJSON decoder,
  NDJSON encoder and response class. It no longer doubles as an inbound port.
* **Authentication was removed (commit `eacddae`, 2026-09-20).** The bearer-token check (`SPEAKER_API_KEY`, `http_auth.py`, `ApiKeyAuthenticator`) described in the first refactor no longer exists; no service has auth and a common scheme is not designed.
* `sounddevice` sits behind an `AudioDriver` protocol (`sounddevice_driver.py` is the only module that
  imports it) plus a `DeviceSelector`, so the adapter is tested against a fake driver.
* Blocking driver calls (open the device, probe readiness) run via `asyncio.to_thread`.

## Bug fixed during the move

A playback that ran to completion reported `"Playback session superseded by new request"` (in the
`completed` event's `message`) because the session id was reset before it was compared. It now reports
`"Playback session finalized successfully"`; `superseded` is captured before the reset.

## Changes since the first refactor (commit `eacddae`)

* **Contract streams.** `POST /process/stream/set` accepts `SPEAKER_INBOUND` events (or raw PCM) and answers with `SPEAKER_OUTBOUND` events (`stream_started`, `completed`/`error`, optional heartbeats).
* **Natural HTTP statuses** (`http_error_mapper.py`): 422 invalid playback format, 503 output device unavailable, else 500.
* **Device-rate resampling.** If the device rejects the requested rate it is reopened at 44.1 kHz and the audio is resampled to it (`LinearResampler`), instead of being written at the wrong speed.
* `/available` probes the device (same check as `/ready`); it no longer reports "a playback is active".
* The autoloader (the speaker pulling a stream by itself) was removed; its old code is archived in `docs/old/autoloader/`.

## Known remaining debt

1. (Resolved) Errors map to 422/503 before the stream starts; a failure after it starts is an `error` event.
2. (Resolved) `tests/simple.py` now drives `/process/stream/set` with Speaker inbound events. It still needs a real output device and was not run in the 2026-10-01 documentation pass.
3. There is no authentication and no service-to-service auth design.
