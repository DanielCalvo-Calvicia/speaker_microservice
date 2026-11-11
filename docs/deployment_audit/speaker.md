# speaker_microservice (port 8003)

Verified against the code on 2026-11-04 (corrections folded in; evidence tags as in `README.md`).

## Role
Plays PCM16 audio on the output device. Brain streams TTS audio to `POST /process/stream/set`; answers an NDJSON outbound stream. Also `/health`, `/ready`, `/available`. No authentication (removed on purpose). [C: `CLAUDE.md`, `http_handler.py`]

## Dependencies
- **Used at runtime:** fastapi, uvicorn, python-dotenv, sounddevice. [C]
- **Listed but not imported by production code:** numpy, soundfile, websockets; httpx is used only by tests. [C: grep of `application/ domain/ infrastructure/ composition_root/ main_flow/`]
- **Dev tools listed in the runtime files:** pytest, ruff, black, mypy. All unpinned. [C]
- **Libraries:** `-e ../shared-logging` (no repo yet; the deploy tool turns it into a wheel for Docker) and the vendored `contracts` 0.15.0 wheel (`./vendor/`). [C]
- **System:** PortAudio (`libportaudio2`, `portaudio19-dev`). `libsndfile1` is in the catalogue `apt` list but nothing imports `soundfile`, so it is not needed. [C]

## Hardware
Audio output.

## Portability
Windows and Linux.

## Local
Works on Windows; hardware retest pending [D]. The speaker-on-PC layout was tested with a Pi [D]. The 84 existing tests pass (run 2026-11-04); they use a fake driver, not a device.

## Docker
Same as microphone:
- **Linux host**: the deploy tool passes `--device /dev/snd` for `audio = true` services (`docker_runtime.py:52`). It does not add the `audio` group; that is fine for a root container but is not implemented. Unproven [U].
- **Windows host**: not reachable from Docker; use the declared local override (`mode = "local"`, `reason = "Windows sound card"`), per the 2026-11-04 decision. **This override is a decision, not implemented yet:** today the tool rejects a Docker speaker on Windows (`host_validation.py:18`) and has no per-machine `mode` key.

## Configuration
`SPEAKER_DEVICE_INDEX`, `SPEAKER_DEVICE_KEYWORDS` (default `i2s,hw,default,sysdefault`, ALSA/Pi flavoured), `ALLOWED_ORIGINS=*`.

## Problems
1. **No null/sim sink** (0 matches in production code). Without an output device **the process does not start**: `SoundDeviceAudioPlayback.__init__` calls `selector.select()` and raises `SpeakerUnavailable` while `new_http_container` builds the app, before uvicorn runs. So `/available` never answers false; brain's preflight just cannot reach the service. [C]
2. **`sounddevice` is imported at module level** (`sounddevice_driver.py`, reached from `speaker_dependencies.py`). Without PortAudio the import itself fails, so a null backend that is selected after that import still crashes on a machine with no PortAudio. [C]
3. **Device keywords matter on Linux, not on Windows.** On the Windows PC checked (Realtek, Bluetooth headsets, Voicemod) no output device name contains any default keyword, so the selector falls back to the OS default output, which works. On a Linux PC `hw` or `default` can match the first ALSA device (for example HDMI) before the wanted one. [C]
4. **`/available` cannot say which backend is active:** `AvailabilityResponse` has only `is_available` and `reason` (`reason` is `None` when ready). [C]
5. Dev tools and unused libraries at runtime; unpinned; CORS `*`.
6. Audio resampling happens here only if the device rejects the rate (by design; keep).

