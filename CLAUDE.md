# CLAUDE.md: speaker_microservice

Port **8003**. Python/FastAPI. Plays raw PCM16 audio on the local output device (`sounddevice`/PortAudio). Status: working, needs retest after recent changes. See `README.md` and `../CLAUDE.md`.

Current state (2026-10-01): branch `feature_ai_claude_2` (tracks `origin/feature_ai_claude_2`, in sync), working tree clean, last commit `0fe580b` "Bundle contracts 0.9.0" (the feature commit is `eacddae`, 2026-09-20). Tests: `84 passed`. Real playback on a device was not run in the last documentation pass; ruff (microphone venv) reports 8 findings here, unfixed.

## Role

Brain streams TTS audio to `POST /process/stream/set?sample_rate=24000&channels=1` (NDJSON `SPEAKER_INBOUND` events, or raw PCM). The service answers with an NDJSON `SPEAKER_OUTBOUND` stream: `stream_started`, then `completed` or `error` (plus heartbeats if `keep_open_after_completed=true`). Also `GET /health`, `/ready`, `/available` (both probe the device; `/available` does not mean "playing"). Nothing else is exposed. Errors before the stream: 422 invalid format, 503 device cannot open, else 500.

## Layout

`main.py` → `main_flow/` → `composition_root/` → `application/` → `domain/` → `infrastructure/`.

## Rules

- Events use `contracts.stream` (`SPEAKER_INBOUND`/`SPEAKER_OUTBOUND`) and the shared codec.
- Audio is never converted between services. The speaker reopens at 44.1 kHz and resamples (`LinearResampler`) only if its device rejects the requested rate.
- Config: `SPEAKER_DEVICE_INDEX` or `SPEAKER_DEVICE_KEYWORDS` picks the device. `ALLOWED_ORIGINS` sets CORS. Also `SERVICE_NAME/HOST/PORT`, `LOG_LEVEL`.
- There is **no auth** in this service (the bearer-token check was removed). A common auth middleware is planned for all services. Do not build a service-specific scheme.
- The old direct-stream autoloader was removed on purpose (`docs/old/autoloader/`). Do not reintroduce it.
- `contracts` comes from `vendor/contracts_microservice-<version>.whl` (0.10.0); refresh it with `contracts/scripts/bundle.py`.
- Ruff/mypy/black are configured in `pyproject.toml` but not installed in this venv. Do not bulk-fix lint unasked.

## Commands

```powershell
& windows\Scripts\python.exe main.py
& windows\Scripts\python.exe -m pytest
```

Real playback needs an output device. Say so instead of claiming it was tested when only mocks ran.
