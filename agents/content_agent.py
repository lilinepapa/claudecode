import anthropic

from agents.base_agent import BaseAgent
from models.blog_post import BlogPost, PostStatus, Topic

SYSTEM_PROMPT = """당신은 네이버 블로그 전문 작가입니다. 한국 독자들이 즐겨 읽는 블로그 포스트를 작성합니다.

작성 원칙:
- 구어체와 문어체를 적절히 혼합한 친근한 문체
- SEO를 고려한 자연스러운 키워드 배치
- 실용적이고 구체적인 정보 제공
- 소제목과 단락을 활용한 가독성 높은 구조
- 독자가 공감하고 저장하고 싶은 콘텐츠

출력 형식은 반드시 다음 구조를 따르세요:
TITLE: [제목]
TAGS: [태그1,태그2,태그3,태그4,태그5]
CONTENT:
[본문 내용]"""


class ContentGeneratorAgent(BaseAgent):
    """Claude API를 사용해 블로그 포스트 본문을 생성하는 에이전트."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = anthropic.Anthropic(api_key=self.settings.claude.api_key)

    async def run(self, topic: Topic) -> BlogPost:
        post = BlogPost(topic=topic, status=PostStatus.GENERATING)
        self.log_info(f"콘텐츠 생성 시작: {topic.title}")

        try:
            raw = self._generate(topic)
            self._parse_into(post, raw)
            post.status = PostStatus.READY
            self.log_info(f"콘텐츠 생성 완료: {post.title}")
        except Exception as exc:
            post.status = PostStatus.FAILED
            post.error = str(exc)
            self.log_error(f"콘텐츠 생성 실패: {exc}")

        return post

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _generate(self, topic: Topic) -> str:
        """Claude API를 호출해 블로그 포스트 텍스트를 반환한다."""
        user_prompt = (
            f"다음 주제로 네이버 블로그 포스트를 작성해주세요.\n\n"
            f"{topic.to_prompt_context()}\n\n"
            f"1,000자 이상 2,000자 이내로 작성하고, 독자가 실생활에 바로 적용할 수 있는 "
            f"구체적인 내용을 포함해주세요."
        )

        full_text = []
        with self._client.messages.stream(
            model=self.settings.claude.model,
            max_tokens=self.settings.claude.max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                full_text.append(text)

        return "".join(full_text)

    def _parse_into(self, post: BlogPost, raw: str) -> None:
        """모델 출력을 BlogPost 필드에 파싱한다."""
        lines = raw.strip().splitlines()
        content_lines: list[str] = []
        in_content = False

        for line in lines:
            if line.startswith("TITLE:"):
                post.title = line.removeprefix("TITLE:").strip()
            elif line.startswith("TAGS:"):
                raw_tags = line.removeprefix("TAGS:").strip()
                post.tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            elif line.startswith("CONTENT:"):
                in_content = True
            elif in_content:
                content_lines.append(line)

        post.content = "\n".join(content_lines).strip()

        # 파싱 실패 대비 폴백
        if not post.title:
            post.title = post.topic.title
        if not post.content:
            post.content = raw
