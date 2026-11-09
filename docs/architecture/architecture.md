# Architecture

Reviewed against the code on 2026-11-05 (branch `feature_ai_claude_2`). Sections marked **(exists)** were verified in the repository; **(proposed)** comes from the deployment audit and is not decided or built. It supersedes the documents in `docs/old/`.

## 1. Purpose and responsibility (exists)

The speaker plays PCM16 audio on the local output device. Brain streams the TTS audio to `POST /process/stream/set`; the speaker plays it while it arrives and answers a `contracts.stream` NDJSON event stream (`stream_started`, then `completed` or `error`). It also answers `/health`, `/ready` and `/available`. Only Brain calls it and it calls nobody ([ADR-002](../decisions/ADR-002-brain-is-the-only-caller.md)). It has no authentication ([ADR-004](../decisions/ADR-004-no-authentication-common-middleware-later.md)).

## 2. Layers and dependency rule (exists)

```
composition_root  ──▶  infrastructure  ──▶  application  ──▶  domain
 (chooses concretes)    inbound/outbound     ports+services    value objects, operations
```

Source-code dependencies point inward only. Runtime calls go outward (HTTP → service → hardware) through ports owned by `application`.

```
SpeakerHandler ──▶ SpeakerPlaybackPort ◀── SpeakerService ──▶ AudioPlaybackPort ◀── SoundDeviceAudioPlayback ──▶ AudioDriver ──▶ sounddevice
(inbound)          (driving port)          (application)       (driven port)          (outbound)                 (protocol)
                                                │
                                                ▼
                                   domain: PlaybackFormat, format_negotiation, LinearResampler
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

The reasons are in [ADR-001](../decisions/ADR-001-layered-architecture.md).

## 3. Current layout (exists)

```
main.py                           calls main_flow.http.run_http()
main_flow/
  http.py                         .env -> config -> init_logging -> container -> uvicorn -> cleanup (stop playback)
domain/
  errors.py                       DomainError, InvalidPlaybackFormat
  value_objects/playback_format.py PlaybackFormat(sample_rate, channels) — all fields > 0
  operations/format_negotiation.py fallback_formats(requested): requested, then 44.1 kHz
  operations/resample.py          LinearResampler: PCM16 rate conversion, used only when the device rate differs from the stream's
application/
  errors.py                       ApplicationError, SpeakerUnavailable
  dtos/play_stream_inbound.py     PlayStreamInboundDTO (audio stream, format, optional setup future)
  dtos/playback_outbound.py       PlaybackOutboundDTO(success, message)
  dtos/readiness_outbound.py      ReadinessOutboundDTO(is_ready, message)
  ports/inbound/speaker_playback_port.py   SpeakerPlaybackPort (driving): play, stop_playback, check_readiness, is_available
  ports/outbound/audio_playback_port.py    AudioPlaybackPort (driven): play, close, check_readiness, is_playing
  services/speaker_service.py     SpeakerService — validates the format, delegates, no rules of its own
infrastructure/
  config/                         ServerConfig, SpeakerConfig (env -> frozen dataclasses)
  inbound/http/                   http_handler.py (SpeakerHandler: the four routes), http_envelope.py,
                                  http_error_mapper.py, request_audio_reader.py, ndjson_audio_decoder.py,
                                  ndjson_events.py, request_body_safe_streaming_response.py
  outbound/sounddevice_playback/  audio_driver.py (protocol), sounddevice_driver.py (the only importer of sounddevice),
                                  sounddevice_device_selector.py, sounddevice_audio_playback.py
composition_root/
  dependencies/speaker_dependencies.py   new_audio_playback / new_speaker_service /
                                         new_http_app (CORS, tracing middleware; the lifespan releases the speaker on shutdown)
  containers/http_container.py           HttpContainer, new_http_container
vendor/contracts_microservice-0.15.0-py3-none-any.whl   the bundled contracts
tests/  domain/ application/ infrastructure/ composition_root/ architecture/   (pytest, 92 tests)   +   simple.py (e2e, needs a device)
```

## 4. Flow of a playback (exists)

1. `SpeakerHandler.handle_set_stream` refuses a non-positive `sample_rate` or `channels` (`422`), builds a `RequestAudioReader` (raw PCM, or the NDJSON decoder when the content type is `application/x-ndjson`) and starts the play task with a setup future.
2. `SpeakerService.play` builds the `PlaybackFormat` and calls `AudioPlaybackPort.play`.
3. `SoundDeviceAudioPlayback.play` (under a lock) cleans up a running session, opens the device in a thread at the first format `fallback_formats` yields (the requested one, then 44.1 kHz) and, if the rate differs, creates the `LinearResampler`. It acknowledges the setup; on a failure it acknowledges the failure and the handler answers `503`.
4. The handler answers `200` NDJSON and yields `stream_started`. The request body is consumed outside the lock into an unbounded queue; a worker writes the queue to the device in a thread.
5. When the body ends the service puts a stop sentinel and waits for the queue to be played, at most the duration of the queued audio plus 2 s (R-6: it was a fixed 3 s until 2026-11-09 and cut replies longer than about 3 s). Then the handler yields `completed` (`end_of_input`, counts), or `error` (`request_stream_failed`, `playback_failed`, `stream_failed`), then optional heartbeats.
6. Shutdown: uvicorn returns, the lifespan and `_cleanup` call `stop_playback` → `close()`: the worker is cancelled, the stream stopped and closed.

State: one stream, one worker task, an `is_playing` flag and a session token in `SoundDeviceAudioPlayback`; a new session supersedes the running one ([ADR-008](../decisions/ADR-008-new-playback-supersedes-the-running-one.md)). There is no storage.

## 5. Decisions

The decisions that shape the service are [ADR-001 to ADR-011](../decisions/README.md): the layout, Brain as only caller, the NDJSON stream contract, no authentication, the removed autoloader, audio never converted (resample only on a rejected rate), the HTTP statuses, supersession, device selection, shared logging and configuration, and the Windows decision.

## 6. History of the layout

* `application/dtos/mapper/` is gone: the request/response DTO triples were field-for-field copies. There is one inbound DTO and small outbound result DTOs.
* The NDJSON protocol moved from `application/events/schema.py` to `infrastructure/inbound/http`: it is transport.
* `runtime/` (custom logger, VS Code launch-profile parsing) was replaced by `shared_logging`; `APP_ENV` is no longer read.
* The 540-line `fastapi_adapter.py` was split into handler, request reader, NDJSON decoder, NDJSON encoder and response class.
* Authentication was removed (commit `eacddae`, 2026-09-20), and so was the autoloader (code in `docs/old/autoloader/`).
* Contract streams, natural HTTP statuses and the device-rate resampling were added after the first refactor; `/available` probes the device and no longer reports "a playback is active".
* A bug of the move: a playback that ran to completion reported `Playback session superseded by new request` because the session id was reset before it was compared. It now reports `Playback session finalized successfully`.
* The contracts wheel was refreshed up to 0.15.0 (`vendor/`).

## 7. Proposed (not built)

From the deployment audit of 2026-11-04: a `null` backend (`SPEAKER_BACKEND=real|null`) behind `AudioPlaybackPort`, chosen in the composition root before `sounddevice` is imported, that drains the stream and paces itself to real time; a `backend` field in `AvailabilityResponse`; device selection in the per-machine deploy configuration (FR-15 to FR-17). The known debt is in [risks-and-debt](../risks/risks-and-debt.md).
