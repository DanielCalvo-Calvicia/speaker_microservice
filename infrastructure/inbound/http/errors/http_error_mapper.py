from fastapi import status

from application.errors import SpeakerUnavailable
from domain.errors import InvalidPlaybackFormat


def map_error(error: Exception) -> int:
    """Translate an application/domain error into an HTTP status code.

    422  the requested playback format is invalid
    503  the output device is unavailable
    500  anything else
    """
    if isinstance(error, InvalidPlaybackFormat):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    if isinstance(error, SpeakerUnavailable):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_500_INTERNAL_SERVER_ERROR
