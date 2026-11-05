from typing import Annotated

from pydantic import BaseModel, StringConstraints

TexteNonVide = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
