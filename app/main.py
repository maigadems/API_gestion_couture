from fastapi import FastAPI

from app.routers import (
    auth,
    catalogue,
    clients,
    livraisons,
    mesures,
    paiements,
    utilisateurs,
)

app = FastAPI(title="API Atelier de couture")

app.include_router(utilisateurs.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(catalogue.router, prefix="/api/v1")
app.include_router(mesures.router, prefix="/api/v1")
app.include_router(paiements.router, prefix="/api/v1")
app.include_router(livraisons.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
