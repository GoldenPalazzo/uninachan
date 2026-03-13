from datetime import datetime
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
import psycopg
from psycopg.rows import class_row

DATABASE_URL = "postgresql://postgres:example@localhost:5432/postgres"
app = FastAPI()

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

def get_boards() -> list[Board]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=class_row(Board)) as cur:
            cur.execute("SELECT * FROM boards")
            return cur.fetchall()

@app.post("/createboard", response_model=Board, status_code=201)
async def create_board(body: Board):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=class_row(Board)) as cur:
            try:
                cur.execute("""
                    INSERT INTO boards (slug, name, description, nsfw, max_threads, bump_limit)
                    VALUES (%(slug)s, %(name)s, %(description)s, %(nsfw)s, %(max_threads)s, %(bump_limit)s)
                    RETURNING *
                """, body.model_dump())
                conn.commit()
                return cur.fetchone()
            except psycopg.errors.UniqueViolation:
                raise HTTPException(status_code=409, detail=f"Board /{body.slug}/ esiste già")

@app.get("/")
async def root():
    return {
        "message": "Hello World",
        'boards': get_boards()
    }
