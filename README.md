# UNINAchan

Image board scritta in Python 3.14+.

## Introduzione

Questo progetto didattico è stato creato per imparare ad usare FastAPI con un
database PostgreSQL.

Non ha la prerogativa di funzionare su larga scala ed essere un punto di 
riferimento per complottismi, razzismo o bigotterie varie che infestano altre
image board preesistenti come 4chan, 8chan e altra spazzatura.

## Uso

### Docker

Consiglio caldamente di usare `docker compose` se si desidera lanciare
l'intero stack di questo repo + postgresql.

Il `Dockerfile` dovrebbe essere sufficiente per poter essere integrato in file
`compose.yml` preesistenti.

Altrimenti se si decide di lanciare tutto a mano o comunque setuppare il repo
per sviluppo, seguire le istruzioni sotto.

#### Sample `compose.yml`

```yml
services:
  api:
    build: ./backend
    ports:
      - 8000:8000
    env_file:
      - path: ./api.env
        required: true
    depends_on:
      - db
  db:
    image: postgres:18-alpine
    restart: unless-stopped
    shm_size: 128mb
    ports:
      - 5432:5432
    env_file:
      - path: ./postgres.env
        required: true
```

dove `./backend` è la cartella dove risiede questo repo.

### Setup python

È necessario `uv` per poter usare questo progetto.

Una volta clonato questo repository, va sincronizzato il virtual environment
con

```bash
$ uv sync
```

### Setup postgresql

Attualmente la documentazione per questa sezione sarà assente: basti sapere
che si deve creare un server postgresql la cui url è salvata nella variabile
`DATABASE_URL` in `main.py`.

### Esecuzione

```bash
$ uv run fastapi run main.py
```

## Licenza

Questo software è distribuito secondo licenza MIT, permettendo uso
commerciale, redistribuzione, modifica ed uso privato.

## Collaborazioni

Qualsiasi pr e fork sono ben accetti.
