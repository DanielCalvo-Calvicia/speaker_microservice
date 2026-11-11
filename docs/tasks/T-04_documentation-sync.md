# T-04 — Documentation sync

| | |
|---|---|
| Status | recurring |
| Kind | docs |
| Depends on | the task being documented |
| Blocks | — |

## Goal

Keep the documents true to the repository after every task of T-01, T-02 and T-03: the table in `CLAUDE.md` is the day-to-day rule; this task is the checklist for a whole pass.

## Checklist after each task

| Trigger | Update |
|---|---|
| Any task done | its status in the board of [README.md](README.md) and in [ORDER.md](ORDER.md); `docs/risks/risks-and-debt.md` (the risk it closes); `docs/requirements/requirements.md` |
| A decision is taken | an ADR (ADR-012 for the null backend; a dated update of ADR-011 for Windows Docker) and its row in `docs/decisions/README.md`; the question in Q01 (the answer after `A:`) |
| A variable is added | `.env.example`, `README.md`, `docs/configuration/environment-variables.md`, `deployment/config/services/speaker.toml` (through `env_inventory.py --write`) and the speaker rows of `deployment/docs/DEPLOYMENT.md` |
| Code, a folder or a file name changes | `docs/architecture/architecture.md` (sections 3 and 4), the layout of `README.md` |
| A route, a response or an event changes | `docs/api/api.md`, `README.md`, `docs/requirements/requirements.md`, and `contracts` first |
| Logging, probes, shutdown | `docs/operations/monitoring.md` |
| Dependencies, the `contracts` wheel, the catalogue | `docs/deployment/deployment.md`, `requirements.*.txt`, `CLAUDE.md`; the wheel is 0.16.0 and the documents still say 0.15.0 (F3): fix them in the first task that touches the requirements |
| Test, ruff or mypy counts | `README.md` status line, `CLAUDE.md` (current state), `docs/requirements/requirements.md` (only after running them) |
| What was or was not run | the *Result* of the task and the *Verified* paragraph of `docs/deployment/deployment.md`; never write "works" for something that only ran against the fake driver or the null sink |

## Checks at the end of a pass

Every link in the edited documents resolves and every path named exists; the counts are the ones that were run; no secret and no recording in any document; `docs/old/` and `.engram/` untouched.
