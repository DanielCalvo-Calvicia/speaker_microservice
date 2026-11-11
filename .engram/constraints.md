# Constraints

- Audio backend is `sounddevice` (PortAudio); output is 16-bit PCM.
- End-to-end test (`tests/simple.py`) needs a real output device.
- `SPEAKER_API_KEY` is mandatory: startup fails without it.
