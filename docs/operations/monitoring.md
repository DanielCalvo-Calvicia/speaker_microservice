# Monitoring and operations

What exists today, checked against the code; anything else is stated as absent.

## Probes

| Probe | Behaviour |
|---|---|
| `GET /health` | `200`, `healthy: true`, whenever the process answers; it touches no device |
| `GET /ready` | `200`; `is_ready` is true when the selected device reports output channels, else false with a reason. Probes the device without opening a stream |
| `GET /available` | The same check, answered as `is_available` / `reason`. The deploy tool (`ready = "/available"` in its catalogue) and Brain's pre-flight use it. It is **not** "a playback is active" |

Neither probe can report "no device at all" because the process refuses to start without one (R-1 in [risks](../risks/risks-and-debt.md)). A device that disappears later makes `is_ready` false and the next playback `503`.

## Start-up and shutdown

Start: `.env` is loaded, the two configs are read, logging starts (`init_logging("speaker")`), the device is selected while the container is built, then uvicorn runs (`timeout_keep_alive=60`). A start-up problem (a bad number in a variable, no usable output device, no PortAudio) stops the process with the error.

Shutdown: on SIGINT or SIGTERM uvicorn returns, the FastAPI lifespan and `_cleanup` in `main_flow/http.py` both call `stop_playback` (idempotent): the playback task is cancelled, the stream stopped and closed, the device released. There is no timeout of its own; a Docker `stop` path has never been run (unproven).

## Logs

Logging is `shared_logging` only (`get_logger(__name__)`), structured, constant messages with keyword fields; the level is `LOG_LEVEL`. `TracingMiddleware` (outermost) continues a W3C `traceparent` or starts a trace, logs one line per request (logger `shared_logging.http`), tags every line with `service: speaker` and `trace_id`, and returns `x-trace-id`; tested in `tests/composition_root/test_tracing.py`. See `shared-logging/docs/logging.md`.

What the service logs about a playback (all at the shown levels):

| Message | Level | Fields |
|---|---|---|
| `HTTP playback stream request received` | info | `client`, `sample_rate`, `channels` |
| `Speaker started` | info | device index, the format the device accepted |
| `Failed to open device with candidate format` | warning | the candidate and the error |
| `Output device rate differs from the stream rate; resampling` | warning | `stream_rate`, `device_rate` |
| `Playback session superseded; stopping audio consumption` | info | |
| `Finished consuming inbound audio stream` | info | `queued_chunks`, `queued_bytes` |
| `Playback queue cleanup timed out; truncating` | warning | the device did not play everything that was queued within its duration plus 2 s, so audio was dropped; the fields `queued_bytes` and `written_bytes` say how much (R-6; the call still answers success) |
| `Playback session finalized` | info | queued and written chunks and bytes |
| `HTTP playback completed successfully` / `HTTP playback failed` | info / warning | `chunks`, `bytes`, `message` |
| `HTTP request stream failed while playback was active`, `HTTP NDJSON request body failed validation` | error | the error type and message |
| `Speaker readiness check failed`, `Speaker device has no output channels` | warning | device index |

The logs never hold the audio: only its counts. They do hold the address of the caller (`client`) and the device name when `DEBUG` is on.

## Not present

- Metrics and alerting: none. Tracing is the shared package's span and log correlation only; no exporter is configured here.
- Which backend is active: `/available` has no field for it (R-4).
- Files on disk: the service writes none.
- Rate limiting and playback queueing: one playback at a time; a new request supersedes the running one.
