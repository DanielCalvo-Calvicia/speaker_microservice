# Decisions

Architecture decision records of the speaker. They were **written on 2026-11-05 from decisions already in force** (the workspace rules, the code and the commit history); the date of an ADR is when it was recorded, and the original date is given where the history shows it. A decision that changes gets a new dated update in its ADR; the body stays as history.

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](ADR-001-layered-architecture.md) | Layered structure shared by every service, with `sounddevice` behind a driver protocol | Accepted |
| [ADR-002](ADR-002-brain-is-the-only-caller.md) | Brain is the only caller; the speaker calls nobody | Accepted |
| [ADR-003](ADR-003-stream-contract-ndjson.md) | The playback request and its answer use the `contracts.stream` NDJSON events | Accepted |
| [ADR-004](ADR-004-no-authentication-common-middleware-later.md) | No authentication in this service; a common scheme for all services later | Accepted |
| [ADR-005](ADR-005-autoloader-removed.md) | The autoloader (the speaker pulling a stream by itself) is removed | Accepted |
| [ADR-006](ADR-006-audio-never-converted-resample-on-device-rejection.md) | Audio is never converted between services; resample only when the device rejects the rate | Accepted |
| [ADR-007](ADR-007-http-statuses-before-the-stream.md) | Natural HTTP statuses before the stream starts; `error` events after | Accepted |
| [ADR-008](ADR-008-new-playback-supersedes-the-running-one.md) | A new playback supersedes the running one | Accepted |
| [ADR-009](ADR-009-device-selection-order.md) | Device selection: index, keywords, OS default | Accepted |
| [ADR-010](ADR-010-shared-logging-and-config-from-environment.md) | `shared_logging` and configuration from environment variables | Accepted |
| [ADR-011](ADR-011-windows-speaker-runs-natively.md) | On Windows the speaker runs natively, not in Docker | Decided 2026-11-04; not implemented in the deploy tool |
