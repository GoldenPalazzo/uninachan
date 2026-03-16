from datetime import datetime
import re

from pydantic import BaseModel, field_validator

class PostFile(BaseModel):
    id: int
    storage_key: str
    thumb_key: str
    width: int | None
    height: int | None
    spoiler: bool

class Post(BaseModel):
    id: int
    thread_id: int
    name: str
    tripcode: str | None
    content: str | None
    files: list[PostFile] = []
    created_at: datetime

class Thread(BaseModel):
    id: int
    board_id: int
    subject: str | None
    locked: bool
    pinned: bool
    bump_at: datetime
    reply_count: int
    op: Post | None = None
    last_replies: list[Post] = []

class Board(BaseModel):
    id: int
    name: str
    description: str | None = None
    nsfw: bool = False
    max_threads: int = 150
    bump_limit: int = 500
    slug: str

    @field_validator("slug")
    @classmethod
    def slug_valido(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9]{1,8}$', v):
            raise ValueError("slug deve essere alfanumerico, max 8 caratteri")
        return v


