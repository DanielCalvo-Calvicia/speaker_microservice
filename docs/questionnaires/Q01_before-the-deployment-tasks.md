# Q01 — Before the deployment tasks

**Answered by the maintainer on 2026-11-09: "Recommended" for all nine questions; processed into ADR-012 and the Resolution of T-01.1, T-01.5, T-01.6 and T-02.3.** (Original text follows.) Written on 2026-11-09 after the deployment audit ([../deployment_audit/speaker.md](../deployment_audit/speaker.md)) and the risk register ([../risks/risks-and-debt.md](../risks/risks-and-debt.md)) were checked against the code and the tests were run (facts F1 to F15 in [../tasks/README.md](../tasks/README.md)). The questions are the decisions that the code cannot settle; they are the same family as microphone's [Q02](../../../microphone_microservice/docs/questionnaires/Q02_deployment-readiness.md) (the switch, how the backend is reported, Docker on Windows, the way manual tasks run): answer both together, the answers should agree.

Write your answer after `A:` (English or Spanish); `[x]` marks a choice; `UNKNOWN`, `NOT APPLICABLE` and `LATER` are valid; **never write secrets**. Every question gives my **recommended** answer, so "Recommended" is a valid answer.

**Stops the chain:** 1 to 4 stop T-01.1 (and so T-01.2 to T-01.4, T-02.2, T-03.x); 5 stops T-01.5; 6 stops T-01.6. 7 to 9 only change how later tasks are run.

---

1. **The switch.** `SPEAKER_BACKEND=real|null`, **code default `real`** (a silent fake default would make a robot with a broken sound card look healthy), an unknown value stops the start naming the variable. The backend is chosen in the composition root **before** the `sounddevice` driver module is imported (F5), so a machine without PortAudio can run `null`. A machine without a sound card starts on `null` through a **catalogue preset** (`[services.speaker.env] SPEAKER_BACKEND = "null"`, like stepper's `MOCK_HARDWARE = "1"`), and the machine with the sound card sets `real` in `deployment/config/local/speaker.toml`.
   *Consequence to accept:* with the preset a default deploy of the speaker is `null`; if you forget `real` on the robot, the service is healthy and silent. The tool's `healthy and available, warning: <reason>` line (question 2) is the safety net.
   - [ ] as recommended (default `real`, preset `null` in the catalogue)
   - [ ] default `real` and **no** preset: a machine without a device sets `null` in its own local file
   *Recommended: the first.* (Same question as microphone Q02-1: answer both alike.)
   A:Recommended

2. **How the active backend is reported (R-4).** (a) In the `reason` of `GET /available` (what tts did, [tts ADR-008](../../../tts_microservice/docs/decisions/ADR-008-fallback-reported-in-available-reason.md)): `is_available` stays true, `reason` is a short note such as `null sink (SPEAKER_BACKEND=null): audio is discarded`, the real backend leaves it empty, no `contracts` change, and the deploy tool already prints `healthy and available, warning: <reason>`; the service also logs the backend once at start. (b) A new `backend` field in `AvailabilityResponse` in `contracts` (a version bump that every service re-bundles), which the audit preferred as "cleaner".
   *Recommended: (a).* Cost of (a) to know: Brain reads `reason` only when `is_available` is false, so Brain itself will not show it; cost of (b): a cross-repository change for a problem the existing field solves.
   A:Recommended

3. **Does the null sink pace itself to real time?** Facts read in Brain: its echo guard and speech cues are computed from the **bytes Brain sends** (`tts_to_speaker.py` calls `echo_guard.robot_speaks(now, seconds_of_audio)` and `speech_cues.began(...)`), not from when the speaker answers, so Brain does not need the null sink to take time. What pacing changes is when the speaker's `completed` event arrives and the realism of the stream: tts is faster than real time and Brain does not pace the stream, so a real device holds the request open for the whole duration (the R-6 situation) and a null sink that answers at once would hide timing problems. Options: (a) pace by default (sleep as long as the audio lasts: the drain wait of R-6 is then exercised too) with an env switch to run unpaced for fast tests; (b) never pace, answer as soon as the body ends.
   *Recommended: (a) pace by default; the null sink must in all cases drain the whole request stream (otherwise Brain's POST backs up).*
   A:Recommended

4. **Docker on a Windows host for an audio service.** The tool rejects `runtime = "docker"` for an audio service on Windows (`deployment/domain/rules/host_validation.py:18`). (a) Keep the rejection and document it, or implement the per-machine `mode = "local"` override of the decision of 2026-11-04 (ADR-011 here)? (b) May a service whose resolved backend is `null` run in Docker on Windows (a small change in `host_validation.py` and a test) so that the Docker acceptance on this PC can run through `oblivion.py`; otherwise it is run by hand with the tool's Dockerfile. This is **the same change as microphone T-06.4**: do it once for both.
   *Recommended: (a) keep the rejection and document it; (b) yes.* In both cases Docker is proven here only on `null`; the real device is proven natively on Windows; `/dev/snd` is Linux/Pi work and is postponed.
   A:Recommended

5. **Unused packages.** `numpy`, `soundfile` and `websockets` are in the runtime requirements but no production file imports them (`httpx` is used only by the tests); `libsndfile1` is in the catalogue `apt` list for `soundfile`. Drop them (and move `pytest`, `httpx` and the lint tools to a dev file), and pin the runtime packages the way stt did (exact `==` of the versions that ran: fastapi 0.136.1, uvicorn 0.47.0, python-dotenv 1.2.2, sounddevice 0.5.5)?
   *Recommended: drop all four, one `requirements-dev.txt` (as tts), exact pins of what ran.* Note: `numpy` is also in the microphone's runtime file, where it is used (the downmix); here it is not.
   A:Recommended

6. **When the drain bound is hit (R-6 open point).** After the fix the speaker waits the duration of the queued audio plus 2 s for the device to play it; if that bound is reached (a stalled device) it only logs a warning (`queued_bytes`, `written_bytes`) and answers `success: true`. Change it to `success: false` with a message?
   *Recommended: yes*, so a stalled device is not reported as success. Brain's reaction to `success: false` has not been checked; the task reads Brain's handling first and stops to ask if Brain would act badly on it (Brain is not edited in this plan).
   A:Recommended

7. **Backend of a `null` sink that records?** Do you want the null sink to keep the last played audio (for a test to read) or only count bytes? *Recommended: only counters in the log and no audio kept (nothing of anyone's voice stays in memory or on disk).*
   A:Recommended

8. **Lint and the register items that are not tasks.** R-7 (unbounded queue), R-8 (no auth, ADR-004), R-9 (CORS `*`), R-12 (8 ruff findings, 4 mypy errors), R-13 (stale material), R-14 (the unused `is_available()` name) and R-15 (the audit is untracked) are recorded as **accepted or postponed with a reason** (section 6 of the [tasks README](../tasks/README.md)), not built. The plan adds no lint finding and does not bulk-fix. Agree?
   *Recommended: yes.* (R-15: you decide when to commit the audit; I commit nothing unasked.)
   A:Recommended

9. **How the manual tasks run.** Tasks that play sound on the real speaker, build a Docker image or download something are `manual`. Same standing permission as stt/tts: you say "go" for **each** task, I say first what it does and costs, **I warn you before any sound is played (volume)**, you are at the PC for the audio ones, scratch folders are deleted at the end, ports 7998 to 8005 are free before and after. Order: microphone first, then speaker, in one session (both edit `deployment/config/catalogue.toml` and `deployment/docs/DEPLOYMENT.md`).
   *Recommended: yes to both.*
   A:Recommended
