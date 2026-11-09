# ADR-010 — `shared_logging` and configuration from environment variables

**Status:** Accepted (workspace rules; recorded 2026-11-05).
**Related:** [ADR-001](ADR-001-layered-architecture.md)

## Context

The first refactor had a custom logger with per-environment levels and the parsing of VS Code launch profiles, and read `APP_ENV`. Hosts and ports must never be assumed: the services run on different machines.

## Decision

Logging is `shared_logging` only (`init_logging("speaker")` in `main_flow/http.py`, `get_logger(__name__)` elsewhere; the stdlib `logging` is never imported in service code); messages are constant strings with keyword fields; `LOG_LEVEL` decides, `APP_ENV` is no longer read; `TracingMiddleware` is the outermost middleware. Configuration comes from environment variables (a `.env` file is loaded if present), read once into frozen dataclasses (`ServerConfig`, `SpeakerConfig`), documented in `.env.example` and in [environment-variables](../configuration/environment-variables.md). Ports are never hardcoded outside the default.

## Consequences

- Positive: the same logging and trace correlation in every service; one list of variables to keep true.
- Negative: `.env.example` changes need the deploy tool's settings file regenerated (`deployment/scripts/env_inventory.py --write`).
