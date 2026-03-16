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

class PostBase(BaseModel):
    name: str = "Anonymous"
    tripcode: str | None = None
    content: str | None = None
    # files: list[PostFile] = []

class PostCreate(PostBase):
    pass

class Post(PostBase):
    board_id: int
    thread_id: int
    id: int
    created_at: datetime
    is_op: bool
    removed_at: datetime | None
    removal_reason: str | None

class ThreadBase(BaseModel):
    subject: str | None

class ThreadCreate(ThreadBase):
    first_post: PostBase

class Thread(ThreadBase):
    id: int
    board_id: int
    locked: bool
    pinned: bool
    bump_at: datetime
    reply_count: int
    op: Post | None = None
    last_replies: list[Post] = []

class BoardBase(BaseModel):
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

class BoardCreate(BoardBase):
    pass

class Board(BoardBase):
    id: int
   
class Removal(BaseModel):
    reason: str
