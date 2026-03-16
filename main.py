from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import re
import os

from fastapi import FastAPI, HTTPException
from loguru import logger
import psycopg
from psycopg.rows import class_row

from models import Board, Thread

DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://uninachan:secret@localhost:5432/uninachan")
@asynccontextmanager
async def lifespan(app: FastAPI):
    schema = Path('./schema.sql').read_text()
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(schema) # type: ignore
            await conn.commit()
            logger.info('Schema initialized')
    yield

app = FastAPI(lifespan=lifespan)

async def get_boards() -> list[Board]:
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute("SELECT * FROM boards")
            return await cur.fetchall()

@app.post("/new/board", response_model=Board, status_code=201)
async def create_board(body: Board):
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
                raise HTTPException(status_code=409, detail=f"Board /{body.slug}/ esiste già")

@app.get("/board/{slug}")
async def get_board(slug: str):
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor(row_factory=class_row(Board)) as cur:
            await cur.execute('SELECT * FROM boards WHERE slug=%s', (slug,))
            board = await cur.fetchone()
            logger.info(board)
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
