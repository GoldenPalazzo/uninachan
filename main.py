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

from models import Board, Post, Thread, BoardCreate, PostCreate, ThreadCreate, Removal

DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://uninachan:secret@localhost:5432/uninachan")

def generate_tripcode(password: str | None) -> str | None:
    if password is None:
        return None
    digest = hashlib.sha1(password.encode()).digest()
    return '!' + base64.b64encode(digest).decode()[:10]

def get_ip_hash(request: Request):
    host = request.client.host if request.client else 'unknown'
    return hashlib.sha256(host.encode()).hexdigest()

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

async def get_board_from_slug(conn: psycopg.AsyncConnection, slug: str) -> Board:
    async with conn.cursor(row_factory=class_row(Board)) as cur:
        await cur.execute('SELECT * FROM boards WHERE slug=%s', (slug,))
        board = await cur.fetchone()
        if not board:
            raise HTTPException(404)
        return board

@app.get("/board/{slug}")
async def get_board(slug: str):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        board = await get_board_from_slug(conn, slug)
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

@app.post("/board", response_model=Board, status_code=201)
async def create_board(board: BoardCreate):
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor(row_factory=class_row(Board)) as cur:
                await cur.execute("""
                    INSERT INTO boards (slug, name, description, nsfw, max_threads, bump_limit)
                    VALUES (%(slug)s, %(name)s, %(description)s, %(nsfw)s, %(max_threads)s, %(bump_limit)s)
                    RETURNING *
                """, board.model_dump())
                b = await cur.fetchone()
            await conn.commit()
            return b
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail=f"Board {board.slug} esiste già")

@app.delete('/board/{slug}')
async def delete_board(slug: str):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute('DELETE FROM boards WHERE slug=%s', (slug,))
            if cur.rowcount == 0:
                raise HTTPException(404)
        await conn.commit()

@app.get('/board/{slug}/{thread_id}')
async def get_thread(slug: str, thread_id: int):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        board = await get_board_from_slug(conn, slug)
        async with conn.cursor(row_factory=class_row(Post)) as cur:
            await cur.execute(
                'SELECT * FROM posts WHERE board_id=%s AND thread_id=%s',
                (board.id, thread_id)
            )
            posts = await cur.fetchall()
            return posts

@app.post("/board/{slug}", response_model=Thread, status_code=201)
async def create_thread(request: Request, slug: str, thread: ThreadCreate) -> Thread:
    ip_hash = get_ip_hash(request)
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        try:
            board = await get_board_from_slug(conn, slug)
            async with conn.cursor(row_factory=class_row(Thread)) as cur:
                await cur.execute('''
                    INSERT INTO threads (board_id, subject)
                    VALUES (%(board_id)s, %(subject)s)
                    RETURNING *
                ''', {
                    **thread.model_dump(),
                    'board_id': board.id
                })
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
                    'board_id': board.id,
                    'ip_hash': ip_hash
                })
                new_post = await cur.fetchone()
            await conn.commit()
            new_thread.op = new_post
            return new_thread
        except psycopg.errors.ForeignKeyViolation:
            raise HTTPException(status_code=409, detail=f"La board /{slug}/ non esiste")

@app.delete('/board/{slug}/{thread_id}')
async def delete_thread(slug: str, thread_id: int):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        board = await get_board_from_slug(conn, slug)
        async with conn.cursor() as cur:
            await cur.execute(
                'DELETE FROM threads WHERE board_id=%s AND id=%s',
                (board.id, thread_id)
            )
            if cur.rowcount == 0:
                raise HTTPException(404)
        await conn.commit()

@app.post("/board/{slug}/{thread_id}", response_model=Post, status_code=201)
async def create_post(request: Request, slug: str, thread_id: int, post: PostCreate):
    ip_hash = get_ip_hash(request)
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        # try:
        board = await get_board_from_slug(conn, slug)
        async with conn.cursor(row_factory=class_row(Post)) as cur:
            post.tripcode = generate_tripcode(post.tripcode)
            await cur.execute('''
                INSERT INTO posts (thread_id, board_id, name, tripcode, content, ip_hash, is_op)
                VALUES (%(thread_id)s, %(board_id)s, %(name)s, %(tripcode)s, %(content)s, %(ip_hash)s, false)
                RETURNING *
            ''', {
                **post.model_dump(),
                'board_id': board.id,
                'thread_id': thread_id,
                'ip_hash': ip_hash
            })
            new_post = await cur.fetchone()
        await conn.commit()
        return new_post
        # except psycopg.errors.ForeignKeyViolation:
        #     raise HTTPException(status_code=409, detail=f"La board {thread.board_id} non esiste")

@app.delete('/board/{slug}/{thread_id}/{post_id}')
async def delete_post(slug: str, thread_id: int, post_id: int, removal: Removal):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        board = await get_board_from_slug(conn, slug)
        async with conn.cursor() as cur:
            await cur.execute(
                '''UPDATE posts SET removed_at=NOW(),
                                    removal_reason=%s
                   WHERE board_id=%s AND thread_id=%s AND id=%s''',
                (removal.reason, board.id, thread_id, post_id)
            )
            if cur.rowcount == 0:
                raise HTTPException(404)
        await conn.commit()



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
