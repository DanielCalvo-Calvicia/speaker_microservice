# T-02 — Deployment tool changes (the `deployment` repository)

| | |
|---|---|
| Status | done |
| Kind | epic |
| Depends on | T-01.1 (each leaf names its own other dependencies) |
| Blocks | T-03 |

## Goal

Change the deployment tool and its catalogue so that the speaker can be deployed on a machine without a sound card and proven so, without the package it never needed, and so that the manual says the same as the catalogue. Today the process does not start without a device (F6), the catalogue installs `libsndfile1` for nothing (F10) and a layout with a Docker speaker on Windows is refused (F11).

## Rules for this epic

- `deployment` is its own repository with its own `CLAUDE.md`: **read `deployment/CLAUDE.md` before editing anything** (layered layout, every external command through `Shell`, dry-run without side effects, tests for the install path, `docs/DEPLOYMENT.md` in step with each `.env.example`).
- The edits are made in `D:\Hobbys\IA\OBLIVION\deployment`, not in this repository. Do not commit or push in either repository unless asked.
- The microphone plan (epic T-06 there) edits the same `config/catalogue.toml` and `docs/DEPLOYMENT.md`, and its T-06.4 is the same decision as [T-02.3](T-02.3_docker-on-windows-with-null.md): microphone first; read `git status` and `git diff` of a file before editing it and keep to your own lines (F14).
- The deployment tests run with the brain venv from `deployment/`, in the background (about 190 s): `..\brain_microservice\windows\Scripts\python.exe -m pytest tests -q`. They use the fake `Shell` and `--dry-run`: no image is built here (that is T-03). Never touch `deployment/config/local/`; use `--config <a throw-away folder>`.

## Subtasks

| Order | Task | Kind | State |
|---|---|---|---|
| 1 | [T-02.1 The speaker catalogue entry](T-02.1_catalogue-entry.md) | code | blocked |
| 2 | [T-02.2 Readiness on a machine without a sound card](T-02.2_readiness-without-a-device.md) | code | blocked |
| 3 | [T-02.3 Docker on Windows for a speaker on `null`](T-02.3_docker-on-windows-with-null.md) | decision + code | awaiting-user |
| 4 | [T-02.4 Inventory and manual](T-02.4_inventory-and-manual.md) | docs | blocked |

## Exit criteria

The speaker entry has no `libsndfile1` and (if Q01-1 says so) the `null` preset; a layout with the speaker on `null` passes the readiness check without a device and the tool prints the reason; `real` without a device still fails; `env_inventory.py --check` passes; `deployment/docs/DEPLOYMENT.md`, `deployment/CLAUDE.md` and `docs/deployment/deployment.md` of this repository say the same; the deployment suite passes.
