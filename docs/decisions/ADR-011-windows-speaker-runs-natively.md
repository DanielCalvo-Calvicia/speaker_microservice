# ADR-011 — On Windows the speaker runs natively, not in Docker

**Status:** Decided 2026-11-04 (recorded in the deployment audit, [`speaker.md`](../deployment_audit/speaker.md)); **not implemented** in the deploy tool.
**Related:** [deployment](../deployment/deployment.md), R-11

## Context

The sound card of a Windows host is not reachable from a Docker container. The deploy tool passes `--device /dev/snd` only on a Linux host, and today rejects a Docker speaker on Windows (`host_validation.py:18`).

## Decision

On a Windows host the speaker keeps a declared local override: `mode = "local"` with `reason = "Windows sound card"`, per machine. The same rule applies to the microphone.

## Consequences

- Positive: the layouts that put the speaker on a Windows PC stay valid.
- Negative: the deploy tool has no per-machine `mode` key yet; until it has, such a layout is refused. The change is in `deployment/`, not in this service.

> **Update 2026-11-09:** the maintainer decided (Q01-4) not to implement the per-machine `mode = "local"` override: the tool keeps rejecting `runtime = "docker"` for an audio service on a Windows host, except when the service's resolved backend is `null` (ADR-012), so the Docker acceptance can run on this PC. Not built yet (T-02.3).
