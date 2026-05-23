import asyncio
import logging
import sys

from composition_root.setup.setup import setup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("speaker_microservice.main")

if __name__ == "__main__":
    try:
        logger.info("Speaker microservice process entrypoint reached.")
        asyncio.run(setup())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting speaker microservice.")
        sys.exit(0)
    except Exception:
        logger.exception("Unhandled exception reached process entrypoint.")
        raise
