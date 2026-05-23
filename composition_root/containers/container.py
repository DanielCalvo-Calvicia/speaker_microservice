import logging
from dataclasses import dataclass
from composition_root.dependencies.speaker_dependency import SpeakerDependency, generate_speaker_dependency

logger = logging.getLogger("speaker_microservice.container")

@dataclass(slots=True, frozen=True)
class Container:
    speaker_dependency: SpeakerDependency

def BuildContainer(name: str) -> Container:
    """Instantiate and compile all system dependency trees."""
    logger.info("Building container: %s", name)
    speaker_dep = generate_speaker_dependency()
    container = Container(speaker_dependency=speaker_dep)
    logger.info("Container built: %s", name)
    return container
