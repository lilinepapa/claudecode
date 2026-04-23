from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PostStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class Topic:
    title: str
    category: str
    keywords: list[str] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_prompt_context(self) -> str:
        kw = ", ".join(self.keywords) if self.keywords else "없음"
        return (
            f"주제: {self.title}\n"
            f"카테고리: {self.category}\n"
            f"키워드: {kw}\n"
            f"설명: {self.description}"
        )


@dataclass
class BlogPost:
    topic: Topic
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    status: PostStatus = PostStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    post_url: Optional[str] = None
    error: Optional[str] = None

    def is_ready(self) -> bool:
        return bool(self.title and self.content)


@dataclass
class PublishResult:
    success: bool
    post_url: Optional[str] = None
    error: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.now)
