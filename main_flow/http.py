
import uvicorn
from dotenv import find_dotenv, load_dotenv
from shared_logging import get_logger, init_logging

from composition_root.containers.http_container import HttpContainer, new_http_container
from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig

logger = get_logger(__name__)


async def run_http() -> None:
    load_dotenv(find_dotenv(".env"))
    server_cfg = ServerConfig.from_env()
    speaker_cfg = SpeakerConfig.from_env()
    init_logging("speaker")

    container = new_http_container(server_cfg, speaker_cfg)
    server = uvicorn.Server(
        uvicorn.Config(
            container.app,
            host=server_cfg.host,
            port=server_cfg.port,
            log_config=None,
            timeout_keep_alive=60,
        )
    )
    logger.info(
        "Starting server",
        service_name=server_cfg.service_name,
        host=server_cfg.host,
        port=server_cfg.port,
    )
    try:
        await server.serve()  # returns after SIGINT/SIGTERM
    finally:
        await _cleanup(container)


async def _cleanup(container: HttpContainer) -> None:
    logger.info("Server stopped; releasing speaker")
    try:
        await container.speaker.stop_playback()
    except Exception:
        logger.exception("Failed to stop speaker playback during cleanup")
    logger.info("Cleanup finished")
