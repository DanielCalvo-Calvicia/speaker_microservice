# ADR-012 — A null playback backend, reported in the `reason` of `/available`

**Status:** Accepted (2026-11-09, the maintainer answered [Q01](../questionnaires/Q01_before-the-deployment-tasks.md) 1 to 4 and 7 "Recommended"; task T-01.1). Built 2026-11-10 (T-01.2 to T-01.4); see the update at the end.
**Related:** [ADR-011](ADR-011-windows-speaker-runs-natively.md), [ADR-008](ADR-008-new-playback-supersedes-the-running-one.md), [tts ADR-008](../../../tts_microservice/docs/decisions/ADR-008-fallback-reported-in-available-reason.md), [risks R-1, R-2, R-4](../risks/risks-and-debt.md), microphone ADR-007 (the same decision for the other audio service)

## Context

Without an output device the process does not start (`SoundDeviceAudioPlayback.__init__` raises while the app is built) and `sounddevice` is imported at module level, so a machine without a sound card or without PortAudio cannot run the service. `/available` cannot say which backend runs. A silent fake default would make a robot with a broken sound card look healthy.

## Decision

1. `SPEAKER_BACKEND=real|null`, **code default `real`**; an unknown value stops the start naming the variable. The backend is chosen in the composition root **before** the `sounddevice` driver module is imported (lazy import), so `null` needs no PortAudio.
2. A machine without a sound card starts on `null` through a **catalogue preset** (`[services.speaker.env] SPEAKER_BACKEND = "null"`); the machine with the sound card sets `real` in `deployment/config/local/speaker.toml`. Accepted consequence: a default deploy is `null`; the tool's warning line is the safety net.
3. The active backend is reported in the `reason` of `/available` (`is_available: true`, a short note that contains `null`; none on `real`), no `contracts` change; the service logs it once at start. `/ready` shows nothing pending for a ready service.
4. The null sink **always drains the whole request stream** and **paces itself to real time by default** (Brain's echo guard and speech cues use the bytes Brain sends, so Brain does not need it; pacing only makes `completed` arrive when real playback would). It keeps **no audio**, only counters in the log. A new request supersedes the running one and `stop_playback` is idempotent, as on the real backend.
5. Docker on a Windows host: the rule that rejects an audio service stays (ADR-011's per-machine `mode = "local"` override is **not** implemented); a service whose resolved backend is `null` is allowed to run in Docker there. One change in the deploy tool, shared with the microphone (`sim`).

## Consequences

- Positive: a machine without a sound card passes the readiness check; Docker can be proven on this PC on `null`.
- Negative: a default deploy to the robot is silent unless `real` is set; Brain does not show the `reason`.

> **Update 2026-11-10 (built):** `infrastructure/outbound/null_playback/null_audio_playback.py` (`NullAudioPlayback`: reads every chunk, then waits until a device would have finished, looking every 0.1 s for a newer request or a close; the result messages are the real backend's), `SpeakerConfig.backend`, the lazy import of the driver in `new_audio_playback`, one warning at start `Speaker backend is null: audio is discarded`, and `/available` answers `is_available: true` with `reason` = `"null sink (SPEAKER_BACKEND=null): audio is discarded, nothing is played"`. `/ready` now sends `pending_reason` only when the service is not ready (before, it would have shown the null note as something pending). Not decided in Q01 and chosen here: no environment variable turns the pacing off (one more setting for no operator need); the tests construct the sink unpaced. A related change decided in the same answers: a drain bound that is hit answers `success: false` (Q01-6, T-01.6). The catalogue preset and the `simulated_when` key are in `deployment`.

> **Update 2026-11-10 (Docker):** the image builds and runs through `oblivion.py` on a Windows host on `null` (accepted through `simulated_when`), the tool prints the note as a warning, every endpoint answers, a 3 s playback sent at once takes 3.06 s and a replaced one ends early. One finding that is not about `null`: `docker stop` with a playback in flight waits for it and is killed after Docker's 10 s grace period (R-16); see `docs/deployment/deployment.md`.

> **Update 2026-11-10 (stop fixed):** the `docker stop` finding of the Docker run (R-16) was fixed with `timeout_graceful_shutdown` (5 s) in `main_flow/http.py`; see `docs/deployment/deployment.md`.
