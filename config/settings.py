import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class NaverConfig:
    client_id: str = field(default_factory=lambda: os.getenv("NAVER_CLIENT_ID", ""))
    client_secret: str = field(default_factory=lambda: os.getenv("NAVER_CLIENT_SECRET", ""))
    username: str = field(default_factory=lambda: os.getenv("NAVER_USERNAME", ""))
    password: str = field(default_factory=lambda: os.getenv("NAVER_PASSWORD", ""))
    blog_id: str = field(default_factory=lambda: os.getenv("NAVER_BLOG_ID", ""))


@dataclass
class ClaudeConfig:
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"))
    max_tokens: int = 4096


@dataclass
class SchedulerConfig:
    # cron 표현식: 기본 매일 오전 9시
    cron_hour: int = int(os.getenv("SCHEDULE_HOUR", "9"))
    cron_minute: int = int(os.getenv("SCHEDULE_MINUTE", "0"))
    # 한 번에 발행할 포스트 수
    posts_per_run: int = int(os.getenv("POSTS_PER_RUN", "1"))
    timezone: str = os.getenv("TIMEZONE", "Asia/Seoul")


@dataclass
class Settings:
    naver: NaverConfig = field(default_factory=NaverConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    data_dir: Path = BASE_DIR / "data"
    log_dir: Path = BASE_DIR / "logs"
    headless_browser: bool = field(
        default_factory=lambda: os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
