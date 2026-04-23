import logging
from abc import ABC, abstractmethod

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """모든 에이전트의 베이스 클래스."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self, *args, **kwargs):
        """에이전트의 메인 실행 로직."""
        ...

    def log_info(self, msg: str) -> None:
        self.logger.info("[%s] %s", self.__class__.__name__, msg)

    def log_error(self, msg: str) -> None:
        self.logger.error("[%s] %s", self.__class__.__name__, msg)

    def log_debug(self, msg: str) -> None:
        self.logger.debug("[%s] %s", self.__class__.__name__, msg)
