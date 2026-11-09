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
| System packages (apt) | `libportaudio2`, `portaudio19-dev`, `libsndfile1` (the last is not needed: nothing imports `soundfile`) |
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
- A speaker image for a machine without a sound card needs the `null` backend (FR-15, proposed).

## Rollback

Through the deploy tool (`update` and `rollback` with a branch, tag or commit of this repository); nothing is kept by the service. A redeploy restarts the process, so a running playback is cut.

## Not yet verified

Real playback in Local (Windows), on Linux and in Docker with `/dev/snd`; `docker stop` releasing the device (by code, SIGTERM reaches uvicorn as PID 1, then `_cleanup` and the lifespan call `stop_playback`).
