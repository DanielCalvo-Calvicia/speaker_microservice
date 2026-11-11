# Tasks

Hierarchical task plan to make the **new deployment of `speaker_microservice`** work and prove it, in the format of the stt and tts deployment plans: **T-01 deployment readiness of the service, T-02 changes in the deployment tool (the `deployment` repository), T-03 Docker and arm64 acceptance, T-04 documentation sync**. It was generated on 2026-11-09 from the deployment audit ([../deployment_audit/speaker.md](../deployment_audit/speaker.md), a snapshot of 2026-11-04) and the risk register ([../risks/risks-and-debt.md](../risks/risks-and-debt.md), R-1 to R-15); every claim it relies on was read in the code or run on 2026-11-09 (section 4). It is written to be executed step by step by the assistant: every leaf task states what to change, what it must not do, and how to prove it is done.

The status of every task is on the board in section 5; the order, with state and date, is in [ORDER.md](ORDER.md) (kept in step with the board and with every task file).

**Plan revision 1 (2026-11-09):** first version. No code task is done. Four decisions in [Q01](../questionnaires/Q01_before-the-deployment-tasks.md) stop the chain ([T-01.1](T-01_deployment-readiness/T-01.1_decisions.md), [T-01.5](T-01_deployment-readiness/T-01.5_requirements.md), [T-01.6](T-01_deployment-readiness/T-01.6_drain-bound-answers-failure.md) and [T-02.3](T-02_deployment-tool-changes/T-02.3_docker-on-windows-with-null.md) are `awaiting-user`). The fix of R-6 (the drain wait) is already built and confirmed on the real device on 2026-11-09 (commit `49e26b3`); it is recorded as history, not as a task. The Raspberry Pi, arm64 and native Linux are `postponed` until the services work at 100 % on Windows (the maintainer's decision of 2026-11-09). Written together with the microphone plan (`microphone_microservice/docs/tasks/`), which is done first.

## 1. Structure and naming

- Every task is a Markdown file. A task with subtasks lives in a folder of the same name, and its own file has the same name inside that folder. Leaves are single files.
- IDs are hierarchical and stable: `T-01` -> `T-01.2`. Never reuse or renumber an ID.
- A parent task describes goal, order and exit criteria; **leaves carry the detail**. Every task file starts with the same header table (`Status`, `Kind`, `Parent`, `Depends on`, `Blocks`, `Size`) and has the sections *Goal*, *Read first*, *Files*, *Specification* or *Steps*, *Acceptance criteria*, *Verification* and *Notes*; a *Result* section is added when it is done, with what was really run.

```
docs/tasks/
├── README.md                          (this file)
├── ORDER.md                           the order, the state and the date of every task
├── T-01_deployment-readiness/         epic 1 (this repository)
├── T-02_deployment-tool-changes/      epic 2 (the `deployment` repository)
├── T-03_docker-and-arm64-acceptance/  epic 3
└── T-04_documentation-sync.md         recurring
```

Kinds: `code`, `test`, `decision`, `docs`, `manual` (needs a real speaker, a Docker build, a download or a person). **Anything that plays sound is manual: say before it plays and wait for "go".**

## 2. Execution protocol

1. Pick the first task whose status is `todo` and whose `Depends on` tasks are all `done`. A decision that is `awaiting-user` **stops the chain** for the tasks that depend on it: ask the maintainer, record the answer in the task's *Notes* and in Q01, then continue.
2. Read the files listed in *Read first*, and the `CLAUDE.md` of the repository you are about to edit (`speaker_microservice`, including its rule that every change updates its documents; `deployment/CLAUDE.md` for T-02).
3. Create or modify only the files listed under *Files* (tests included). Another file, dependency or folder requires updating the task first.
4. **Code tasks:** when a defect is fixed, write the test first and show it fails on the old code; then the change; then one-line mutations of the new code with a script that restores the file in a `finally` (aim for all caught; a missed mutation shows a missing test or dead code). Run the task's *Verification* and the baseline of section 3.
5. Set the task's `Status` to `done`, update its row on the board and in [ORDER.md](ORDER.md), update the parent if its exit criteria are met, record any new fact in *Notes* and write a *Result* with numbers.
6. Update the documents the change touches in the same piece of work (the table of `CLAUDE.md`), including `docs/risks/risks-and-debt.md`.
7. Do not commit, push or publish unless the maintainer asks. Do not run anything that plays sound, builds an image, downloads something or reaches another machine without saying so first and waiting for "go" for that task (proposed in Q01-9). Never `git stash`, `reset` or `checkout` to compare with a baseline: use `git diff`, `git show HEAD:<file>` or a scratch copy.
8. Never open a `.env` file and never print a secret.

Status values: `todo`, `awaiting-user`, `blocked` (waits, directly or through other tasks, for a decision), `in-progress`, `done`, `postponed` (decided not to run yet; it does not block the Windows work).

## 3. Baseline definition of done (applies to every code or test task)

- `windows\Scripts\python.exe -m pytest` passes from `speaker_microservice` (**92 passed** on 2026-11-09; a task that adds tests raises the number, and the new count goes into the status line of `README.md`, `CLAUDE.md` and `docs/requirements/requirements.md`).
- Tests live under `tests/`, mirroring the layer they cover (`application`, `domain`, `infrastructure`, `composition_root`, `architecture`); they need no sound card, no network and no PortAudio (fakes, `monkeypatch`: the driver is faked as `tests/composition_root/test_http_container.py` does by patching `speaker_dependencies.SoundDeviceDriver`). The test folders have no `__init__.py`: do not add any. `tests/architecture/test_dependency_rules.py` stays green: dependencies point inward only, only `sounddevice_driver.py` imports `sounddevice`.
- Logging only through `shared_logging` (`get_logger(__name__)`), constant message strings with keyword fields; never stdlib `logging`. Never log audio.
- Settings only from environment variables, documented in `.env.example`; after any `.env.example` change run `brain_microservice\windows\Scripts\python.exe deployment\scripts\env_inventory.py --write` from the workspace root and `--check` from `deployment/` (read `git status` of `deployment` first, F14).
- Audio is never converted between services; the only conversion here is the device-rate resample (ADR-006).
- No `contracts` change is planned (Q01-2 recommends the `reason` of `/available`). If a task needs one, contracts goes first, with a version bump, then every service re-bundles.
- **Lint:** ruff and mypy are not installed in this venv; run them with the microphone venv (`..\microphone_microservice\windows\Scripts\ruff.exe check .` and `..\microphone_microservice\windows\Scripts\python.exe -m mypy .` from this folder). Today **8 ruff findings (4 fixable) and 4 mypy errors** are known (R-12): a task adds **none** and does not bulk-fix them; compare the counts before and after.
- No secrets in code, tests, fixtures or documents. The documents the change touches are updated in the same change and their links still resolve.
- Search only inside the service and exclude `windows/` and the cache folders. Never grep the whole workspace. Most files are LF here (`file` tells you); keep the line endings of the file you edit.

## 4. Facts the tasks rely on

Verified on 2026-11-09 against the code (`[C]`) or by running something (`[D]`); `[U]` not verified. Nothing was deployed, built or downloaded; no sound was played.

| # | Fact |
|---|---|
| F1 | The repository is on `feature_ai_claude_2`, HEAD `49e26b3` "Speaker: wait for the duration of the queued audio instead of a fixed 3 s (R-6)"; the working tree was clean when the plan was written (the docs of 2026-11-05 are committed too; `docs/deployment_audit/` is therefore no longer untracked, R-15 is out of date). `pytest`: **92 passed** in 6.8 s (`[D]`). The audit says 84 tests, `CLAUDE.md` is from 2026-11-05. After the work of 2026-11-10: **120 passed**, ruff 7 findings (4 fixable), mypy the same 4 errors (47 files before, 49 now). |
| F2 | `ruff check .` (microphone venv) reports **8 findings, 4 fixable** (`http_handler.py:4` unused `time`, line lengths in `http_handler.py` and `ndjson_events.py`, import order in three test files) and `mypy .` reports **4 errors in 3 files** (47 files: `resample.py` 31 and 50, `ndjson_events.py:48`, `ndjson_audio_decoder.py:47`) (`[D]`). The speaker venv has neither tool. |
| F3 | `vendor/` holds `contracts_microservice-0.16.0-py3-none-any.whl` and both requirements files name it, but `CLAUDE.md`, the README and other documents say 0.15.0 and the **venv has `contracts-microservice 0.15.0`** installed: the venv was not refreshed (`[C]`, `[D]`). |
| F4 | `requirements.windows.txt` and `requirements.linux.txt` differ only by a comment: runtime `fastapi`, `uvicorn`, `python-dotenv`, `httpx`, `sounddevice`, `soundfile`, `numpy`, `websockets`, **`pytest`, `ruff`, `black`, `mypy`**, `-e ../shared-logging`, the vendored wheel; all unpinned. A search of `application/ domain/ infrastructure/ composition_root/ main_flow/` finds **no** import of `numpy`, `soundfile` or `websockets`; `httpx` is only for tests (`[C]`). The venv (Python 3.14.2) has fastapi 0.136.1, uvicorn 0.47.0, python-dotenv 1.2.2, sounddevice 0.5.5, numpy 2.4.5, soundfile 0.13.1, websockets 16.0, httpx 0.28.1 and pytest 9.0.3 installed, and no ruff, black or mypy (`pip list`, `[D]`). |
| F5 | `sounddevice` is imported at module level only in `infrastructure/outbound/sounddevice_playback/sounddevice_driver.py`, and `composition_root/dependencies/speaker_dependencies.py` imports `SoundDeviceDriver` at the top of the module, so importing the composition root needs PortAudio (on Windows the wheel carries it; on Linux it needs `libportaudio2`). `tests/composition_root/test_http_container.py` replaces `speaker_dependencies.SoundDeviceDriver` with a fake (`[C]`). |
| F6 | **No device, no process:** `SoundDeviceAudioPlayback.__init__` calls `selector.select()` and raises `SpeakerUnavailable("sounddevice bootstrap failed: ...")` while `new_http_container` builds the app, before uvicorn runs; there is no null sink. `/available` therefore never answers false (`[C]`; R-1). |
| F7 | `GET /available` and `GET /ready` call `check_readiness()`, which probes `device_info(device_index)` without opening a stream: `is_available`/`is_ready` true and `reason`/`pending_reason` empty on success, false with the text otherwise (`http_handler.py:59-72`, `sounddevice_audio_playback.py:181`). `AvailabilityResponse` has only `is_available` and `reason` (`[C]`). |
| F8 | R-6 built (commit `49e26b3`): the end of a playback waits `queued_bytes / (rate * channels * 2) + 2.0` s (`_drain_timeout_seconds`, `_DRAIN_MARGIN_SECONDS`); a playback that reaches the bound logs the warning `Playback queue cleanup timed out; truncating` and still returns `success=True, message="Playback session finalized successfully"` (`sounddevice_audio_playback.py`, lines about 150 and 170). Confirmed on the real device on 2026-11-09 (7.12 s reply written in full, maintainer heard all three sentences). `[C]`, from R-6 |
| F9 | Brain computes the echo guard and the speech cues from the **audio it sends** (`tts_to_speaker.py`: `echo_guard.robot_speaks(now, len(encoded_audio) * 3 / 4 / bytes_per_second)`, `speech_cues.began(...)`), not from the speaker's answer; so a null sink does not need to take time for Brain's logic. Pacing changes only when the speaker's `completed` arrives and how realistic the stream is (Q01-3). `[C]` |
| F10 | `[services.speaker]` in `deployment/config/catalogue.toml`: port 8003, `ready = "/available"`, `audio = true`, `libraries = ["shared-logging"]`, requirements windows/linux, `apt = ["libportaudio2", "portaudio19-dev", "libsndfile1"]`, `dotenv` default `true` (the service loads its `.env`: `main_flow/http.py` calls `load_dotenv(find_dotenv(".env"))`), no `[env]` preset, no `prepare` (`[C]`). The audit's remark about `libsndfile1` is right: nothing imports `soundfile`. |
| F11 | `deployment/domain/rules/host_validation.py:18` rejects `runtime = "docker"` for an `audio` service on a Windows host; `docker_runtime.py:69` adds `--device /dev/snd` for an `audio` service on a Linux host. Both look at the catalogue flag, not at the backend. There is no per-machine `mode` key (ADR-011 here names it as a decision). `[C]` |
| F12 | The deployment tool waits for `/available` (`UNAVAILABLE_GRACE_SECONDS` = 15 s for a service that answers but is unavailable; a service that does not answer at all just fails the wait), and since tts it prints `healthy and available, warning: <reason>` when an available service carries a `reason` (`deployment/CLAUDE.md`, tts ADR-008). Brain's start-up preflight needs the speaker. `[C]` |
| F13 | Device keywords: the default `i2s,hw,default,sysdefault` is ALSA/Pi flavoured; on the Windows PC checked (Realtek, Bluetooth headsets, Voicemod) no output device name contains one, so the selector falls back to the OS default output, which works (confirmed on the real device on 2026-11-09, output device 3). On Linux `hw` or `default` can match the first ALSA device (HDMI) before the wanted one. `[C]` from the audit, `[D]` for Windows |
| F14 | The `deployment` repository holds no uncommitted work now (HEAD `abf0815`); the microphone plan edits `config/catalogue.toml` and `docs/DEPLOYMENT.md` first: read `git status` and `git diff` of a file before editing it and keep to your own lines. `[D]` |
| F15 | Docker Desktop 29.5.2 is running on this PC (`desktop-linux`, linux/amd64); every command needs `--context desktop-linux`. Docker on a Windows host cannot reach the sound card, so a container of the speaker can only run on `null` here. `[D]` |
| F16 | The shutdown path by reading: `python main.py` as PID 1 gets SIGTERM, uvicorn stops, the lifespan calls `stop_playback()` (idempotent) and `main_flow` cleans up; no Docker run has ever shown it. `[C]`, `[U]` for Docker |

## 5. Status board

| ID | Task | Kind | Status |
|---|---|---|---|
| [T-01](T-01_deployment-readiness/T-01_deployment-readiness.md) | **Deployment readiness of the service** (epic) | epic | done |
| [T-01.1](T-01_deployment-readiness/T-01.1_decisions.md) | Decisions: switch, report, pacing (Q01-1 to Q01-4, Q01-7) | decision | done |
| [T-01.2](T-01_deployment-readiness/T-01.2_backend-switch-lazy-import.md) | `SPEAKER_BACKEND` and the lazy import of the driver (R-1, R-2) | code | done |
| [T-01.3](T-01_deployment-readiness/T-01.3_null-sink.md) | The null sink: drain and pace (R-1) | code | done |
| [T-01.4](T-01_deployment-readiness/T-01.4_report-the-backend.md) | Report the active backend in `/available` and the log (R-4) | code | done |
| [T-01.5](T-01_deployment-readiness/T-01.5_requirements.md) | Split the requirements, drop the unused ones, pin (R-5) | code | done |
| [T-01.6](T-01_deployment-readiness/T-01.6_drain-bound-answers-failure.md) | A drain bound that is hit answers `success: false` (R-6 open point) | code | done |
| [T-01.7](T-01_deployment-readiness/T-01.7_hardware-retest.md) | Retest on the real device (R-10) | manual | done |
| [T-01.8](T-01_deployment-readiness/T-01.8_device-keywords-on-linux.md) | Device keywords on Linux (R-3) | manual | postponed |
| [T-02](T-02_deployment-tool-changes/T-02_deployment-tool-changes.md) | **Deployment tool changes** (the `deployment` repository) | epic | done |
| [T-02.1](T-02_deployment-tool-changes/T-02.1_catalogue-entry.md) | The speaker catalogue entry: no `libsndfile1`, the `null` preset | code | done |
| [T-02.2](T-02_deployment-tool-changes/T-02.2_readiness-without-a-device.md) | Readiness on a machine without a sound card | code | done |
| [T-02.3](T-02_deployment-tool-changes/T-02.3_docker-on-windows-with-null.md) | Docker on Windows for a speaker on `null` (R-11; with microphone T-06.4) | decision + code | done |
| [T-02.4](T-02_deployment-tool-changes/T-02.4_inventory-and-manual.md) | Inventory and manual | docs | done |
| [T-03](T-03_docker-and-arm64-acceptance/T-03_docker-and-arm64-acceptance.md) | **Docker and arm64 acceptance** | epic | done |
| [T-03.1](T-03_docker-and-arm64-acceptance/T-03.1_amd64-build.md) | Build the image on amd64 | manual | done |
| [T-03.2](T-03_docker-and-arm64-acceptance/T-03.2_run-and-call.md) | Run the container on `null` and call every endpoint | manual | done |
| [T-03.3](T-03_docker-and-arm64-acceptance/T-03.3_restart-recreate-stop.md) | Restart, recreate and `docker stop` | manual | done |
| [T-03.4](T-03_docker-and-arm64-acceptance/T-03.4_image-contents-and-secrets.md) | Image contents and secrets | manual | done |
| [T-03.5](T-03_docker-and-arm64-acceptance/T-03.5_docker-with-dev-snd-and-arm64.md) | Docker with `/dev/snd`, and on arm64 | manual | postponed |
| [T-03.6](T-03_docker-and-arm64-acceptance/T-03.6_record-the-results.md) | Record what was verified | docs | done |
| [T-04](T-04_documentation-sync.md) | **Documentation sync** (recurring) | docs | recurring |

## 6. Where every risk of the register went

| Risk | Disposition |
|---|---|
| R-1 no device, no process | T-01.2 (switch), T-01.3 (null sink), T-02.2 (readiness) |
| R-2 `sounddevice` imported at module level | T-01.2 (lazy import) |
| R-3 device keywords on Linux | T-01.8, **postponed** (Linux); Windows needs nothing (F13) |
| R-4 `/available` cannot say the backend | T-01.4 (in the `reason`, Q01-2) |
| R-5 unused and dev packages, unpinned, `libsndfile1` | T-01.5 and T-02.1 |
| R-6 drain bound | **done 2026-11-09** (history); the open point is T-01.6 |
| R-7 unbounded queue and body | **accepted**: only Brain calls it; revisit if another caller appears (Q01-8) |
| R-8 no auth, a new request supersedes | **accepted**: ADR-004, ADR-008, network limits (Q01-8) |
| R-9 CORS `*` | **accepted**: Brain is a server-side caller; list origins when a browser calls it (Q01-8) |
| R-10 hardware not retested | T-01.7 (the drain fix was confirmed on 2026-11-09; the rest of `tests/simple.py` and the device-rate resampling are not) |
| R-11 Docker on Windows rejected | T-02.3 (decision, with microphone T-06.4) |
| R-12 lint (8 ruff, 4 mypy) | **accepted**: no new finding, no bulk fix (Q01-8) |
| R-13 stale material | **accepted**: archives, not touched (Q01-8) |
| R-14 `is_available()` name | **accepted**: rename when the port is next changed (a rename would touch the port; not needed for deployment) |
| R-15 audit untracked | **out of date**: the audit is committed (F1); nothing to do |
