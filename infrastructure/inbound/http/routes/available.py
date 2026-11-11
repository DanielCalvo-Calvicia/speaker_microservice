from contracts.api.microservices.common.availability import AvailabilityResponse
from fastapi.responses import JSONResponse

from application.ports.inbound.speaker_inbound_port import SpeakerInboundPort
from infrastructure.inbound.http.response.http_envelope import success


async def handle_available(inbound: SpeakerInboundPort) -> JSONResponse:
    """GET /available: whether the output device can be used (probed without opening a stream)."""
    readiness = await inbound.check_readiness()
    return success(
        "check_availability",
        "Speaker availability checked",
        AvailabilityResponse(is_available=readiness.is_ready, reason=readiness.message or None),
    )
