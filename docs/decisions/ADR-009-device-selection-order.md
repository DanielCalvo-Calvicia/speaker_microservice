# ADR-009 — Device selection: index, keywords, OS default

**Status:** Accepted (recorded 2026-11-05 from the code, `DeviceSelector`). The proposal to move the choice into the per-machine hardware configuration is FR-17, not decided.

## Context

The service runs on a Windows PC and on a Raspberry Pi (I2S, USB or the board's own output), where the device names differ.

## Decision

`SPEAKER_DEVICE_INDEX` wins when set. Otherwise the first output device (one with output channels) whose name contains any word of `SPEAKER_DEVICE_KEYWORDS` (default `i2s,hw,default,sysdefault`, case-insensitive) is used. Otherwise the OS default output. With none, the start fails. The device is chosen once at start-up.

## Consequences

- Positive: a Pi finds its I2S card without configuration; Windows falls back to the default output.
- Negative: the keywords are ALSA-flavoured and can pick the wrong device on a Linux PC (R-3); the device cannot change without a restart.
