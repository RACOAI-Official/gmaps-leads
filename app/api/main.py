from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import jobs, leads

app = FastAPI(title="gmaps-leads API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}
