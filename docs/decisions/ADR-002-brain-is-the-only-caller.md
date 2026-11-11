# ADR-002 — Brain is the only caller

**Status:** Accepted (workspace rule, recorded 2026-11-05).

## Context

OBLIVION is a voice robot made of small HTTP services. If services called each other the pipeline would have no single place where its order, its timing and its failures are decided.

## Decision

Brain is the only coordinator. The speaker never calls another service and exposes nothing that another service needs besides Brain's playback request and the probes. No outbound HTTP exists in the code.

## Consequences

- Positive: the speaker can be tested alone; hosts and ports come from Brain's settings (`SPEAKER_BASE_URL`), never from this service.
- Negative: nothing in the service enforces who the caller is (see [ADR-004](ADR-004-no-authentication-common-middleware-later.md)).
