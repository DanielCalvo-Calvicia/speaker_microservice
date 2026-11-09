# ADR-001 — Layered structure shared by every service

**Status:** Accepted (recorded 2026-11-05; the layout was adopted in the refactor that followed `microphone_microservice`, see `docs/old/pattern_comparison_speaker.md`).
**Related:** [ADR-010](ADR-010-shared-logging-and-config-from-environment.md)

## Context

The services of OBLIVION are small and were written one by one with different layouts. The workspace rule is one structure everywhere so that a change in one service is readable in the others.

## Decision

`main.py` → `main_flow/` → `composition_root/` → `application/` → `domain/` → `infrastructure/`; dependencies point inward only (`infrastructure → application → domain`). The composition root is the only place where concrete adapters are chosen. The application layer owns the ports (`SpeakerPlaybackPort` driving, `AudioPlaybackPort` driven). `sounddevice` sits behind an `AudioDriver` protocol and a `DeviceSelector`; `sounddevice_driver.py` is the only module that imports it, so the adapter is tested against a fake driver. Blocking driver calls run through `asyncio.to_thread`. `tests/architecture/test_dependency_rules.py` enforces the rule by parsing the imports.

## Consequences

- Positive: no hardware needed for the 84 tests; the hardware can be replaced (a null sink, FR-15) by a new adapter without touching the application.
- Negative: `sounddevice_driver.py` is still imported at module level by the composition root, so a machine without PortAudio cannot start the service (R-2).
