# Architecture

Reviewed against the code on 2026-11-11 (branch `feature_ai_claude_2`). Sections marked **(exists)** were verified in the repository; **(proposed)** comes from the deployment audit and is not decided or built. It supersedes the documents in `docs/old/`.

## 1. Purpose and responsibility (exists)

The speaker plays PCM16 audio on the local output device. Brain streams the TTS audio to `POST /process/stream/set`; the speaker plays it while it arrives and answers a `contracts.stream` NDJSON event stream (`stream_started`, then `completed` or `error`). It also answers `/health`, `/ready` and `/available`. Only Brain calls it and it calls nobody ([ADR-002](../decisions/ADR-002-brain-is-the-only-caller.md)). It has no authentication ([ADR-004](../decisions/ADR-004-no-authentication-common-middleware-later.md)).

## 2. Layers and dependency rule (exists)

```
composition_root  ──▶  infrastructure  ──▶  application  ──▶  domain
 (chooses concretes)    inbound/outbound     ports+services    value objects, operations
```

Source-code dependencies point inward only. Runtime calls go outward (HTTP → service → hardware) through ports owned by `application`. There are three ports, one for each kind of component, and each lives in its own folder of `application/ports/` (the same split as `stt_microservice`):

```
SpeakerHandler ─implements▶ SpeakerInboundPort     (inbound adapter port: the operations every inbound adapter offers)
SpeakerHandler ─calls─────▶ SpeakerServicePort ◀─implements─ SpeakerService     (the service's own port: the use cases)
SpeakerService ─calls─────▶ SpeakerOutboundPort ◀─implements─ SoundDeviceAudioPlayback, NullAudioPlayback
                            (outbound adapter port: what the service needs from an output device)
                                  │                                   SoundDeviceAudioPlayback ──▶ AudioDriver ──▶ sounddevice
                                  ▼
                     domain: PlaybackFormat, format_negotiation, LinearResampler
```

A new inbound adapter (gRPC, a CLI...) implements `SpeakerInboundPort` and a new playback backend implements `SpeakerOutboundPort`, so each has the same functions as the ones already there. `SpeakerInboundPort` has `health`, `check_readiness` and `play` (DTOs, no transport types); `SpeakerHandler` implements them by calling the service, and its routes decode the HTTP request into those calls. (Before 2026-11-11 the service port was called `SpeakerPlaybackPort`, the outbound port `AudioPlaybackPort`, and there was no inbound port.)

`tests/architecture/test_dependency_rules.py` enforces this by parsing imports:

| Layer | May import | Must not import |
|---|---|---|
| `domain` | stdlib, `domain` | everything else |
| `application` | stdlib, `domain`, `application` | `infrastructure`, `composition_root`, fastapi/starlette/pydantic/uvicorn/sounddevice/numpy/httpx/dotenv |
| `infrastructure/inbound` | application, domain, frameworks | `infrastructure.outbound`, `composition_root` |
| `infrastructure/outbound` | application, domain, frameworks | `infrastructure.inbound`, `composition_root` |
| `composition_root` | everything | — |
| `main_flow` | `composition_root`, `infrastructure.config` | `infrastructure.inbound`, `infrastructure.outbound` |

Two more rules of the same test: no `print()` outside `infrastructure`, and no module or folder named `utils`, `common` or `helpers`, except `infrastructure/inbound/http/helpers/`. `tests/architecture/test_dtos.py` keeps the DTOs apart: every one lives in `application/dtos/inbound` (what an inbound adapter hands to the application) or `application/dtos/outbound` (what the application hands back), and the folder, the file suffix and the class suffix agree. `tests/architecture/test_ports.py` checks the ports: the service, the HTTP handler and both playback backends implement theirs, each port declares exactly the operations listed here, and any class named `*Handler` under `infrastructure/inbound` or `*AudioPlayback` under `infrastructure/outbound` must implement its port.

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
  dtos/inbound/play_stream_inbound.py     PlayStreamInboundDTO (audio stream, format, optional setup future)
  dtos/outbound/playback_outbound.py      PlaybackOutboundDTO(success, message)
  dtos/outbound/readiness_outbound.py     ReadinessOutboundDTO(is_ready, message)
  ports/service/speaker_service_port.py   SpeakerServicePort: the service's own port (SpeakerService implements it): play, stop_playback, check_readiness, is_available
  ports/inbound/speaker_inbound_port.py   SpeakerInboundPort: what every inbound adapter offers (SpeakerHandler implements it): health, check_readiness, play
  ports/outbound/speaker_outbound_port.py SpeakerOutboundPort: what every output backend offers (both backends implement it): play, close, check_readiness, is_playing
  services/speaker_service.py     SpeakerService — validates the format, delegates, no rules of its own
