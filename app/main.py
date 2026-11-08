from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.erreurs import enregistrer_gestionnaires
from app.routers import (
    auth,
    catalogue,
    clients,
    commandes,
    livraisons,
    mesures,
    paiements,
    statistiques,
    utilisateurs,
)

app = FastAPI(title="API Atelier de couture")
enregistrer_gestionnaires(app)

app.include_router(utilisateurs.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(catalogue.router, prefix="/api/v1")
app.include_router(mesures.router, prefix="/api/v1")
app.include_router(paiements.router, prefix="/api/v1")
app.include_router(livraisons.router, prefix="/api/v1")
app.include_router(commandes.router, prefix="/api/v1")
app.include_router(statistiques.router, prefix="/api/v1")


@app.get("/health", tags=["Santé"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Base de données indisponible")
    return {"status": "ok"}
