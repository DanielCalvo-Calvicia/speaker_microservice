# Task order

The order in which the tasks must be done, with the state of each one and the date its file was last updated. It follows the execution protocol of the [tasks README](README.md) (section 2): the first task that is `todo` and whose dependencies are `done`. Decisions that stop the chain are marked.

**Keep this file true:** every change to a task (a status, a dependency, a new task, an order change) updates this table, the board of the [tasks README](README.md) section 5 and the task file itself (see `CLAUDE.md` at the root of the repository). The *Last updated* column is the date of the last change to the task file and is refreshed by the same change.

## States

| State | Meaning |
|---|---|
| Done | Implemented and verified (or, for a decision, taken and recorded) |
| In progress | Some of its sub-tasks are done and some are not |
| Todo | Ready to start when its dependencies are done |
| Awaiting user | A decision needs the maintainer's answer; it stops the tasks that depend on it |
| Blocked | Waits, directly or through other tasks, for a decision |
| Postponed | Decided not to run yet (Raspberry Pi, arm64 and native Linux wait until the services work at 100 % on Windows, 2026-11-09); it does not block the Windows work |
| Recurring | Repeated after every big task |

Written on 2026-11-09 from the deployment audit and the risk register. Nothing is done. Everything that can run on Windows is done (T-01.7 was run with the maintainer on 2026-11-10); the postponed tasks (T-01.8, T-03.5) wait for Linux or the Raspberry Pi. Decisions that stop the chain: **T-01.1** (Q01-1 to Q01-4 and Q01-7), **T-01.5** (Q01-5), **T-01.6** (Q01-6) and **T-02.3** (Q01-4, together with microphone T-06.4). The microphone plan is done first (both edit `deployment/config/catalogue.toml` and `docs/DEPLOYMENT.md`).

## A. Deployment readiness of the service (T-01)

| # | Task | Name | Kind | State | Detail | Depends on | Last updated |
|---|---|---|---|---|---|---|---|
| 1 | [T-01](T-01_deployment-readiness/T-01_deployment-readiness.md) | Deployment readiness of the service | epic | Done | R-6 is built (history); the rest below | — | 2026-11-10 |
| 2 | [T-01.1](T-01_deployment-readiness/T-01.1_decisions.md) | Decisions: switch, report, pacing | decision | Done | Q01-1 to Q01-4, Q01-7; stops T-01.2 to T-01.4 | — | 2026-11-09 |
| 3 | [T-01.2](T-01_deployment-readiness/T-01.2_backend-switch-lazy-import.md) | `SPEAKER_BACKEND` and the lazy import of the driver | code | Done | R-1, R-2; ADR-012 | T-01.1 | 2026-11-10 |
| 4 | [T-01.3](T-01_deployment-readiness/T-01.3_null-sink.md) | The null sink: drain and pace | code | Done | R-1 | T-01.2 | 2026-11-10 |
| 5 | [T-01.4](T-01_deployment-readiness/T-01.4_report-the-backend.md) | Report the active backend in `/available` and the log | code | Done | R-4 | T-01.3 | 2026-11-10 |
| 6 | [T-01.5](T-01_deployment-readiness/T-01.5_requirements.md) | Split the requirements, drop the unused ones, pin | code | Done | R-5; Q01-5; can start as soon as answered | — | 2026-11-10 |
| 7 | [T-01.6](T-01_deployment-readiness/T-01.6_drain-bound-answers-failure.md) | A drain bound that is hit answers `success: false` | code | Done | R-6 open point; Q01-6 | — | 2026-11-10 |
| 8 | [T-01.7](T-01_deployment-readiness/T-01.7_hardware-retest.md) | Retest on the real device | manual | Done | R-10; *needs the maintainer*; plays sound | — | 2026-11-10 |
| 9 | [T-01.8](T-01_deployment-readiness/T-01.8_device-keywords-on-linux.md) | Device keywords on Linux | manual | Postponed | R-3; Linux work | — | 2026-11-09 |

