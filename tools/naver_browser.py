"""네이버 블로그 웹 자동화 클라이언트 (Playwright 기반).

네이버는 공개 블로그 작성 API를 제공하지 않으므로
Playwright로 웹 UI를 제어해 포스트를 발행한다.
"""

import asyncio
import logging
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from models.blog_post import BlogPost, PublishResult

logger = logging.getLogger(__name__)

# 네이버 로그인 / 에디터 URL
_NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
_BLOG_WRITE_URL = "https://blog.naver.com/PostWriteForm.naver"


class NaverBlogBrowser:
    """Playwright를 래핑한 네이버 블로그 자동화 클라이언트."""

    def __init__(
        self,
        username: str,
        password: str,
        blog_id: str,
        headless: bool = True,
    ):
        self._username = username
        self._password = password
        self._blog_id = blog_id
        self._headless = headless
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "NaverBlogBrowser":
        await self._launch()
        return self

    async def __aexit__(self, *_) -> None:
        await self._close()

    async def publish(self, post: BlogPost) -> PublishResult:
        """블로그 포스트를 네이버에 발행하고 결과를 반환한다."""
        try:
            page = await self._new_page()
            await self._login(page)
            await self._navigate_to_editor(page)
            await self._fill_post(page, post)
            url = await self._submit(page)
            await page.close()
            return PublishResult(success=True, post_url=url)
        except Exception as exc:
            logger.error("발행 실패: %s", exc)
            return PublishResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def _launch(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )

    async def _close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()

    async def _new_page(self) -> Page:
        assert self._context, "Browser not launched"
        return await self._context.new_page()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def _login(self, page: Page) -> None:
        logger.debug("네이버 로그인 시도")
        await page.goto(_NAVER_LOGIN_URL, wait_until="load", timeout=30_000)
        await asyncio.sleep(2)

        await page.wait_for_selector("#id", timeout=15_000)
        await page.fill("#id", self._username)
        await page.fill("#pw", self._password)
        await page.click(".btn_login")

        # 로그인 완료 대기
        await page.wait_for_load_state("networkidle", timeout=15_000)

        if "nidlogin" in page.url:
            raise RuntimeError("로그인 실패: 캡차 또는 자격 증명 오류가 발생했습니다.")
        logger.debug("로그인 성공 (현재 URL: %s)", page.url)

        # 로그인 완료 대기 (홈 또는 captcha 화면)
        await page.wait_for_load_state("networkidle", timeout=15_000)

        if "nidlogin" in page.url:
            raise RuntimeError(
                "로그인 실패: 캡차 또는 자격 증명 오류가 발생했습니다."
            )
        logger.debug("로그인 성공 (현재 URL: %s)", page.url)

    # ------------------------------------------------------------------
    # Editor
    # ------------------------------------------------------------------

    async def _navigate_to_editor(self, page: Page) -> None:
        write_url = f"{_BLOG_WRITE_URL}?blogId={self._blog_id}"
        await page.goto(write_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)  # 에디터 JS 로딩 대기

    async def _fill_post(self, page: Page, post: BlogPost) -> None:
        # 제목 입력 — 스마트에디터 ONE 기준
        title_selector = ".se-title-input"
        await page.wait_for_selector(title_selector, timeout=15_000)
        await page.click(title_selector)
        await page.keyboard.type(post.title)

        # 본문 입력
        body_selector = ".se-text-paragraph"
        await page.wait_for_selector(body_selector, timeout=10_000)
        await page.click(body_selector)
        await page.keyboard.type(post.content)

        # 태그 입력
        if post.tags:
            tag_selector = ".se-tag-input"
            tag_visible = await page.is_visible(tag_selector)
            if tag_visible:
                await page.click(tag_selector)
                for tag in post.tags:
                    await page.keyboard.type(tag)
                    await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def _submit(self, page: Page) -> Optional[str]:
        # 발행 버튼 클릭
        publish_btn = ".publish-btn, [data-action='publish'], button:has-text('발행')"
        await page.click(publish_btn)

        # 발행 확인 팝업이 있을 경우 처리
        try:
            confirm_btn = "button:has-text('확인'), button:has-text('발행하기')"
            await page.wait_for_selector(confirm_btn, timeout=3_000)
            await page.click(confirm_btn)
        except Exception:
            pass

        # 발행 후 URL 수집
        await page.wait_for_load_state("networkidle", timeout=15_000)
        return page.url if "blog.naver.com" in page.url else None
