import asyncio
import logging
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.content_agent import ContentGeneratorAgent
from agents.publisher_agent import PublisherAgent
from agents.topic_agent import TopicAgent
from models.blog_post import BlogPost, PostStatus

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """전체 블로그 발행 파이프라인을 조율하는 오케스트레이터.

    흐름:
      TopicAgent → ContentGeneratorAgent → PublisherAgent
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._topic_agent = TopicAgent(settings=self.settings)
        self._content_agent = ContentGeneratorAgent(settings=self.settings)
        self._publisher_agent = PublisherAgent(settings=self.settings)

    async def run(self, posts_count: int = 1) -> list[BlogPost]:
        """posts_count개의 포스트를 선정 → 생성 → 발행한다."""
        self.log_info(f"파이프라인 시작 (목표: {posts_count}개 포스트)")
        start = datetime.now()

        # 1. 주제 선정
        topics = await self._topic_agent.run(count=posts_count)

        # 2. 콘텐츠 생성 (병렬)
        content_tasks = [self._content_agent.run(topic) for topic in topics]
        posts: list[BlogPost] = await asyncio.gather(*content_tasks)

        # 3. 발행 (순차 — 네이버 봇 감지 방지)
        results: list[BlogPost] = []
        for post in posts:
            if post.status == PostStatus.READY:
                await self._publisher_agent.run(post)
                # 포스트 간 간격 (봇 감지 방지)
                await asyncio.sleep(5)
            else:
                self.log_error(f"발행 건너뜀 (생성 실패): {post.topic.title}")
            results.append(post)

        elapsed = (datetime.now() - start).total_seconds()
        success = sum(1 for p in results if p.status == PostStatus.PUBLISHED)
        self.log_info(
            f"파이프라인 완료: {success}/{len(results)}개 발행 성공 ({elapsed:.1f}초)"
        )
        return results
