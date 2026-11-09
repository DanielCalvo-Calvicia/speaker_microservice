# speaker_microservice

HTTP service that plays raw signed 16-bit PCM audio, streamed by a client, on the local output device (`sounddevice` / PortAudio). It answers with `contracts.stream` events (`SPEAKER_OUTBOUND`). Part of OBLIVION, a voice robot made of small HTTP services; **only Brain calls it**, and it calls nobody. Port **8003**, Python / FastAPI.

```
Brain ──POST /process/stream/set──►  speaker  ──►  output device
      (raw PCM or SPEAKER_INBOUND)   (plays while it receives)
      ◄── NDJSON SPEAKER_OUTBOUND ──  stream_started, completed | error
```

## Status

Working, needs a hardware retest. The service and its tests are built and pass; real playback on a device was not run in the last passes.

| Area | State |
|---|---|
| Playback of a PCM stream (raw or NDJSON `SPEAKER_INBOUND`) and the NDJSON answer (`SPEAKER_OUTBOUND`) | Implemented; tested with a fake driver |
| Statuses before the stream (`422`, `503`, `500`) and `error` events after it | Implemented |
| One playback at a time (a new request supersedes the running one) | Implemented |
| Device-rate fallback to 44.1 kHz with resampling | Implemented; not run on hardware |
| Device selection (index, keywords, OS default) | Implemented; the keywords suit ALSA (see risks) |
| `/health`, `/ready`, `/available` | Implemented |
| Authentication | **None**, on purpose (a common scheme for all services is planned) |
| Real playback on a device (`tests/simple.py`), Docker with `/dev/snd` | **Not run** |
| A `null` sink backend for machines without a sound card; the active backend in `/available` | Proposed, not built |

92 tests pass (2026-11-09; 84 on 2026-11-05), all with a fake driver. `ruff`, `mypy` and `black` are configured in `pyproject.toml` but not installed in this venv.

## Run

```powershell
& windows\Scripts\python.exe main.py        # Windows (the service's own venv)
```

```bash
windows/bin/python main.py                  # Linux / Raspberry Pi: the venv folder keeps its name
```

Install with `pip install -r requirements.windows.txt` (or `requirements.linux.txt`; Linux needs `libportaudio2` and `portaudio19-dev` first). Settings come from the environment; a `.env` file is loaded if present (template: [.env.example](.env.example)). The default bind address is `127.0.0.1`; set `SERVICE_HOST` (for example `0.0.0.0`) when Brain runs on another machine. The service does not start without a usable output device.

```bash
curl -s http://127.0.0.1:8003/health
curl -s http://127.0.0.1:8003/available     # data.is_available true when the device can be used
```

## Configuration

Every variable has a default. Full table: [docs/configuration/environment-variables.md](docs/configuration/environment-variables.md).

| Variable | Default | Purpose |
|---|---|---|
| `SERVICE_NAME` | `Speaker Microservice` | API title / log name (the shared logger also reads `SERVICE_NAME`) |
| `SERVICE_HOST` | `127.0.0.1` | Bind address |
| `SERVICE_PORT` | `8003` | Bind port |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins (credentials only when it is not `*`) |
| `SPEAKER_DEVICE_INDEX` | *(empty)* | Explicit output device index; empty = auto-detect |
| `SPEAKER_DEVICE_KEYWORDS` | `i2s,hw,default,sysdefault` | Device-name keywords for auto-detect; falls back to the OS default output |
| `LOG_LEVEL` | `INFO` | Read by the shared logging package (`TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`) |

