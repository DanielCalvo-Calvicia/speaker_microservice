# CLAUDE.md: speaker_microservice

Port **8003**. Python/FastAPI. Plays raw PCM16 audio on the local output device (`sounddevice`/PortAudio). Status: working, needs retest after recent changes. See `README.md` and `../CLAUDE.md`.

## Role

Brain streams TTS audio to `POST /process/stream/set?sample_rate=24000&channels=1` (NDJSON events, or raw PCM). The service answers with an NDJSON event stream that ends in `completed` or `error`. Also `GET /health`, `/ready`, `/available`.

## Layout

`main.py` → `main_flow/` → `composition_root/` → `application/` → `domain/` → `infrastructure/`.

## Rules

- Events use `contracts.stream` (`SPEAKER_INBOUND`/`SPEAKER_OUTBOUND`) and the shared codec.
- Audio is never converted between services. The speaker resamples only if its device rejects the requested rate.
- Config: `SPEAKER_DEVICE_INDEX` or `SPEAKER_DEVICE_KEYWORDS` picks the device. `ALLOWED_ORIGINS` sets CORS.
- **Auth:** routes other than `/health` expect a bearer token (`SPEAKER_API_KEY`). This is currently not wired from Brain and is treated as unused. A common auth middleware is planned. Do not build a service-specific auth scheme.
- The old direct-stream autoloader was removed on purpose (`docs/old/autoloader/`). Do not reintroduce it.

## Commands

```powershell
& windows\Scripts\python.exe main.py
& windows\Scripts\python.exe -m pytest
```

Real playback needs an output device. Say so instead of claiming it was tested when only mocks ran.