## Recommended changes
1. Add a `null` sink backend (`SPEAKER_BACKEND=real|null`) behind the existing `AudioPlaybackPort`.
   - Choose the backend in the composition root **before** importing the sounddevice driver (lazy import), so a null-only machine needs no PortAudio and the Docker image for it can skip `libportaudio2`.
   - The null sink must drain the request stream (otherwise Brain's POST backs up) and, by default, pace itself to real time (sleep for the audio duration), so `completed` arrives when real playback would. Check what Brain's echo guard and speech cues need before choosing the default.
   - Update `tests/composition_root/test_http_container.py`, which patches `speaker_dependencies.SoundDeviceDriver`.
2. Report the active backend: add a `backend` field to `AvailabilityResponse` in `contracts` (bump the version, then producers and consumers), or, as a fallback, put it in `reason`. The field is cleaner.
3. Move device selection into the per-machine hardware config (keywords per machine; index when known).
4. Split dev requirements, drop `numpy`/`soundfile`/`websockets` (and `libsndfile1` from the catalogue `apt` list), pin ranges.

## Tests
- Existing 84 tests; new tests for the null sink, including: starts with no device and no PortAudio, drains and paces the stream, keeps `/health`, `/ready`, `/available` and the NDJSON events identical in shape to the real backend.
- Hardware: real playback in Local (Windows) and in Docker on Linux with `/dev/snd`.
- Shutdown: `docker stop` releases the device without hanging playback. By code reading, `python main.py` as PID 1 gets SIGTERM through uvicorn, then `_cleanup` and the lifespan call `stop_playback` (idempotent); no Docker path has ever run [U].

## Update 2026-11-09

Checked against the code and the tests the same day (facts F1 to F16 of [../tasks/README.md](../tasks/README.md)); this audit stays a record of 2026-11-04. Still true: no null sink and no process without an output device (problem 1), `sounddevice` imported at module level (problem 2), `/available` cannot name the backend (problem 4), dev tools and unused packages (`numpy`, `soundfile`, `websockets`) in the runtime requirements, unpinned, `libsndfile1` in the catalogue, CORS `*`; Docker on a Windows host cannot reach the sound card and the tool rejects it (`host_validation.py:18`). What changed: **92 tests** (not 84): the fixed 3 s drain wait (R-6) is now the duration of the queued audio plus 2 s, built and confirmed on the real device on 2026-11-09 (commit `49e26b3`); `contracts` 0.16.0 is bundled (the venv still has 0.15.0); ruff reports 8 findings and mypy 4 errors (run with the microphone venv). The service already loads its `.env` (`dotenv` is true in the catalogue). The recommendation to report the backend in a `contracts` field (recommended change 2) is now a question (Q01-2) whose recommended answer is the `reason` of `/available`, as tts did (ADR-008), with no `contracts` change. Plan: [../tasks/README.md](../tasks/README.md); open decisions: [../questionnaires/Q01_before-the-deployment-tasks.md](../questionnaires/Q01_before-the-deployment-tasks.md). Linux and the Raspberry Pi are postponed until the services work at 100 % on Windows.

## Update 2026-11-10

The recommended changes were made (plan: [../tasks/README.md](../tasks/README.md), decision: [../decisions/ADR-012-null-backend.md](../decisions/ADR-012-null-backend.md)): (1) `SPEAKER_BACKEND=real|null`, code default `real`, the `sounddevice` driver imported only for `real`, `null` through a catalogue preset in `deployment`; the null sink drains the stream, takes the time the audio would take and keeps no audio; (2) the active backend is reported in the `reason` of `/available` (the `contracts` field was not chosen); `/ready` shows nothing pending for a ready service; (3) the runtime requirements lost the dev tools, `numpy`, `soundfile` and `websockets` and were pinned, and the catalogue lost `libsndfile1`; (4) a drain bound that is hit answers `success: false`. Device keywords per machine already live in `config/local/speaker.toml` (R-3 stays a Linux task, postponed). Run: 116 unit tests, the workspace pipeline check (84 passed, 18 skipped) and the real service on `null` in a scratch folder (3 s of silence sent at once took 3.09 s; a replaced playback ended after 1.64 s). **Not run:** Docker (T-03), the real device since the R-6 retest (T-01.7), Linux (postponed).

## Update 2026-11-10 (Docker)

The Docker acceptance on amd64 on `null` was run (tasks T-03.1 to T-03.4, details in [../deployment/deployment.md](../deployment/deployment.md)): the image builds in 23 s (224 MB), the deploy passes the readiness check without a device and prints the null note, every endpoint answers, a stream sent at once takes the time the audio would take, restart and recreate work, the image holds no dev tool, no unused package and no secret. The audit's remark that `docker stop` releases the device without hanging playback is only half true: with a playback in flight `docker stop` waits for it and is killed after the 10 s grace period (R-16). Still not run: `--device /dev/snd`, Linux, arm64 (postponed) and a real sound card in a container.

> **Update 2026-11-10 (stop):** the `docker stop` finding above (R-16) was fixed the same day with a 5 s graceful-shutdown timeout; with a 20 s playback in flight the stop now takes 5.73 s and exits with code 0.