`LOG_FORMAT`, `LOG_OUTPUT`, `ENVIRONMENT` and `TRACE_EXPORT_*` are also read by the shared logging package: see [`shared-logging/docs/logging.md`](../shared-logging/docs/logging.md). The table equals `.env.example` and `ServerConfig` / `SpeakerConfig` in `infrastructure/config/`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process/stream/set?sample_rate=24000&channels=1` | Brain's playback request. Body: raw PCM, or `SPEAKER_INBOUND` NDJSON events. Answers an NDJSON `SPEAKER_OUTBOUND` stream: `stream_started`, then `completed` or `error` (plus heartbeats if `keep_open_after_completed=true`) |
| GET | `/health` | Liveness |
| GET | `/ready` | Whether the selected device has output channels |
| GET | `/available` | Whether the output device can be used (probed without opening a stream); not "a playback is active" |

The probes use the envelope `action / status / status_code / message / timestamp / data`. Failures before the stream: `422` invalid format, `503` the device cannot be opened, else `500`. Full contract: [docs/api/api.md](docs/api/api.md).

Audio is never converted between services. Only if the device refuses the requested rate does the speaker reopen it at 44.1 kHz and resample the audio to that rate (`domain/operations/resample.py`).

## Project layout

```text
main.py            entry point (calls main_flow)
main_flow/         config, logging init, uvicorn, graceful shutdown (stops playback)
composition_root/  the only place concrete adapters are wired together (app, CORS, tracing middleware)
infrastructure/    config, HTTP (inbound: handler, envelope, error mapper, request reader, NDJSON decoder/encoder) and sounddevice (outbound) adapters
application/       use-case service, ports, DTOs, application errors
domain/            playback format value object, format negotiation, resampler
tests/             domain, application, infrastructure, composition_root, architecture (pytest) and simple.py (end to end, needs a device)
vendor/            the bundled contracts wheel (0.15.0); refresh with contracts/scripts/bundle.py
docs/              api, architecture, configuration, decisions, deployment, operations, requirements, risks, security
```

Dependencies point inward only (`infrastructure -> application -> domain`); `tests/architecture/` enforces this.

## Test

```powershell
& windows\Scripts\python.exe -m pytest        # unit + architecture tests, no hardware needed
& windows\Scripts\python.exe tests\simple.py  # end to end, needs a real output device
```

Real playback on a device was not run in the last passes: it needs an output device.

## Scope

- **In scope:** play the PCM16 stream Brain sends on the local output device and report how it went as contract events.
- **Non-goals:** calling other services (Brain is the only coordinator), converting audio between services, authentication of its own (a common scheme comes later), storing audio.
- **Proposed, not built:** a `null` backend for machines without a sound card; the active backend in `/available`; device choice per machine in the deploy configuration.

## Known limitations

- Without a usable output device the process does not start, so `/available` never answers false (R-1).
- `sounddevice` is imported at start-up, so a machine without PortAudio cannot start it either (R-2).
- On Linux the default keywords can match the wrong ALSA device; set `SPEAKER_DEVICE_INDEX` (R-3).
- After the body of a request ends the service waits for the device up to the duration of the queued audio plus 2 s. Until 2026-11-09 the wait was a fixed 3 s and a reply longer than about 3 s was cut (R-6, confirmed on a real device: a 7.15 s sentence played for 3 s and the call returned `success: true`); fixed, tested with a fake real-time device and confirmed on the real device on 2026-11-09 (a 7.12 s reply was written in full). If the bound is hit anyway the rest is dropped, logged, and still answered as a success.
- No authentication: whoever reaches the port can play audio and interrupt the speech (R-8).

All of them, with their numbers, are in [docs/risks/risks-and-debt.md](docs/risks/risks-and-debt.md).

## Documentation

| Document | Content |
|---|---|
| [docs/api/api.md](docs/api/api.md) | Routes, the playback request and its NDJSON answer, statuses |
| [docs/architecture/architecture.md](docs/architecture/architecture.md) | Layers, layout, flow of a playback, state |
| [docs/configuration/environment-variables.md](docs/configuration/environment-variables.md) | Every variable |
| [docs/requirements/requirements.md](docs/requirements/requirements.md) | Functional and non-functional requirements with their status |
| [docs/operations/monitoring.md](docs/operations/monitoring.md) | Probes, start and shutdown, logs |
| [docs/security/security.md](docs/security/security.md) | What is and is not protected |
| [docs/deployment/deployment.md](docs/deployment/deployment.md) | How the deploy tool runs it; Docker and Windows |
| [docs/decisions/](docs/decisions/README.md) | Architecture decision records (ADR-001 to ADR-011) |
| [docs/risks/risks-and-debt.md](docs/risks/risks-and-debt.md) | Risks, limits and known debt (R-1 to R-15) |
| [docs/deployment_audit/speaker.md](docs/deployment_audit/speaker.md) | The deployment audit of 2026-11-04 (not committed) |
| [docs/old/](docs/old/) | Archive: the previous layout, the removed auth and the removed autoloader (do not trust) |
| [CLAUDE.md](CLAUDE.md) | Rules for working in this repository, including the mandatory update of the documentation |
