import random
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg
from psycopg.rows import class_row

DATABASE_URL = "postgresql://postgres:example@localhost:5432/postgres"
app = FastAPI()

class User(BaseModel):
    name: str

def get_users() -> list[User]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=class_row(User)) as cur:
            cur.execute("SELECT * FROM users")
            return cur.fetchall()

@app.get("/")
async def root():
    return {
        "message": "Hello World",
        'existing_users': get_users()
    }

@app.get('/createuser')
async def newuser(username: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO users (name) VALUES (%s)", (username,))
                conn.commit() # Commit the changes to the database
            except psycopg.errors.UniqueViolation as e:
                return {'error': f'User {username} already exists'}
    users = get_users()
    print(users)
    return {
        'message': f'Creato nuovo utente {username}',
        'existing_users': get_users()
    }
