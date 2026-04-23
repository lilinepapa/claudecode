import json
import random
from pathlib import Path

from agents.base_agent import BaseAgent
from models.blog_post import Topic


class TopicAgent(BaseAgent):
    """주제 선정 에이전트.

    topics.json에서 주제를 로드하고, 이미 사용한 주제를 추적해
    중복 없이 순환 발행한다.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._topics: list[Topic] = []
        self._used_indices: set[int] = set()
        self._topics_file = self.settings.data_dir / "topics.json"
        self._state_file = self.settings.data_dir / "used_topics.json"
        self._load_topics()
        self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, count: int = 1) -> list[Topic]:
        """사용하지 않은 주제를 count개 반환한다."""
        selected = self._pick(count)
        self.log_info(f"{len(selected)}개 주제 선정: {[t.title for t in selected]}")
        self._save_state()
        return selected

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_topics(self) -> None:
        if not self._topics_file.exists():
            self.log_error(f"topics.json 없음: {self._topics_file}")
            return

        raw = json.loads(self._topics_file.read_text(encoding="utf-8"))
        for category in raw.get("categories", []):
            cat_name = category["name"]
            for item in category.get("topics", []):
                self._topics.append(
                    Topic(
                        title=item["title"],
                        category=cat_name,
                        keywords=item.get("keywords", []),
                        description=item.get("description", ""),
                    )
                )
        self.log_info(f"총 {len(self._topics)}개 주제 로드 완료")

    def _load_state(self) -> None:
        if self._state_file.exists():
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            self._used_indices = set(data.get("used_indices", []))

    def _save_state(self) -> None:
        self._state_file.write_text(
            json.dumps({"used_indices": list(self._used_indices)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _pick(self, count: int) -> list[Topic]:
        available = [i for i in range(len(self._topics)) if i not in self._used_indices]

        # 모든 주제를 사용했으면 초기화 (순환)
        if len(available) < count:
            self.log_info("모든 주제 사용 완료 - 주제 목록 초기화")
            self._used_indices.clear()
            available = list(range(len(self._topics)))

        chosen = random.sample(available, min(count, len(available)))
        self._used_indices.update(chosen)
        return [self._topics[i] for i in chosen]
