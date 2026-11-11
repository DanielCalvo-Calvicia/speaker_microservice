# Deployment

How the service is delivered. This repository has **no `Dockerfile`, no CI workflow and no manifest**: the service is deployed by the `deployment/` tool of the workspace (`oblivion.py`, `launch.py`), whose manual is `deployment/docs/DEPLOYMENT.md` (venvs, every variable, start order, health checks). This document holds what is specific to the speaker. The audit of 2026-11-04 behind it is [`docs/deployment_audit/speaker.md`](../deployment_audit/speaker.md); evidence tags `[C]` code, `[D]` documentation, `[U]` unproven.

## What the deploy tool knows (`deployment/config/catalogue.toml`)

| Item | Value |
|---|---|
| Repository and branch | `speaker_microservice`, `feature_ai_claude_2` |
| Port | `8003` (`SERVICE_PORT`) |
| Readiness probe | `/available` |
| `audio` | `true` (the container gets `/dev/snd` on a Linux host) |
| Libraries | `shared-logging` (turned into a wheel for Docker); `contracts` comes from `vendor/` |
| Requirements | `requirements.windows.txt` / `requirements.linux.txt` |
| System packages (apt) | `libportaudio2`, `portaudio19-dev` (`libsndfile1` was removed on 2026-11-10: nothing imports `soundfile`). Only the `real` backend needs them |
| `audio`, `simulated_when` | `true`, `{ SPEAKER_BACKEND = "null" }` | Needs a sound device, except on the `null` backend: then it may run in Docker on Windows and gets no `--device /dev/snd` |
| `[env]` | `SPEAKER_BACKEND = "null"` | **A default deploy runs the null speaker** (ADR-012): a machine without a sound card passes the readiness check and `/available` says `null sink`. **The machine with the speaker must set `SPEAKER_BACKEND = "real"` in `config/local/speaker.toml`**, or the robot is healthy and mute |
| Settings file | `deployment/config/services/speaker.toml` (generated from `.env.example`); your own values in `deployment/config/local/speaker.toml` |

## Run without the tool

```powershell
& windows\Scripts\python.exe main.py            # Windows, from this folder
```

```bash
windows/bin/python main.py                      # Linux / Raspberry Pi: the venv folder keeps its name
```

