import base64
from contextlib import asynccontextmanager
from datetime import datetime
import hashlib
from pathlib import Path
import re
import os

from fastapi import FastAPI, HTTPException, Request
from loguru import logger
import psycopg
from psycopg.rows import class_row

from models import Board, Post, Thread, BoardCreate, PostCreate, ThreadCreate

DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://uninachan:secret@localhost:5432/uninachan")

def generate_tripcode(password: str | None) -> str | None:
    if password is None:
        return None
    digest = hashlib.sha1(password.encode()).digest()
    return '!' + base64.b64encode(digest).decode()[:10]

@asynccontextmanager
async def lifespan(app: FastAPI):
    schema = Path('./schema.sql').read_text()
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(schema) # type: ignore
            await conn.commit()
    yield

app = FastAPI(lifespan=lifespan)

async def get_boards() -> list[Board]:
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute("SELECT * FROM boards")
            return await cur.fetchall()

@app.post("/new/board", response_model=Board, status_code=201)
async def create_board(body: BoardCreate):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            try:
                await cur.execute("""
                    INSERT INTO boards (slug, name, description, nsfw, max_threads, bump_limit)
                    VALUES (%(slug)s, %(name)s, %(description)s, %(nsfw)s, %(max_threads)s, %(bump_limit)s)
                    RETURNING *
                """, body.model_dump())
                await conn.commit()
                return await cur.fetchone()
            except psycopg.errors.UniqueViolation:
                raise HTTPException(status_code=409, detail=f"Board {body.slug} esiste già")

@app.post("/new/thread", response_model=Thread, status_code=201)
async def create_thread(request: Request, thread: ThreadCreate) -> Thread:
    ip_hash = hashlib.sha256(request.client.host.encode()).hexdigest()
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        try:
            async with conn.cursor(row_factory=class_row(Thread)) as cur:
                await cur.execute('''
                    INSERT INTO threads (board_id, subject)
                    VALUES (%(board_id)s, %(subject)s)
                    RETURNING *
                ''', thread.model_dump())
                new_thread = await cur.fetchone()
                assert(new_thread is not None)
            async with conn.cursor(row_factory=class_row(Post)) as cur:
                thread.first_post.tripcode = generate_tripcode(thread.first_post.tripcode)
                await cur.execute('''
                    INSERT INTO posts (thread_id, board_id, name, tripcode, content, ip_hash, is_op)
                    VALUES (%(thread_id)s, %(board_id)s, %(name)s, %(tripcode)s, %(content)s, %(ip_hash)s, true)
                    RETURNING *
                ''', {
                    **thread.first_post.model_dump(),
                    'thread_id': new_thread.id,
                    'board_id': thread.board_id,
                    'ip_hash': ip_hash
                })
                new_post = await cur.fetchone()
                await conn.commit()
            new_thread.op = new_post
            return new_thread
        except psycopg.errors.ForeignKeyViolation:
            raise HTTPException(status_code=409, detail=f"La board {thread.board_id} non esiste")

@app.post("/new/post", response_model=Post, status_code=201)
async def create_post(request: Request, post: PostCreate):
    ip_hash = hashlib.sha256(request.client.host.encode()).hexdigest()
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        # try:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute('''
                SELECT * FROM boards WHERE slug=%s
            ''', (post.board_slug,))
            board = await cur.fetchone()
            if not board:
                raise HTTPException(404)
        async with conn.cursor(row_factory=class_row(Post)) as cur:
            post.tripcode = generate_tripcode(post.tripcode)
            await cur.execute('''
                INSERT INTO posts (thread_id, board_id, name, tripcode, content, ip_hash, is_op)
                VALUES (%(thread_id)s, %(board_id)s, %(name)s, %(tripcode)s, %(content)s, %(ip_hash)s, false)
                RETURNING *
            ''', {
                **post.model_dump(),
                'board_id': board.id,
                'ip_hash': ip_hash
            })
            new_post = await cur.fetchone()
            await conn.commit()
        return new_post
        # except psycopg.errors.ForeignKeyViolation:
        #     raise HTTPException(status_code=409, detail=f"La board {thread.board_id} non esiste")



@app.get("/board/{slug}")
async def get_board(slug: str):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute('SELECT * FROM boards WHERE slug=%s', (slug,))
            board = await cur.fetchone()
            if not board:
                raise HTTPException(404)
        async with conn.cursor(row_factory=class_row(Thread)) as cur:
            await cur.execute(
                'SELECT * FROM threads WHERE board_id=%s ORDER BY bump_at DESC',
                (board.id,)
            )
            threads = await cur.fetchmany(5)
        return {
            'board': board,
            'threads': threads
        }

@app.get('/board/{slug}/{thread_id}')
async def get_thread(slug: str, thread_id: int):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute('SELECT * FROM boards WHERE slug=%s', (slug,))
            board = await cur.fetchone()
            if not board:
                raise HTTPException(404)
        # async with conn.cursor(row_factory=class_row(Thread)) as cur:
        #     await cur.execute(
        #         'SELECT * FROM threads WHERE board_id=%s AND id=%s',
        #         (board.id, thread_id)
        #     )
        #     thread = await cur.fetchone()
        #     if not thread:
        #         raise HTTPException(404)
        async with conn.cursor(row_factory=class_row(Post)) as cur:
            await cur.execute(
                'SELECT * FROM posts WHERE board_id=%s AND thread_id=%s',
                (board.id, thread_id)
            )
            posts = await cur.fetchall()
            # print(posts)
            return posts

@app.get("/")
async def root():
    try:
        boards = await get_boards()
    except:
        boards = []
    return {
        "message": "Hello World",
        'boards': boards
    }

@app.get("/favicon.ico")
async def favicon():
    return {}
