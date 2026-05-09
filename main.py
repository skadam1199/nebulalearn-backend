from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import student, faculty, provost

load_dotenv()

app = FastAPI(title="NebulaLearn API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(student.router, prefix="/api")
app.include_router(faculty.router, prefix="/api")
app.include_router(provost.router, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "NebulaLearn backend is running"}