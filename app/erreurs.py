from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ErreurMetier


async def gerer_erreur_metier(request: Request, exc: ErreurMetier) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
    )


def enregistrer_gestionnaires(app: FastAPI) -> None:
    app.add_exception_handler(ErreurMetier, gerer_erreur_metier)
