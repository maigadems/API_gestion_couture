from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import ErreurMetier

MESSAGES_HTTP = {404: "Ressource introuvable", 405: "Méthode non autorisée"}


async def gerer_erreur_metier(request: Request, exc: ErreurMetier) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
    )


def _texte(erreur: dict) -> str:
    type_ = erreur["type"]
    ctx = erreur.get("ctx") or {}
    msg = erreur["msg"]
    if type_ == "missing":
        return "champ obligatoire"
    if type_ in ("int_parsing", "int_type", "int_from_float"):
        return "doit être un nombre entier"
    if type_ in ("float_parsing", "float_type"):
        return "doit être un nombre"
    if type_ in ("bool_parsing", "bool_type"):
        return "doit être vrai ou faux"
    if type_ == "string_type":
        return "doit être un texte"
    if type_ in ("date_parsing", "date_type", "date_from_datetime_parsing"):
        return "doit être une date valide au format AAAA-MM-JJ"
    if type_ == "string_too_short":
        return f"doit contenir au moins {ctx.get('min_length')} caractère(s)"
    if type_ == "string_too_long":
        return f"ne doit pas dépasser {ctx.get('max_length')} caractères"
    if type_ == "too_short":
        return f"doit contenir au moins {ctx.get('min_length')} élément(s)"
    if type_ == "greater_than":
        return f"doit être strictement supérieur à {ctx.get('gt')}"
    if type_ == "greater_than_equal":
        return f"doit être supérieur ou égal à {ctx.get('ge')}"
    if type_ == "less_than":
        return f"doit être strictement inférieur à {ctx.get('lt')}"
    if type_ == "less_than_equal":
        return f"doit être inférieur ou égal à {ctx.get('le')}"
    if type_ in ("enum", "literal_error"):
        return f"valeur non autorisée (valeurs possibles : {ctx.get('expected')})"
    if type_ == "json_invalid":
        return "le corps de la requête n'est pas un JSON valide"
    if type_ == "value_error":
        texte = msg.removeprefix("Value error, ")
        if texte.startswith("value is not a valid email address"):
            return "adresse e-mail invalide"
        return texte
    return msg


def traduire_erreur(erreur: dict) -> str:
    if erreur["type"] == "json_invalid":
        return "Le corps de la requête n'est pas un JSON valide"
    champ =".".join(str(p) for p in erreur["loc"] if p not in ("body", "query", "path"))
    texte = _texte(erreur)
    if champ:
        return f"{champ} : {texte}"
    return texte[:1].upper() + texte[1:]


async def gerer_erreur_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    messages = [traduire_erreur(erreur) for erreur in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": " ; ".join(messages)})


async def gerer_erreur_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = MESSAGES_HTTP.get(exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": detail}, headers=exc.headers
    )


def enregistrer_gestionnaires(app: FastAPI) -> None:
    app.add_exception_handler(ErreurMetier, gerer_erreur_metier)
    app.add_exception_handler(RequestValidationError, gerer_erreur_validation)
    app.add_exception_handler(StarletteHTTPException, gerer_erreur_http)