Python 3.14 on Windows (`windows\`); Linux needs PortAudio first (`sudo apt-get install -y libportaudio2 portaudio19-dev`) and the user in the `audio` group (`sudo usermod -aG audio $USER`, then log in again).

## Environments and layouts

The speaker has no environment of its own. It runs where the sound output is. The `speaker-on-pc` layout (speaker on the Windows PC, the rest on the Raspberry Pi) was tested with a Pi [D]; the speaker on a Pi with an I2S or USB card is the default Linux case. `SERVICE_HOST` must be `0.0.0.0` (or the machine's address) when Brain is on another machine, and the machine's firewall must allow port 8003 for Brain.

## Order and checks

Any order among the services; Brain last. Brain waits (`STARTUP_PREFLIGHT_*`) for `GET /health` and then `GET /available` of the speaker.

```bash
curl -s http://<host>:8003/health
curl -s http://<host>:8003/available    # data.is_available must be true
```

A speaker whose `/available` never answers has no usable output device: it did not start (R-1).

## Docker

- **Linux host:** the tool passes `--device /dev/snd` for `audio = true` services; it does not add the `audio` group, which is fine for a root container but is not implemented. **Unproven [U]**; no Docker run has been done.
- **Windows host:** the sound card is not reachable from Docker. Decision of 2026-11-04 ([ADR-011](../decisions/ADR-011-windows-speaker-runs-natively.md)): the speaker keeps a declared local override (`mode = "local"`, `reason = "Windows sound card"`). **The decision is not implemented:** today the tool rejects a Docker speaker on Windows (`host_validation.py:18`) and has no per-machine `mode` key.
- A speaker image for a machine without a sound card runs on the `null` backend (FR-15, built 2026-11-10; Docker on `null` was run on 2026-11-10, below). On a Windows host the tool refuses Docker for `real` and accepts it for `null` (decision Q01-4, ADR-011 update).

## Rollback

Through the deploy tool (`update` and `rollback` with a branch, tag or commit of this repository); nothing is kept by the service. A redeploy restarts the process, so a running playback is cut.

## Not yet verified

Real playback in Local (Windows), on Linux and in Docker with `/dev/snd`; `docker stop` releasing the device (by code, SIGTERM reaches uvicorn as PID 1, then `_cleanup` and the lifespan call `stop_playback`).

## Verified in Docker (2026-11-10, tasks T-03.1 to T-03.4; amd64, Docker Desktop 29.5.2, `null` only, no audio device, nothing played)

Built and run through `oblivion.py deploy` from a scratch deployment (a copy of the working tree, `runtime = "docker"`, nothing set for the backend so the catalogue preset applied). **Build:** the deploy took 23 s (base image cached), the image is 224 MB on Python 3.12.16, `docker build` carried `APT_PACKAGES=libportaudio2 portaudio19-dev` and no `PREPARE`, nothing was compiled (0 `Building wheel`), the pip layer is 21.2 MB and the apt layer 9.7 MB (the image keeps PortAudio although `null` never imports `sounddevice`: a small cost). The `docker run` line has the `.env` as a read-only bind mount at `/app/.env`, `-p 127.0.0.1:8003:8003` and no `--device`. The tool printed `speaker: healthy and available, warning: null sink (SPEAKER_BACKEND=null): audio is discarded, nothing is played`. **Endpoints:** `/health` 200; `/ready` ready with nothing pending; `/available` true with the note; a Brain-style NDJSON body (`stream_started`, 3 s of silence in 4,800-byte `partial` events handed over at once, `completed`) answered `stream_started` and `completed` ("Playback session finalized successfully") after **3.06 s**; the same with a raw PCM body of 2 s after 2.04 s; `sample_rate=0` 422; an empty body 200; a 20 s playback replaced after 1.5 s by a 1 s one: the second took 1.02 s and the first ended after **1.64 s** with "Playback session superseded by new request"; the response decodes with the `SPEAKER_OUTBOUND` contract. **Lifecycle:** `docker restart` healthy in 0.9 s; a recreate through the tool 25.3 s with a new container; `docker start` after a stop healthy in 2.1 s. **Finding (not fixed):** `docker stop` with a playback in flight waits for it, because uvicorn's graceful shutdown waits for the open request: with a 20 s playback and a 30 s grace period it took 18.55 s and ended with exit code 0 and the cleanup (`Shutting down: releasing the speaker`); with Docker's default 10 s grace period it took 10.49 s and was killed (exit code 137, the cleanup logs never appear, the client got an incomplete read). One earlier run, with a 30 s playback started 1 s before the stop, ended in 1.64 s with exit code 137 and only the line `Shutting down`: that run is not explained (it was not repeated). **Image:** no pytest, httpx, ruff, black, mypy, numpy, soundfile or websockets; no `.env*` file in the image (and 0 entries in the 8,428 layer entries of `docker save`); 0 matches for key, secret, token or password patterns in `docker history`, `docker inspect` of the image and of the container; the process runs as root; the image also holds `tests/` and `docs/`. **Not verified:** `/dev/snd` and a real sound card in a container (Linux/Pi, postponed), arm64, and Brain in front of the container.

**Fix of the `docker stop` finding (2026-11-10).** **Fixed 2026-11-10:** `main_flow/http.py` passes `timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS` (5 s) to uvicorn, which now cancels the open requests after 5 s and runs the lifespan cleanup. Test first (`tests/main_flow/test_shutdown.py`, failing on the old code), 4 of 4 one-line mutations caught. Re-run in Docker with Docker's default 10 s grace period: with a 20 s playback in flight `docker stop` took **5.73 s** and ended with exit code **0**; the log shows `Shutting down: releasing the speaker`, `Speaker playback stopped` and `Server stopped; releasing speaker`; the sender got an incomplete read (the playback was cut by the stop, as it must be). Same uvicorn ERROR line for the cancelled request.
