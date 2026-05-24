import logging

from runtime.environment import RuntimeEnvironment, resolve_runtime_environment


TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self: logging.Logger, message, *args, **kwargs) -> None:
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]


_PROJECT_LOGGER_PREFIX = "speaker_microservice"
_ENVIRONMENT_LEVELS = {
    "development": TRACE_LEVEL,
    "staging": logging.WARNING,
    "production": logging.CRITICAL,
}


class ApplicationLogFilter(logging.Filter):
    def __init__(self, environment: RuntimeEnvironment):
        super().__init__()
        self.environment = environment
        self.minimum_level = _ENVIRONMENT_LEVELS[environment.name]

    def filter(self, record: logging.LogRecord) -> bool:
        if not record.name.startswith(_PROJECT_LOGGER_PREFIX):
            return True
        return record.levelno >= self.minimum_level


class EnvironmentFormatter(logging.Formatter):
    def __init__(self, environment: RuntimeEnvironment):
        super().__init__(
            fmt="%(asctime)s - %(environment)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.environment = environment.name

    def format(self, record: logging.LogRecord) -> str:
        record.environment = self.environment
        return super().format(record)


def configure_logging(environment: RuntimeEnvironment | None = None) -> RuntimeEnvironment:
    resolved_environment = environment or resolve_runtime_environment()

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(TRACE_LEVEL)

    handler = logging.StreamHandler()
    handler.setLevel(TRACE_LEVEL)
    handler.setFormatter(EnvironmentFormatter(resolved_environment))
    handler.addFilter(ApplicationLogFilter(resolved_environment))
    root_logger.addHandler(handler)

    return resolved_environment


def get_logger(scope: str) -> logging.Logger:
    name = scope if scope.startswith(_PROJECT_LOGGER_PREFIX) else f"{_PROJECT_LOGGER_PREFIX}.{scope}"
    return logging.getLogger(name)