## B. Deployment tool changes (T-02, the `deployment` repository)

| # | Task | Name | Kind | State | Detail | Depends on | Last updated |
|---|---|---|---|---|---|---|---|
| 10 | [T-02](T-02_deployment-tool-changes/T-02_deployment-tool-changes.md) | Deployment tool changes | epic | Done | after the microphone's T-06 | T-01.1 | 2026-11-10 |
| 11 | [T-02.1](T-02_deployment-tool-changes/T-02.1_catalogue-entry.md) | The speaker catalogue entry | code | Done | drop `libsndfile1`, the `null` preset | T-01.2, T-01.5 | 2026-11-10 |
| 12 | [T-02.2](T-02_deployment-tool-changes/T-02.2_readiness-without-a-device.md) | Readiness on a machine without a sound card | code | Done | tests of the tool; `real` without a device still fails | T-02.1, T-01.4 | 2026-11-10 |
| 13 | [T-02.3](T-02_deployment-tool-changes/T-02.3_docker-on-windows-with-null.md) | Docker on Windows for a speaker on `null` | decision + code | Done | R-11; Q01-4; one change with microphone T-06.4 | T-02.1 | 2026-11-10 |
| 14 | [T-02.4](T-02_deployment-tool-changes/T-02.4_inventory-and-manual.md) | Inventory and manual | docs | Done | `env_inventory.py`, `DEPLOYMENT.md` | T-02.1 | 2026-11-10 |

## C. Docker and arm64 acceptance (T-03)

| # | Task | Name | Kind | State | Detail | Depends on | Last updated |
|---|---|---|---|---|---|---|---|
| 15 | [T-03](T-03_docker-and-arm64-acceptance/T-03_docker-and-arm64-acceptance.md) | Docker and arm64 acceptance | epic | Done | Docker only on `null` on this PC | T-01, T-02 | 2026-11-10 |
| 16 | [T-03.1](T-03_docker-and-arm64-acceptance/T-03.1_amd64-build.md) | Build the image on amd64 | manual | Done | | T-02.1, T-01.5 | 2026-11-10 |
| 17 | [T-03.2](T-03_docker-and-arm64-acceptance/T-03.2_run-and-call.md) | Run the container on `null` and call every endpoint | manual | Done | | T-03.1, T-02.2 | 2026-11-10 |
| 18 | [T-03.3](T-03_docker-and-arm64-acceptance/T-03.3_restart-recreate-stop.md) | Restart, recreate and `docker stop` | manual | Done | | T-03.2 | 2026-11-10 |
| 19 | [T-03.4](T-03_docker-and-arm64-acceptance/T-03.4_image-contents-and-secrets.md) | Image contents and secrets | manual | Done | | T-03.1 | 2026-11-10 |
| 20 | [T-03.5](T-03_docker-and-arm64-acceptance/T-03.5_docker-with-dev-snd-and-arm64.md) | Docker with `/dev/snd`, and on arm64 | manual | Postponed | needs a Linux host or the Pi | T-03.3 | 2026-11-09 |
| 21 | [T-03.6](T-03_docker-and-arm64-acceptance/T-03.6_record-the-results.md) | Record what was verified | docs | Done | | T-03.2, T-03.3, T-03.4 | 2026-11-10 |

## D. Recurring

| # | Task | Name | Kind | State | Detail | Depends on | Last updated |
|---|---|---|---|---|---|---|---|
| 22 | [T-04](T-04_documentation-sync.md) | Documentation sync | docs | Recurring | after T-01, T-02 and T-03 | — | 2026-11-09 |

## What can run in parallel

T-01.5 (requirements), T-01.6 (the drain answer) and T-01.7 (the hardware retest) do not depend on each other or on the backend work; the backend chain T-01.1 → T-01.2 → T-01.3 → T-01.4 is sequential (same files). T-02.x needs the service tasks it names.
