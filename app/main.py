from fastapi import FastAPI

from app.routers import (
    auth,
    clients,
    utilisateurs,
)

app = FastAPI(title="API Atelier de couture")

app.include_router(utilisateurs.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
