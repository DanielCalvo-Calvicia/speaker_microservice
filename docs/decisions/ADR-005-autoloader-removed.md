# ADR-005 — The autoloader is removed

**Status:** Accepted (commit `eacddae`, 2026-09-20; recorded 2026-11-05).
**Related:** [ADR-002](ADR-002-brain-is-the-only-caller.md)

## Context

An earlier version had an autoloader: the speaker pulled an audio stream from another service by itself, which is a service-to-service call.

## Decision

It was removed on purpose. The speaker only plays what Brain sends to `POST /process/stream/set`. **Do not reintroduce it.** Its code is archived in `docs/old/autoloader/`. Some old `.env.example` comments and documents of other services may still mention autoloader stream URLs; they are stale.

## Consequences

- Positive: one direction of flow, from Brain to the speaker.
- Negative: none known.
