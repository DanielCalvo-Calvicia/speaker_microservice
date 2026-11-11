# ADR-006 — Audio is never converted between services; resample only when the device rejects the rate

**Status:** Accepted (workspace rule; the resampler came after commit `eacddae`; recorded 2026-11-05).

## Context

Every service passes PCM16 mono in `bytes_base64`, in the format the previous one announced. A device may still refuse that rate. Writing the samples as they are at another rate would play them at the wrong pitch and speed.

## Decision

The speaker plays at the requested rate. `fallback_formats` lists what to try when opening the device: the requested format, then the same layout at 44.1 kHz. If the device accepted another rate than the stream's, a `LinearResampler` (`domain/operations/resample.py`, linear interpolation, stateful across chunks) converts the audio to it, and a warning is logged. The events still announce the requested format. Nothing is converted for any other reason.

## Consequences

- Positive: a device that only opens at 44.1 kHz plays correctly.
- Negative: linear interpolation is cheap, not high quality; the path has been tested with a fake driver only (R-10).
