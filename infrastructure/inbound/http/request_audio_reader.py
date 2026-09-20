from collections.abc import AsyncGenerator

from fastapi import Request
from shared_logging import get_logger
from starlette.requests import ClientDisconnect

from infrastructure.inbound.http.ndjson_audio_decoder import NdjsonAudioDecoder, NdjsonInputError

logger = get_logger(__name__)


class RequestAudioReader:
    """Turns an HTTP request body into audio chunks, remembering what it read.

    The body is either raw PCM or, when the content type is ``application/x-ndjson``, a
    stream of NDJSON events (see ``NdjsonAudioDecoder``).
    """

    def __init__(self, request: Request, sample_rate: int, channels: int) -> None:
        self._request = request
        self._format = (sample_rate, channels)
        self.chunk_count = 0
        self.total_bytes = 0
        self.read_error: Exception | None = None
        content_type = request.headers.get("content-type", "").lower()
        self.is_ndjson = "application/x-ndjson" in content_type

    def audio(self) -> AsyncGenerator[bytes, None]:
        return self._ndjson_audio() if self.is_ndjson else self._raw_audio()

    def _count(self, audio: bytes) -> None:
        self.chunk_count += 1
        self.total_bytes += len(audio)

    async def _raw_audio(self) -> AsyncGenerator[bytes, None]:
        try:
            async for chunk in self._request.stream():
                if not chunk:
                    continue
                self._count(chunk)
                yield chunk
        except ClientDisconnect:
            logger.info("HTTP raw request stream disconnected; finalizing playback stream")
            return
        except Exception as error:
            self.read_error = error
            logger.error(
                "HTTP request stream failed while playback was active",
                type=type(error).__name__,
                message=str(error),
            )
            raise

    async def _ndjson_audio(self) -> AsyncGenerator[bytes, None]:
        decoder = NdjsonAudioDecoder(*self._format)
        try:
            async for chunk in self._request.stream():
                if not chunk:
                    continue
                for audio in decoder.feed(chunk):
                    self._count(audio)
                    yield audio
            for audio in decoder.finish():
                self._count(audio)
                yield audio
        except ClientDisconnect:
            logger.info("HTTP NDJSON request stream disconnected; finalizing playback stream")
            return
        except UnicodeDecodeError as error:
            self.read_error = NdjsonInputError("NDJSON request body must be valid UTF-8.")
            logger.error("HTTP NDJSON request body failed validation", read_error=self.read_error)
            raise self.read_error from error
        except NdjsonInputError as error:
            self.read_error = error
            logger.error("HTTP NDJSON request body failed validation", error=error)
            raise
