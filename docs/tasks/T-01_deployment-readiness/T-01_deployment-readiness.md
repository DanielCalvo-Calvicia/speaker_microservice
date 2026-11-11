# T-01 — Deployment readiness of the service

| | |
|---|---|
| Status | done |
| Kind | epic |
| Depends on | — |
| Blocks | T-02, T-03 |

## Goal

Make the speaker deployable on a machine **without** a sound card and without PortAudio, say which backend is active, keep the install small and reproducible, and re-prove the real device on Windows. Today the process does not start without an output device (F6), imports `sounddevice` at module level (F5), lists packages it does not use (F4) and cannot say which backend it runs (F7).

## History (not a task): R-6, the end of a playback

Built and confirmed on 2026-11-09 (commit `49e26b3`, 8 new tests, 9 of 9 one-line mutations caught, 92 tests): the wait for the device to finish is now the duration of the queued audio plus 2 s instead of a fixed 3 s, so a reply longer than 3 s is no longer cut. Seen on the real device: a 7.12 s sentence written in full, the maintainer heard all three test sentences. Recorded in the register ([R-6](../../risks/risks-and-debt.md)) and in F8. Open point: [T-01.6](T-01.6_drain-bound-answers-failure.md).

## Subtasks

| Order | Task | Kind | State |
|---|---|---|---|
| 1 | [T-01.1 Decisions: switch, report, pacing](T-01.1_decisions.md) | decision | awaiting-user |
| 2 | [T-01.2 `SPEAKER_BACKEND` and the lazy import of the driver](T-01.2_backend-switch-lazy-import.md) | code | blocked |
| 3 | [T-01.3 The null sink: drain and pace](T-01.3_null-sink.md) | code | blocked |
| 4 | [T-01.4 Report the active backend in `/available` and the log](T-01.4_report-the-backend.md) | code | blocked |
| 5 | [T-01.5 Split the requirements, drop the unused ones, pin](T-01.5_requirements.md) | code | awaiting-user |
| 6 | [T-01.6 A drain bound that is hit answers `success: false`](T-01.6_drain-bound-answers-failure.md) | code | awaiting-user |
| 7 | [T-01.7 Retest on the real device](T-01.7_hardware-retest.md) | manual | todo |
| 8 | [T-01.8 Device keywords on Linux](T-01.8_device-keywords-on-linux.md) | manual | postponed |

## Exit criteria

With `SPEAKER_BACKEND=null` the service starts with no sound card and with `sounddevice` made unimportable, answers `/health`, `/ready` and `/available` (with the reason that says `null`), drains and paces the stream and returns the same NDJSON events as the real backend; with the variable unset it behaves as before (the old tests unchanged and green); the runtime requirements hold only what the service imports, with exact pins; the real device was retested on Windows; the documents of the table in `CLAUDE.md` are true again; no new ruff or mypy finding (F2).
