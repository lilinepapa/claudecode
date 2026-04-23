from agents.base_agent import BaseAgent
from models.blog_post import BlogPost, PostStatus, PublishResult
from tools.naver_browser import NaverBlogBrowser


class PublisherAgent(BaseAgent):
    """네이버 블로그에 포스트를 발행하는 에이전트."""

    async def run(self, post: BlogPost) -> PublishResult:
        if not post.is_ready():
            msg = f"포스트가 준비되지 않았습니다: {post.status}"
            self.log_error(msg)
            return PublishResult(success=False, error=msg)

        self.log_info(f"발행 시작: {post.title}")
        post.status = PostStatus.PUBLISHING

        naver = self.settings.naver
        async with NaverBlogBrowser(
            username=naver.username,
            password=naver.password,
            blog_id=naver.blog_id,
            headless=self.settings.headless_browser,
        ) as browser:
            result = await browser.publish(post)

        if result.success:
            from datetime import datetime
            post.status = PostStatus.PUBLISHED
            post.published_at = result.published_at
            post.post_url = result.post_url
            self.log_info(f"발행 완료: {result.post_url}")
        else:
            post.status = PostStatus.FAILED
            post.error = result.error
            self.log_error(f"발행 실패: {result.error}")

        return result
