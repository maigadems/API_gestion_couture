from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Livraison(Base):
    __tablename__ = "livraisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique : une seule livraison par commande
    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), unique=True
    )
    mode: Mapped[str] = mapped_column(String(20))
    adresse: Mapped[str | None] = mapped_column(Text)
    livreur: Mapped[str | None] = mapped_column(String(100))
    date_prevue: Mapped[date] = mapped_column(Date)
    date_effective: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(20), default="planifiee")
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped["Commande"] = relationship(back_populates="livraison")

    # Valeurs calculées pour la liste de tournée
    @property
    def numero_commande(self) -> str:
        return self.commande.numero

    @property
    def client_nom(self) -> str:
        return self.commande.client_nom

    @property
    def client_telephone(self) -> str:
        return self.commande.client.telephone

    @property
    def solde_commande(self) -> int:
        return self.commande.solde
