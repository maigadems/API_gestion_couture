from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True
    )
    type_vetement_id: Mapped[int] = mapped_column(ForeignKey("types_vetement.id"))
    description: Mapped[str | None] = mapped_column(Text)
    quantite: Mapped[int] = mapped_column(Integer)
    prix_unitaire: Mapped[int] = mapped_column(Integer)

    commande: Mapped["Commande"] = relationship(back_populates="lignes")
    type_vetement: Mapped["TypeVetement"] = relationship()

    @property
    def type_vetement_nom(self) -> str:
        return self.type_vetement.nom

    @property
    def sous_total(self) -> int:
        return self.quantite * self.prix_unitaire
