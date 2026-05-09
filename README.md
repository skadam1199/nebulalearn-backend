# NebulaLearn Backend

FastAPI backend powering 6 AI agents for NebulaLearn.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Create a `.env` file:
```
OPENAI_API_KEY=your_key_here
```

## Run locally

```bash
uvicorn main:app --reload
```

API runs at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/health | Health check |
| POST | /api/process | Student: process video |
| POST | /api/search | Student: semantic search |
| POST | /api/translate | Translate any content |
| POST | /api/faculty-audit | Faculty: pedagogical audit |
| POST | /api/curriculum-map | Provost: curriculum mapping |

## File structure

```
nebulalearn-backend/
├── main.py                    # FastAPI app
├── requirements.txt
├── .env                       # Your API keys (never commit)
├── agents/
│   ├── agent1_ingestion.py    # YouTube transcript extraction
│   ├── agent2_synthesis.py    # Outline, summaries, flashcards
│   ├── agent3_search.py       # Semantic search
│   ├── agent4_pedagogy.py     # Faculty audit
│   ├── agent5_translation.py  # Translation
│   └── agent6_curriculum.py   # Curriculum mapping
└── routers/
    ├── student.py
    ├── faculty.py
    └── provost.py
```