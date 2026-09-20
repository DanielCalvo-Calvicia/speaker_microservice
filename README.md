# Speaker Microservice

HTTP service that plays raw signed 16-bit PCM audio, streamed by a client, on the local output
device (via `sounddevice` / PortAudio).

## Run

```bash
pip install -r requirements.windows.txt   # or requirements.linux.txt
python main.py
```

Configuration is read from the environment (a `.env` file is loaded if present); see `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `SERVICE_NAME` | `Speaker Microservice` | API title / log name |
| `SERVICE_HOST` | `127.0.0.1` | Bind address |
| `SERVICE_PORT` | `8003` | Bind port |
| `LOG_LEVEL` | `INFO` | Read by the shared logging module; `TRACE`→DEBUG, `WARN`→WARNING also accepted |
| `LOG_FORMAT`, `SERVICE_NAME`, `TRACE_EXPORT_*` | see docs | Also read by the shared logging module: [`shared-logging/docs/logging.md`](../shared-logging/docs/logging.md) |
| `SPEAKER_API_KEY` | *(required)* | Bearer token for every route except `/health`; startup fails without it |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |
| `SPEAKER_DEVICE_INDEX` | *(empty)* | Explicit output device; empty = auto-detect |
| `SPEAKER_DEVICE_KEYWORDS` | `i2s,hw,default,sysdefault` | Device-name keywords for auto-detect; falls back to the OS default output |

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | no | Liveness |
| GET | `/ready` | yes | `true` if the selected device has output channels |
| GET | `/available` | yes | `true` while a playback session is active |
| POST | `/process/stream/set?sample_rate=24000&channels=1` | yes | Body is raw PCM, or NDJSON events (`Content-Type: application/x-ndjson`). Answers with an NDJSON event stream |

`/health`, `/ready` and `/available` use the envelope `action / status / status_code / message /
timestamp / data`. Every failure currently returns HTTP 500.

The playback response is NDJSON: `stream_started` once the device is open, then `completed`
(or `error`), plus `heartbeat` events if `keep_open_after_completed=true`. A new playback request
supersedes a running one. If the device rejects the requested rate it is reopened at 44.1 kHz
(the audio is not resampled).

## Project layout

```text
main.py            entry point (calls main_flow)
main_flow/         startup and graceful shutdown (logging: shared `shared_logging` package)
composition_root/  the only place concrete adapters are wired together
infrastructure/    config, HTTP (inbound) and sounddevice (outbound) adapters
application/       use-case service, ports, DTOs, application errors
domain/            playback format value object, pure format negotiation
```

Dependencies point inward only (`infrastructure → application → domain`); `tests/architecture/`
enforces this.

## Development

```bash
pytest                    # unit + architecture tests (no hardware needed)
mypy .
ruff check .
black --check .
python tests/simple.py    # end-to-end, needs a real output device
```

Architecture: [docs/architecture/architecture.md](docs/architecture/architecture.md).
The previous layout is documented in [docs/old/](docs/old/).
