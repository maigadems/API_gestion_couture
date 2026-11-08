from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.workflow import est_en_retard


class Commande(Base):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    mesure_id: Mapped[int | None] = mapped_column(ForeignKey("mesures.id"))
    statut: Mapped[str] = mapped_column(String(20), default="en_attente", index=True)
    date_commande: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    date_livraison_prevue: Mapped[date] = mapped_column(Date)
    date_livraison_reelle: Mapped[date | None] = mapped_column(Date)
    remise: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    montant_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    montant_paye: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship()
    mesure: Mapped["Mesure | None"] = relationship()
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="LigneCommande.id"
    )
    historique: Mapped[list["HistoriqueStatut"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="HistoriqueStatut.id",
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="Paiement.id"
    )
    livraison: Mapped["Livraison | None"] = relationship(
        back_populates="commande", cascade="all, delete-orphan", uselist=False
    )

    # Valeurs calculées, utilisées par les schémas de lecture
    @property
    def client_nom(self) -> str:
        return f"{self.client.prenom} {self.client.nom}"

    @property
    def solde(self) -> int:
        return self.montant_total - self.montant_paye

    @property
    def en_retard(self) -> bool:
        return est_en_retard(self.date_livraison_prevue, self.statut)
