NDJSON_MEDIA_TYPE = "application/x-ndjson"


def stream_headers() -> dict[str, str]:
    """The headers of a live NDJSON playback answer: never cached, never sniffed."""
    return {
        "Cache-Control": "no-cache",
        "X-Content-Type-Options": "nosniff",
    }
