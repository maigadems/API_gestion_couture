from fastapi import HTTPException


def route_a_implementer() -> HTTPException:
    return HTTPException(status_code=501, detail="Route à implémenter")
