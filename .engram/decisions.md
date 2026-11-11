# Decisions

- D1: No `cmd/` folder (shadows stdlib `cmd`); entry point is `main.py` + `main_flow/`.
- D2: Config is stdlib frozen dataclasses in `infrastructure/config/`.
- D3: The NDJSON stream protocol (`ndjson_*`) is transport, so it lives in `infrastructure/inbound/http`, not `application`.
- D4: HTTP status mapping stays "everything is 500" (`http_error_mapper.py`) until clients are ready.
- D5: The API key is read once at startup (`ServerConfig`) and injected into `ApiKeyAuthenticator`, not read per request.
- D6: `PlayStreamInboundDTO.setup_future` is kept so the HTTP adapter can answer as soon as the device is open, without waiting for the whole stream.
- D7: Runtime environments (`APP_ENV` log levels, `runtime/`) were dropped; logging is stdlib and `LOG_LEVEL` decides.
