from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginer(db: Session, requete: Select, limit: int, offset: int, *options) -> dict:
    """Exécute une requête de liste et renvoie la page au format de l'API."""
    total = db.scalar(select(func.count()).select_from(requete.order_by(None).subquery()))
    items = db.scalars(requete.options(*options).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