infrastructure/
  config/                         ServerConfig, SpeakerConfig (env -> frozen dataclasses)
  inbound/http/http_handler.py    SpeakerHandler(SpeakerInboundPort): declares the four endpoints and wires each to its route; no request logic
  inbound/http/routes/            one file per endpoint, a function taking the inbound port: health, ready, available, set_stream
  inbound/http/response/          http_envelope.py (success / failure -> ApiEnvelope), stream_events.py (NdjsonEventStream: the SPEAKER_OUTBOUND events),
                                  playback_stream_response.py (the events of one playback, cancel), stream_headers.py,
                                  request_body_safe_streaming_response.py
  inbound/http/errors/http_error_mapper.py   exception -> HTTP status
  inbound/http/helpers/           request_audio_reader.py (body -> audio chunks), ndjson_audio_decoder.py (SPEAKER_INBOUND events -> audio)
  outbound/null_playback/         null_audio_playback.py (SPEAKER_BACKEND=null: plays nothing, ADR-012)
  outbound/sounddevice_playback/  audio_driver.py (protocol), sounddevice_driver.py (the only importer of sounddevice),
                                  sounddevice_device_selector.py, sounddevice_audio_playback.py
composition_root/
  dependencies/audio_playback_dependency.py   new_audio_playback (SPEAKER_BACKEND: null, or the sound card with the lazy driver import)
  dependencies/speaker_service_dependency.py  new_speaker_service
  dependencies/http_app_dependency.py         new_http_app (CORS, tracing middleware; the lifespan releases the speaker on shutdown)
  containers/http_container.py                HttpContainer, new_http_container
vendor/contracts_microservice-0.16.0-py3-none-any.whl   the bundled contracts
requirements.windows.txt, requirements.linux.txt   what the service runs on (the deploy tool installs them)
requirements.dev.txt                       pytest, httpx and the lint tools (the deploy tool never installs it)
tests/  domain/ application/ infrastructure/ composition_root/ main_flow/ architecture/   (pytest, 132 tests)   +   simple.py (e2e, needs a device)
```

## 4. Flow of a playback (exists)

1. The route `handle_set_stream` (`routes/set_stream.py`, wired by `SpeakerHandler`) refuses a non-positive `sample_rate` or `channels` (`422`), builds a `RequestAudioReader` (raw PCM, or the NDJSON decoder when the content type is `application/x-ndjson`) and starts the play task with a setup future.
2. `SpeakerService.play` builds the `PlaybackFormat` and calls `SpeakerOutboundPort.play`.
3. `SoundDeviceAudioPlayback.play` (under a lock) cleans up a running session, opens the device in a thread at the first format `fallback_formats` yields (the requested one, then 44.1 kHz) and, if the rate differs, creates the `LinearResampler`. It acknowledges the setup; on a failure it acknowledges the failure and the handler answers `503`.
4. The handler answers `200` NDJSON and yields `stream_started`. The request body is consumed outside the lock into an unbounded queue; a worker writes the queue to the device in a thread.
5. When the body ends the service puts a stop sentinel and waits for the queue to be played, at most the duration of the queued audio plus 2 s (R-6: it was a fixed 3 s until 2026-11-09 and cut replies longer than about 3 s). If the bound is hit the playback result is `success: false` (since 2026-11-10) and the handler yields `error` (`playback_failed`) instead. Then the handler yields `completed` (`end_of_input`, counts), or `error` (`request_stream_failed`, `playback_failed`, `stream_failed`), then optional heartbeats.
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
* The contracts wheel was refreshed up to 0.16.0 (`vendor/`).
* 2026-11-11: the layout was aligned with `stt_microservice`: DTOs split into `dtos/inbound` and `dtos/outbound`; three port folders (`SpeakerInboundPort` is new, `SpeakerPlaybackPort` became `SpeakerServicePort`, `AudioPlaybackPort` became `SpeakerOutboundPort`); the HTTP adapter split into `routes/`, `response/`, `errors/` and `helpers/` with the handler only declaring the endpoints; the composition root's one `speaker_dependencies.py` split into one file per dependency; `tests/architecture/test_dtos.py` and `test_ports.py` added; `requirements-dev.txt` renamed `requirements.dev.txt`. Behaviour, routes and the wire format did not change.
* 2026-11-10 (ADR-012): `infrastructure/outbound/null_playback/` (`NullAudioPlayback`: drains the stream, takes the time the audio would take, supersedes, keeps no audio), `SPEAKER_BACKEND` in `SpeakerConfig`, and the composition root imports the `sounddevice` driver only on the `real` branch. A drain bound that is hit answers `success: false`.

## 7. Proposed (not built)

From the deployment audit of 2026-11-04: ~~a `null` backend (`SPEAKER_BACKEND=real|null`) behind `SpeakerOutboundPort` (called `AudioPlaybackPort` until 2026-11-11), chosen in the composition root before `sounddevice` is imported~~ **built 2026-11-10 (FR-15, ADR-012)**; the active backend is reported in the `reason` of `/available` (FR-16, no `contracts` change, decided against a `backend` field); device selection in the per-machine deploy configuration (FR-17, proposed). The known debt is in [risks-and-debt](../risks/risks-and-debt.md).
