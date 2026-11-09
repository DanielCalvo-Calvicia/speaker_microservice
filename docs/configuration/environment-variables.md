# Environment variables

Settings come from the process environment; a `.env` file in the working directory is loaded first if it exists (`python-dotenv`, `main_flow/http.py`) and a variable already set in the process wins over the file. They are read once at start-up into two frozen dataclasses in `infrastructure/config/`: `ServerConfig` and `SpeakerConfig`. The template with comments is [`.env.example`](../../.env.example); the README repeats the table. **Never write a real secret in `.env.example`, in the code or in a document.**

Sensitive: none. This service holds no secret and has no authentication. `.env` is ignored by git.

Every variable has a default; none is required.

## Service (`ServerConfig`)

| Variable | Default | Description | Sensitive |
|---|---|---|---|
| `SERVICE_NAME` | `Speaker Microservice` | Title of the API and name in the start-up log (the shared logger also reads it) | no |
| `SERVICE_HOST` | `127.0.0.1` | Bind address. Set `0.0.0.0` (or the machine's address) when Brain runs on another machine; the deploy tool computes it | no |
| `SERVICE_PORT` | `8003` | Bind port. An invalid number stops the start with a `ValueError` | no |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins. Credentials are allowed only when it is not `*` | no |

## Output device (`SpeakerConfig`)

| Variable | Default | Description | Sensitive |
|---|---|---|---|
| `SPEAKER_DEVICE_INDEX` | empty | Index of the output device (PortAudio). Empty means auto-detect. A non-number stops the start with a `ValueError` | no |
| `SPEAKER_DEVICE_KEYWORDS` | `i2s,hw,default,sysdefault` | Words looked for, case-insensitive, in the device names when the index is empty; the first output device that matches wins, otherwise the OS default output is used. The defaults suit ALSA / Raspberry Pi; on Windows no name usually matches and the OS default is used | no |

Device order: the configured index, else the first keyword match, else the OS default output; if there is none, the service does not start.

## Read by the shared logging package, not by this service

`LOG_LEVEL` (`TRACE`, `DEBUG`, `INFO`, `WARN`/`WARNING`, `ERROR`, `CRITICAL`; default `INFO`), `LOG_FORMAT`, `LOG_OUTPUT`, `ENVIRONMENT` and `TRACE_EXPORT_*`: see [`shared-logging/docs/logging.md`](../../../shared-logging/docs/logging.md). `APP_ENV` is **not** read any more.

## Set by the deploy tool

`SERVICE_HOST` and `SERVICE_PORT` are computed by `deployment/` from the layout; `ALLOWED_ORIGINS` is shared with the other services in `deployment/config/services/all.toml`. The per-service settings file is `deployment/config/services/speaker.toml`, generated from `.env.example` (`deployment/scripts/env_inventory.py --write`), so a change to `.env.example` needs that regeneration (see [CLAUDE.md](../../CLAUDE.md)).

## Brain's side

Brain finds this service through its own `SPEAKER_BASE_URL` and `SPEAKER_PLAY_STREAM_ENDPOINT`; they are Brain's settings, documented in `deployment/docs/DEPLOYMENT.md`, not this service's.
