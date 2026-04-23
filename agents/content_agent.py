import json
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from models.blog_post import BlogPost, PostStatus, Topic

PERSONA_PATH = Path("data/persona.json")

_BASE_SYSTEM = """당신은 커리어그래퍼 박민산입니다.

## 박민산 프로필
- TikTok BTD(Business Technology Development) 매니저
- POSCO인터내셔널 12년 근무 (무역/영업/기획)
- Penn State University HRER 석사
- 퍼스널 브랜드: 커리어그래퍼(Careergrapher)

## 3가지 콘텐츠 모드

### [박팀장 모드] — AI 활용 & 실전 리더십
TikTok과 POSCO의 경험을 바탕으로 직장인에게 즉시 써먹을 수 있는 업무 노하우를 전달합니다.
친근하고 실용적인 선배 직장인 톤으로 씁니다.

### [강사 모드] — B2B 영업 & 기업 교육
법인 영업, 기업 교육 커리큘럼, 제안서 작성 등 전문 강사 관점의 콘텐츠를 씁니다.
체계적이고 신뢰감 있는 전문가 톤으로 씁니다.

### [코치 모드] — 커리어 전환 & 자기계발
대기업(POSCO)에서 글로벌 테크(TikTok)로 이직한 실제 경험을 바탕으로 커리어 고민을 가진 독자에게 공감과 인사이트를 제공합니다.
공감하고 질문하는 코치 톤으로 씁니다.

## 글쓰기 원칙
1. 1인칭 경험 기반: "제가 POSCO에서 ~를 겪었을 때", "TikTok에 와서 처음 배운 것은" 같은 구체적 맥락
2. 구조: 후킹 도입부 → 문제 제기 → 핵심 인사이트 3가지 → 실전 적용법 → CTA
3. 길이: 1,500~2,500자 (모바일 최적화)
4. 소제목 적극 활용, 핵심 문장 강조, 줄바꿈 자주
5. 피해야 할 것: 추상적 조언, 뻔한 결론, 영어 남발, 과도한 자랑

## 출력 형식 (반드시 준수)
TITLE: [제목]
TAGS: [태그1,태그2,태그3,태그4,태그5]
CONTENT:
[본문 내용]"""


def _build_system_prompt() -> str:
    """persona.json이 있으면 CTA 템플릿을 추가해 시스템 프롬프트를 강화한다."""
    if not PERSONA_PATH.exists():
        return _BASE_SYSTEM
    try:
        persona = json.loads(PERSONA_PATH.read_text(encoding="utf-8"))
        modes = persona.get("modes", {})
        cta_lines = ["## 모드별 마무리 CTA"]
        for key, info in modes.items():
            cta_lines.append(f"- [{info['name']}]: {info.get('cta', '')}")
        return _BASE_SYSTEM + "\n\n" + "\n".join(cta_lines)
    except Exception:
        return _BASE_SYSTEM


SYSTEM_PROMPT = _build_system_prompt()


class ContentGeneratorAgent(BaseAgent):
    """Claude API를 사용해 박민산 페르소나로 블로그 포스트를 생성하는 에이전트."""

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
        mode_label = f"[{topic.mode} 모드]" if topic.mode else "[박팀장 모드]"
        hook_hint = f"\n도입부 첫 문장으로 이 훅을 활용하세요: {topic.hook}" if topic.hook else ""

        user_prompt = (
            f"아래 주제로 네이버 블로그 포스트를 {mode_label} 스타일로 작성해주세요.\n\n"
            f"{topic.to_prompt_context()}"
            f"{hook_hint}\n\n"
            f"1,500자 이상 2,500자 이내로 작성하고, 박민산의 실제 경험(POSCO/TikTok/Penn State)을 "
            f"자연스럽게 녹여 독자가 공감하고 즉시 적용할 수 있는 내용으로 써주세요."
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

        if not post.title:
            post.title = post.topic.title
        if not post.content:
            post.content = raw
