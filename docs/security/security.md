# Security

Only what can be verified in the repository. Labels: **Implemented** (in the code and tested), **Configured** (in a file, not run), **Required** (the operator must do it), **Recommended but not implemented**.

## Access to the service

- **Not implemented:** authentication and authorisation. The bearer-token check (`SPEAKER_API_KEY`, `http_auth.py`) was removed on purpose in commit `eacddae` (2026-09-20) and no variable of that name exists. Every service of the project is without authentication; a common middleware is planned for all of them. **Do not build a scheme specific to this service** ([ADR-004](../decisions/ADR-004-no-authentication-common-middleware-later.md)).
- **Consequence:** whoever can reach port 8003 can make the robot play any audio, and, because a new playback supersedes the running one, can interrupt Brain's speech. **Required:** the network in front of the service limits who can reach it; the default bind is `127.0.0.1`, and `0.0.0.0` is for a trusted network only.
- **Implemented:** only Brain is meant to call the service. Nothing in the code enforces it.
- **Implemented:** CORS from `ALLOWED_ORIGINS`; credentials are allowed only when the list is not `*`. The default `*` is open to any browser origin: **Recommended** to list the origins where a browser can reach the service.

## The request

- **Implemented:** the sample rate and channel count must be positive (`422` otherwise); a NDJSON body is decoded by the shared codec, which enforces the sequence rules; `bytes_base64` is decoded with `validate=True`; a stream that announces another format than the query is refused; invalid UTF-8 is refused. A refused body fails the playback with an `error` event, never a crash.
- **Not implemented:** a limit on the size or the duration of a request. The body is a stream that is played as it arrives; a caller can hold the device for as long as it sends audio. The queue between the reader and the device is unbounded, so a fast sender grows memory by the audio it sends ahead of the device (R-6, R-7 in [risks](../risks/risks-and-debt.md)).
- **Implemented:** an unhandled exception answers `{"message": "An internal error occurred"}` and logs only the type; the error text of a playback failure does reach the caller in the `error` event (device and driver messages).

## Data

- The service handles audio only in memory, for the time it takes to play it; it writes nothing to disk and logs only counts, never audio.
- The log line of a request holds the address of the caller.

## Secrets

- **Required:** none exists, and none is committed. `.env` is ignored by git (`.gitignore`); `.env.example` holds names and public defaults only.
- No document, test or example holds a secret value.

## The container

- No `Dockerfile` in this repository: the deploy tool builds and runs the service (`deployment/`). A Docker run on Linux passes `--device /dev/snd` for `audio = true` services; it does not add the `audio` group (not needed for a root container) and has never been run (unproven). On Windows the sound card is not reachable from Docker ([deployment](../deployment/deployment.md)).

## Supply chain

- `contracts` is the vendored wheel `vendor/contracts_microservice-0.15.0-py3-none-any.whl` (refreshed with `contracts/scripts/bundle.py`). `shared-logging` is a local checkout (`-e ../shared-logging`).
- The runtime requirements files list unpinned packages, including dev tools and packages the code does not import (R-5). No dependency scan is configured.
