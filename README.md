# Speaker Microservice

HTTP service that plays raw signed 16-bit PCM audio, streamed by a client, on the local output device (via `sounddevice` / PortAudio). It answers with `contracts.stream` events (`SPEAKER_OUTBOUND`). Only Brain calls it.

## Run

```bash
pip install -r requirements.windows.txt   # or requirements.linux.txt
python main.py
```

(Use the service's own venv, `windows\Scripts\python.exe`.) Configuration is read from the environment (a `.env` file is loaded if present); see `.env.example`. The default bind address is `127.0.0.1`; set `SERVICE_HOST` (for example `0.0.0.0`) when Brain runs on another machine.

| Variable | Default | Purpose |
|---|---|---|
| `SERVICE_NAME` | `Speaker Microservice` | API title / log name (the shared logger also reads `SERVICE_NAME`) |
| `SERVICE_HOST` | `127.0.0.1` | Bind address |
| `SERVICE_PORT` | `8003` | Bind port |
| `LOG_LEVEL` | `INFO` | Read by the shared logging module (`TRACE`, `DEBUG`, `INFO`, `WARN`/`WARNING`, `ERROR`, `CRITICAL`) |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins (credentials are only allowed when it is not `*`) |
| `SPEAKER_DEVICE_INDEX` | *(empty)* | Explicit output device index; empty = auto-detect |
| `SPEAKER_DEVICE_KEYWORDS` | `i2s,hw,default,sysdefault` | Device-name keywords for auto-detect; falls back to the OS default output |

`LOG_FORMAT`, `LOG_OUTPUT`, `ENVIRONMENT` and `TRACE_EXPORT_*` are also read by the shared logging package, not by this service: see [`shared-logging/docs/logging.md`](../shared-logging/docs/logging.md). The table equals `.env.example` and `ServerConfig`/`SpeakerConfig` in `infrastructure/config/`.

**There is no authentication.** An earlier version required `SPEAKER_API_KEY` (a bearer token); that was removed and no variable of that name exists. A common auth scheme for all services is not designed yet.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness (`HealthCheckResponse{healthy}`) |
| GET | `/ready` | `ReadinessResponse{is_ready, pending_reason}`: whether the selected device has output channels |
| GET | `/available` | `AvailabilityResponse{is_available, reason}`: whether the output device can be used, probed without opening a stream |
| POST | `/process/stream/set?sample_rate=24000&channels=1` | Brain's playback request. Body is raw PCM, or `contracts.stream` NDJSON events (`SPEAKER_INBOUND`: `stream_started` announcing the same format, `partial` with `bytes_base64`, `completed` per spoken text, `heartbeat`). Answers with an NDJSON event stream |

`/health`, `/ready` and `/available` use the envelope `action / status / status_code / message / timestamp / data` (`contracts.api.common.envelope.ApiEnvelope`).

The playback answer (`application/x-ndjson`, `SPEAKER_OUTBOUND`) is `stream_started` once the device is open, then `completed` (`reason: end_of_input`, `chunk_count`, `byte_count`) or `error` (`request_stream_failed`, `playback_failed`, `stream_failed`). Extra query parameters: `keep_open_after_completed` (default `false`; when `true`, `heartbeat` events follow `completed`), `heartbeat_interval_seconds` (15) and `max_heartbeats_after_completed` (unlimited). A new playback request supersedes a running one.

Failures before the stream starts: `422` non-positive `sample_rate`/`channels` or invalid format, `503` the output device could not be opened, `500` anything else.

Audio is never converted between services. Only if the device refuses the requested rate does the speaker reopen it at 44.1 kHz **and resample the audio to that rate** (linear interpolation, `domain/operations/resample.py`) so it plays at the right pitch and speed; it logs a warning when it does.

## Project layout

```text
main.py            entry point (calls main_flow)
main_flow/         config, logging init, uvicorn, graceful shutdown (stops playback)
composition_root/  the only place concrete adapters are wired together (app, CORS, tracing middleware)
infrastructure/    config, HTTP (inbound: handler, envelope, error mapper, request reader, NDJSON decoder/encoder) and sounddevice (outbound) adapters
application/       use-case service, ports, DTOs, application errors
domain/            playback format value object, format negotiation, resampler
```

Dependencies point inward only (`infrastructure -> application -> domain`); `tests/architecture/` enforces this.

## Development

```powershell
windows\Scripts\python.exe -m pytest        # unit + architecture tests (no hardware needed)
windows\Scripts\python.exe tests\simple.py  # end to end, needs a real output device
```

Result on 2026-10-01: `84 passed` in 1.9 s. `ruff`, `mypy` and `black` are configured in `pyproject.toml` but not installed in this venv; the microphone venv's ruff reports 8 findings here (4 auto-fixable), not fixed on purpose. Real playback (`tests/simple.py`, the sounddevice adapter on a real device) was not run: it needs an output device.

Architecture: [docs/architecture/architecture.md](docs/architecture/architecture.md). The previous layout, the removed auth and the removed autoloader are archived in [docs/old/](docs/old/).
