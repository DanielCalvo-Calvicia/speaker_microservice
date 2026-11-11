# CLAUDE.md: speaker_microservice

Port **8003**. Python/FastAPI. Plays raw PCM16 audio on the local output device (`sounddevice`/PortAudio). Status: working, needs retest after recent changes. See `README.md` and `../CLAUDE.md`.

Current state (2026-11-11): branch `feature_ai_claude_2`, last commit `49e26b3` "Speaker: wait for the duration of the queued audio instead of a fixed 3 s (R-6)"; the work of the deployment plan (`docs/tasks/`) is uncommitted. Tests: `132 passed` (2026-11-11: the layout aligned with stt, 12 architecture tests added; 120 on 2026-11-10: the null backend, the lazy import of the driver, the requirements split and a drain bound that answers `success: false`; 92 before; the R-6 fix was run on a real device on 2026-11-09: a 7.12 s reply played in full). The null backend was also run as the real service, through the pipeline check and in Docker on amd64 (2026-11-10; `docker stop` with a playback in flight was killed after 10 s until the graceful-shutdown timeout of the same day, R-16, now fixed). Real playback was retested on the real device on 2026-11-10 (T-01.7; it found and fixed R-17, a playback replaced while draining); ruff (microphone venv) reports 4 findings here and mypy 4 errors, unfixed (none added). `git status` is the truth.

Read [README.md](README.md) for the state and [docs/architecture/architecture.md](docs/architecture/architecture.md) for the structure. Known debt is numbered R-1 to R-17 in [docs/risks/risks-and-debt.md](docs/risks/risks-and-debt.md).

## MANDATORY: every change updates the documentation

**No change is finished until the documents that describe it are true again.** This applies to code, configuration, tests, a decision or a contract change. Do it in the same piece of work, not later.

| If you change... | Update, in the same change |
|---|---|
| Code, a package, a folder or a file name | [docs/architecture/architecture.md](docs/architecture/architecture.md) (sections 3 and 4) and the layout of [README.md](README.md) |
| An environment variable, a default or a setting | `.env.example`, the table of [README.md](README.md), [docs/configuration/environment-variables.md](docs/configuration/environment-variables.md); then regenerate the deploy settings: `brain_microservice\windows\Scripts\python.exe deployment\scripts\env_inventory.py --write` from the workspace root |
| A route, a query parameter, a status code, an event or an error | [docs/api/api.md](docs/api/api.md), [docs/requirements/requirements.md](docs/requirements/requirements.md), the endpoint table of [README.md](README.md) and the tests; events go into `contracts` first |
| Logging, probes, start-up, shutdown | [docs/operations/monitoring.md](docs/operations/monitoring.md) |
| A requirement (new, changed, done) | [docs/requirements/requirements.md](docs/requirements/requirements.md) (status of the row) and the status table of [README.md](README.md) |
| A decision, a rule of the workspace that applies here | a new ADR in [docs/decisions/](docs/decisions/README.md) (or a dated update of the one it changes) and its row in the index |
| A risk, a limit, a known debt (found or fixed) | [docs/risks/risks-and-debt.md](docs/risks/risks-and-debt.md) and the "Known limitations" of [README.md](README.md) |
| Access, secrets, CORS, what a caller can do | [docs/security/security.md](docs/security/security.md) |
| How it is deployed, its port, its packages, the deploy catalogue | [docs/deployment/deployment.md](docs/deployment/deployment.md); `deployment/` is its own repo, read its `CLAUDE.md` first |
| The `contracts` wheel (a new version) | `requirements.*.txt`, `vendor/`, and the version named in `CLAUDE.md`, the README, the architecture and the security documents |
| The number of tests or a hardware result | the status line of [README.md](README.md), this file and [docs/requirements/requirements.md](docs/requirements/requirements.md) |

