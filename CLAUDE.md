# CLAUDE.md: speaker_microservice

Port **8003**. Python/FastAPI. Plays raw PCM16 audio on the local output device (`sounddevice`/PortAudio). Status: working, needs retest after recent changes. See `README.md` and `../CLAUDE.md`.

Current state (2026-09-22): branch `feature_ai_claude`, clean, last commit "Speaker: contract events, format validation, device-rate resampling, remove auth and autoloader".

## Role

Brain streams TTS audio to `POST /process/stream/set?sample_rate=24000&channels=1` (NDJSON events, or raw PCM). The service answers with an NDJSON event stream that ends in `completed` or `error`. Also `GET /health`, `/ready`, `/available`. Nothing else is exposed.

## Layout

`main.py` → `main_flow/` → `composition_root/` → `application/` → `domain/` → `infrastructure/`.

## Rules

- Events use `contracts.stream` (`SPEAKER_INBOUND`/`SPEAKER_OUTBOUND`) and the shared codec.
- Audio is never converted between services. The speaker resamples only if its device rejects the requested rate.
- Config: `SPEAKER_DEVICE_INDEX` or `SPEAKER_DEVICE_KEYWORDS` picks the device. `ALLOWED_ORIGINS` sets CORS. Also `SERVICE_NAME/HOST/PORT`, `LOG_LEVEL`.
- There is **no auth** in this service (the bearer-token check was removed). A common auth middleware is planned for all services. Do not build a service-specific scheme.
- The old direct-stream autoloader was removed on purpose (`docs/old/autoloader/`). Do not reintroduce it.
- Gotcha: `.env.example` still has a dangling "Required: bearer token" comment and an autoloader stream-URL comment. `README.md` and `.engram/` may still mention `SPEAKER_API_KEY`. All of it is stale, the code has no such variable.
- Ruff/mypy are configured in `pyproject.toml` but not installed in this venv. Do not bulk-fix lint unasked.

## Commands

```powershell
& windows\Scripts\python.exe main.py
& windows\Scripts\python.exe -m pytest
```

Real playback needs an output device. Say so instead of claiming it was tested when only mocks ran.
