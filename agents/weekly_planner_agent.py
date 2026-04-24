"""매주 목요일 실행되는 주간 콘텐츠 계획 수립 에이전트."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from config.settings import Settings

logger = logging.getLogger(__name__)

WEEKLY_PLAN_PATH = Path("data/weekly_plan.json")
PERSONA_PATH = Path("data/persona.json")

PLANNER_SYSTEM_PROMPT = """당신은 커리어그래퍼 박민산의 전속 콘텐츠 전략가입니다.

박민산 프로필:
- TikTok BTD 매니저 / POSCO인터내셔널 12년 경력
- Penn State HRER 석사
- 퍼스널 브랜드: 커리어그래퍼(Careergrapher)
- 3가지 콘텐츠 모드: [박팀장 모드] AI/리더십, [강사 모드] B2B영업/기업교육, [코치 모드] 커리어전환

당신의 역할은 박민산의 실제 경험과 전문성에 기반한 주간 블로그 콘텐츠 계획을 수립하는 것입니다.
각 포스팅은 독자에게 즉시 적용 가능한 실용적 가치를 제공해야 합니다."""


class WeeklyPlannerAgent(BaseAgent):
    """Anthropic API를 활용해 7일치 블로그 콘텐츠 계획을 생성하고 저장한다."""

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings)
        self._client = anthropic.Anthropic(api_key=self.settings.claude.api_key)
        self._persona = self._load_persona()

    def _load_persona(self) -> dict:
        if PERSONA_PATH.exists():
            with open(PERSONA_PATH, encoding="utf-8") as f:
                return json.load(f)
        return {}

    async def run(self, *args, **kwargs) -> dict:
        plan = self._generate_plan()
        self._save_plan(plan)
        logger.info("주간 콘텐츠 계획 수립 완료: %d개 항목", len(plan.get("days", [])))
        return plan

    def _generate_plan(self) -> dict:
        today = datetime.now()
        date_range = [(today + timedelta(days=i)) for i in range(7)]
        rotation = self._persona.get("weekly_content_rotation", {})

        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_contexts = []
        for d in date_range:
            dn = day_names[d.weekday()]
            rot = rotation.get(dn, {})
            day_contexts.append({
                "date": d.strftime("%Y-%m-%d"),
                "weekday": dn,
                "mode": rot.get("mode", "박팀장"),
                "theme": rot.get("theme", ""),
            })

        user_prompt = self._build_prompt(day_contexts)
        response_text = self._call_api(user_prompt)
        return self._parse_response(response_text, day_contexts)

    def _build_prompt(self, day_contexts: list[dict]) -> str:
        modes_info = json.dumps(
            {k: v["topics"] for k, v in self._persona.get("modes", {}).items()},
            ensure_ascii=False,
            indent=2,
        )
        days_info = json.dumps(day_contexts, ensure_ascii=False, indent=2)

        return f"""박민산(커리어그래퍼)의 다음 7일 네이버 블로그 콘텐츠 계획을 수립해주세요.

각 모드별 주요 주제:
{modes_info}

7일 일정 (요일별 모드/테마 배정):
{days_info}

각 날짜별로 아래 JSON 형식으로 계획을 작성해주세요.
박민산의 실제 경험(POSCO 12년, TikTok, Penn State)과 연결되는 구체적인 주제를 선택하세요.
중복 없이, 독자에게 즉시 가치를 줄 수 있는 실용적인 주제로 구성하세요.

반드시 아래 JSON 형식만 출력하세요 (다른 텍스트 없이):
{{
  "week_start": "YYYY-MM-DD",
  "generated_at": "YYYY-MM-DD",
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "weekday": "monday",
      "mode": "박팀장",
      "title": "포스팅 제목 (30자 이내, 클릭을 유도하는 제목)",
      "keywords": ["키워드1", "키워드2", "키워드3"],
      "angle": "이 포스팅의 핵심 관점/차별화 포인트 (2-3문장)",
      "hook": "첫 문장 도입부 (독자를 잡아끄는 질문 또는 반전 문장)"
    }}
  ]
}}"""

    def _call_api(self, user_prompt: str) -> str:
        response = self._client.messages.create(
            model=self.settings.claude.model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": PLANNER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def _parse_response(self, text: str, day_contexts: list[dict]) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            plan = json.loads(text)
            today_str = datetime.now().strftime("%Y-%m-%d")
            plan.setdefault("week_start", day_contexts[0]["date"])
            plan.setdefault("generated_at", today_str)
            return plan
        except json.JSONDecodeError:
            logger.warning("API 응답 JSON 파싱 실패, 기본 플랜 사용")
            return self._fallback_plan(day_contexts)

    def _fallback_plan(self, day_contexts: list[dict]) -> dict:
        today_str = datetime.now().strftime("%Y-%m-%d")
        fallback_titles = {
            "박팀장": "AI로 업무 효율 3배 올린 실전 방법",
            "강사": "B2B 영업에서 첫 미팅을 계약으로 바꾸는 법",
            "코치": "대기업에서 글로벌 테크로 이직한 현실 이야기",
        }
        days = []
        for ctx in day_contexts:
            mode = ctx.get("mode", "박팀장")
            days.append({
                "date": ctx["date"],
                "weekday": ctx["weekday"],
                "mode": mode,
                "title": fallback_titles.get(mode, "커리어그래퍼 박민산의 실전 인사이트"),
                "keywords": ["커리어그래퍼", "박민산", mode],
                "angle": f"{mode} 관점에서 독자에게 실용적인 인사이트를 제공합니다.",
                "hook": "당신의 커리어, 지금 이대로 괜찮으신가요?",
            })
        return {"week_start": day_contexts[0]["date"], "generated_at": today_str, "days": days}

    def _save_plan(self, plan: dict) -> None:
        WEEKLY_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(WEEKLY_PLAN_PATH, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        logger.info("주간 계획 저장: %s", WEEKLY_PLAN_PATH)

    @staticmethod
    def load_todays_plan() -> dict | None:
        if not WEEKLY_PLAN_PATH.exists():
            return None
        with open(WEEKLY_PLAN_PATH, encoding="utf-8") as f:
            plan = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        for day in plan.get("days", []):
            if day.get("date") == today:
                return day
        return None
