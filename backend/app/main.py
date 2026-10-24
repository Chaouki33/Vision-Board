from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_schema
from .routers import admin, auth, companies, datasets, kpis, reports, templates

# Création des tables au démarrage ; les migrations (Alembic) viendront avec PostgreSQL.
create_schema()

app = FastAPI(title="Vision Board API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, admin.router, companies.router, templates.router, datasets.router, kpis.router,
               reports.router):
    app.include_router(router, prefix="/api")


@app.get("/", include_in_schema=False)
def home():
    """Le port de l'API n'est pas l'application : on indique où aller."""
    return {
        "message": "API Vision Board en ligne. L'application s'ouvre sur l'adresse du frontend.",
        "application": settings.cors_origins[0],
        "documentation_api": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
