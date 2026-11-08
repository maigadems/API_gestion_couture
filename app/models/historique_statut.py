from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HistoriqueStatut(Base):
    __tablename__ = "historique_statuts"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True
    )
    ancien_statut: Mapped[str | None] = mapped_column(String(20))
    nouveau_statut: Mapped[str] = mapped_column(String(20))
    commentaire: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    date_changement: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    commande: Mapped["Commande"] = relationship(back_populates="historique")
