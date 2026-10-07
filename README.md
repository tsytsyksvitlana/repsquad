# RepSquad

A social network for athletes: a workout journal with public/private visibility, posts with photos, follows and a feed,
likes and comments, personal records with progress charts, an AI workout planner and exercise video guides.

**Stack:** Python 3.10+, FastAPI + uvicorn, SQLite · React + Vite.

## Features

- **Accounts and profile** - sign up, sign in, profile (sport, level, goals, bio) and profile photo.
- **Workout journal** - exercises, sets, reps and weight. Every workout is **private by default** and can be made public at any time.
- **Posts** - text with an optional photo, public or private.
- **Feed and discovery** - follow people; the feed and "Discover" pages can be filtered by *All / Workouts / Posts*.
- **Likes and comments** on workouts and posts.
- **Records and progress** - personal records, estimated 1RM (Epley formula) and progress charts.
- **AI trainer** - describe the workout you want and get an editable draft based on your profile; weights are calculated from your own records.
- **Exercise videos** - a built-in YouTube guide for every exercise in the catalog.
- **Privacy** - a private item is never visible to anyone else (feed, profile, search, direct links, photos).

## Run

Requirements: Python 3.10+ and Node.js 18+.

```bash
# 1. Backend: create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate            # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Frontend: build the web app into frontend/dist
cd frontend && npm install && npm run build && cd ..

# 3. Start the server
python run.py --seed                 # create repsquad.db with demo data and start
python run.py                        # start with the existing (or empty) database; another port: python run.py 8080
```

Activate the environment (`source .venv/bin/activate`) in every new terminal before running the commands below.

Open **http://localhost:8000** (use `localhost`, not `127.0.0.1`: YouTube does not play embedded videos on an IP address).
Interactive API documentation: http://localhost:8000/docs.

Demo accounts (password `demo12345`): `olena_fit`, `taras_pl`, `iryna_run`, `max_gym`.
`python seed.py` only loads the demo data; it is safe to run repeatedly.

### AI trainer

Get a free API key at https://aistudio.google.com/apikey, copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
Optionally set `GEMINI_MODEL` to force a specific model. Without a key the rest of the app works; only the AI trainer shows a setup hint.

### Development

```bash
python run.py                        # API on :8000
cd frontend && npm run dev           # hot-reloading UI on http://localhost:5173 (proxies /api to :8000)
```

### Tests

```bash
python -m unittest discover -s tests -t .
```

## Project layout

```
backend/    FastAPI app (api.py, schemas.py), business logic (services.py), privacy rule (privacy.py),
            validation, AI module (ai.py), exercise videos (videos.py), SQLite schema (db.py)
frontend/   React app: src/pages, src/components, src/context
tests/      Automated backend tests
seed.py     Demo data        run.py   Entry point
```
