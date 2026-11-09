# ADR-004 — No authentication in this service; a common scheme later

**Status:** Accepted (commit `eacddae`, 2026-09-20; recorded 2026-11-05).

## Context

The first refactor gave the speaker a bearer-token check (`SPEAKER_API_KEY`, `http_auth.py`, `ApiKeyAuthenticator`). No other service had one, Brain sent no token, and a per-service scheme would have to be redone when a common one is designed.

## Decision

The check was removed and no variable of that name exists. A common authentication middleware for all the services is planned and not designed. **Do not build a scheme specific to the speaker.** Until then the network in front of the service is the only protection (see [security](../security/security.md)).

## Consequences

- Positive: one scheme later instead of six.
- Negative: whoever reaches the port can play audio and interrupt the speech (R-8).
- The old code is archived in `docs/old/auth/`.
