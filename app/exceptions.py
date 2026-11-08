class ErreurMetier(Exception):
    """Erreur levée par les services : elle décrit le problème, pas le format HTTP."""

    status_code = 400
    headers: dict[str, str] | None = None

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NonAuthentifie(ErreurMetier):
    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}


class Interdit(ErreurMetier):
    status_code = 403


class Introuvable(ErreurMetier):
    status_code = 404


class Conflit(ErreurMetier):
    status_code = 409


class DonneesInvalides(ErreurMetier):
    status_code = 422
