# ADR-008 — A new playback supersedes the running one

**Status:** Accepted (recorded 2026-11-05 from the code; the session token is in `SoundDeviceAudioPlayback`).

## Context

There is one output device. Brain may start a new utterance, or interrupt one, while the previous is still being played.

## Decision

One playback at a time. A new request cleans up the running session (its worker is cancelled), opens the device again and plays. The superseded request stops consuming its audio and ends with `completed` and the message `Playback session superseded by new request`. A session id (`object()`) is compared before the shared state is reset, so a playback that ran to the end reports `Playback session finalized successfully` (a bug of the first refactor reported "superseded" because the id was reset first).

## Consequences

- Positive: an interruption is immediate; no queue of utterances to manage here.
- Negative: any caller can interrupt the speech (R-8); the audio queued but not yet played by the superseded session is dropped.
