"""APScheduler 기반 블로그 자동 발행 스케줄러."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.orchestrator import OrchestratorAgent
from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class BlogScheduler:
    """주기적으로 OrchestratorAgent를 실행하는 스케줄러."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._scheduler = AsyncIOScheduler(timezone=self._settings.scheduler.timezone)
        self._orchestrator = OrchestratorAgent(settings=self._settings)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """스케줄러를 등록하고 시작한다."""
        cfg = self._settings.scheduler
        trigger = CronTrigger(
            hour=cfg.cron_hour,
            minute=cfg.cron_minute,
            timezone=cfg.timezone,
        )
        self._scheduler.add_job(
            self._run_pipeline,
            trigger=trigger,
            id="naver_blog_post",
            replace_existing=True,
            misfire_grace_time=600,  # 10분 이내 누락 허용
        )
        self._scheduler.start()
        logger.info(
            "스케줄러 시작: 매일 %02d:%02d (%s) 실행",
            cfg.cron_hour,
            cfg.cron_minute,
            cfg.timezone,
        )

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("스케줄러 종료")

    async def run_now(self) -> None:
        """즉시 파이프라인 한 번 실행 (테스트/수동 실행용)."""
        await self._run_pipeline()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run_pipeline(self) -> None:
        posts_count = self._settings.scheduler.posts_per_run
        logger.info("예약 작업 실행: %d개 포스트 발행 시작", posts_count)
        try:
            results = await self._orchestrator.run(posts_count=posts_count)
            published = [p for p in results if p.post_url]
            for p in published:
                logger.info("발행 완료: %s -> %s", p.title, p.post_url)
        except Exception as exc:
            logger.error("예약 작업 오류: %s", exc, exc_info=True)
