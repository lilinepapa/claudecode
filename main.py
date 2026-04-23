"""네이버 블로그 자동 발행 에이전트 - 엔트리포인트."""

import asyncio
import logging
import signal
import sys

from config.settings import get_settings
from scheduler.job_scheduler import BlogScheduler


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/app.log", encoding="utf-8"),
        ],
    )


async def _run_daemon(scheduler: BlogScheduler) -> None:
    """스케줄러를 데몬 모드로 실행하고 SIGINT/SIGTERM을 처리한다."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(*_):
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    scheduler.start()
    print("네이버 블로그 에이전트 실행 중... (종료: Ctrl+C)")
    await stop_event.wait()
    scheduler.stop()
    print("에이전트 종료")


def main() -> None:
    settings = get_settings()
    _setup_logging(settings.log_level)

    scheduler = BlogScheduler(settings=settings)

    # CLI 인자로 즉시 실행 모드 지원
    if len(sys.argv) > 1 and sys.argv[1] == "--run-now":
        logging.getLogger(__name__).info("즉시 실행 모드 (포스트 발행)")
        asyncio.run(scheduler.run_now())
    elif len(sys.argv) > 1 and sys.argv[1] == "--plan-now":
        logging.getLogger(__name__).info("즉시 실행 모드 (주간 계획 수립)")
        asyncio.run(scheduler.plan_now())
    else:
        asyncio.run(_run_daemon(scheduler))


if __name__ == "__main__":
    main()
