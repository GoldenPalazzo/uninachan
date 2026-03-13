import random
from fastapi import FastAPI

app = FastAPI()
utenti = []

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get('/createuser')
async def newuser():
    new_user = f'NuovoUtente{random.randint(1,100)}'
    utenti.append(new_user)
    return {
        'message': f'Creato nuovo utente {new_user}',
        'existing_users': utenti
    }