How to do it:
1. Change the documents **with** the change and say what you updated when you report the work.
2. Use dated notes (`> **Update 2026-11-05:** ...`) in documents that are history (the ADRs); correct the text in documents that describe the present (README, API, architecture, configuration, monitoring, requirements, risks).
3. Mark what is proposed as proposed and what is built as built; never describe as working something that was only run against the fake driver: say "needs hardware".
4. After editing, check that the links still resolve.
5. When the documents and the code disagree and you cannot tell which is right, do not guess: ask the maintainer.
6. `docs/old/` and `.engram/` are archives: do not update them and do not trust them.

## Role

Brain streams TTS audio to `POST /process/stream/set?sample_rate=24000&channels=1` (NDJSON `SPEAKER_INBOUND` events, or raw PCM). The service answers with an NDJSON `SPEAKER_OUTBOUND` stream: `stream_started`, then `completed` or `error` (plus heartbeats if `keep_open_after_completed=true`). Also `GET /health`, `/ready`, `/available` (both probe the device; `/available` does not mean "playing"). Nothing else is exposed. Errors before the stream: 422 invalid format, 503 device cannot open, else 500.

## Layout

`main.py` → `main_flow/` → `composition_root/` → `application/` → `domain/` → `infrastructure/`. Same layout as `stt_microservice` (aligned 2026-11-11): `application/dtos/{inbound,outbound}`, three ports (`SpeakerInboundPort`, `SpeakerServicePort`, `SpeakerOutboundPort`), the HTTP adapter in `routes/ response/ errors/ helpers/`, one file per dependency in `composition_root/dependencies/`, and `tests/architecture/` enforcing the dependency rule, the DTO folders and the ports.

## Rules

- Events use `contracts.stream` (`SPEAKER_INBOUND`/`SPEAKER_OUTBOUND`) and the shared codec.
- Audio is never converted between services. The speaker reopens at 44.1 kHz and resamples (`LinearResampler`) only if its device rejects the requested rate.
- Config: `SPEAKER_BACKEND=real|null` (code default `real`: a missing sound card is never replaced by `null`; `null` plays nothing, needs no PortAudio and is reported in the `reason` of `/available`, ADR-012; the deploy catalogue presets `null`, so the machine with the sound card sets `real` in `config/local/speaker.toml`). `SPEAKER_DEVICE_INDEX` or `SPEAKER_DEVICE_KEYWORDS` picks the device. `ALLOWED_ORIGINS` sets CORS. Also `SERVICE_NAME/HOST/PORT`, `LOG_LEVEL`. The `.env` next to `main.py` is loaded at start.
- The `sounddevice` driver is imported only on the `real` branch of `composition_root/dependencies/audio_playback_dependency.py`: keep it lazy, so `null` runs on a machine without PortAudio (a test makes `sounddevice` unimportable).
- There is **no auth** in this service (the bearer-token check was removed). A common auth middleware is planned for all services. Do not build a service-specific scheme.
- The old direct-stream autoloader was removed on purpose (`docs/old/autoloader/`). Do not reintroduce it.
- `contracts` comes from `vendor/contracts_microservice-<version>.whl` (0.16.0; the service venv still has 0.15.0 installed); refresh it with `contracts/scripts/bundle.py`.
- Ruff/mypy/black are configured in `pyproject.toml` and listed in `requirements.dev.txt` (the deploy tool never installs it) but not installed in this venv: run them with the microphone venv (`..\microphone_microservice\windows\Scripts\ruff.exe check .` and `python -m mypy .`). Known today (2026-11-11): 4 ruff findings and 4 mypy errors (R-12). Add none; do not bulk-fix lint unasked.
- **Tasks:** the deployment plan is in [docs/tasks/](docs/tasks/README.md) (order in [ORDER.md](docs/tasks/ORDER.md)); a task that plays sound, builds an image or downloads something is manual: say what it does and wait for "go".

## Commands

```powershell
& windows\Scripts\python.exe -m pip install -r requirements.dev.txt   # once: pytest, httpx and the lint tools
& windows\Scripts\python.exe main.py
& windows\Scripts\python.exe -m pytest
```

Real playback needs an output device. Say so instead of claiming it was tested when only mocks ran.
