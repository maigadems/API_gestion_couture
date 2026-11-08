from datetime import date

from app.exceptions import Conflit

# Statut actuel -> statuts qu'il est possible de poser ensuite.
TRANSITIONS: dict[str, set[str]] = {
    "en_attente": {"en_coupe", "annulee"},
    "en_coupe": {"en_couture", "annulee"},
    "en_couture": {"essayage", "terminee", "annulee"},
    "essayage": {"retouches", "terminee", "annulee"},
    "retouches": {"essayage", "terminee", "annulee"},
    "terminee": {"livree"},
    "livree": set(),
    "annulee": set(),
}

TOUS_LES_STATUTS = list(TRANSITIONS)
STATUTS_FINAUX = ("livree", "annulee")


def statuts_possibles(actuel: str) -> list[str]:
    """Statuts qu'on peut poser par la route de changement de statut.

    « livree » n'en fait pas partie : il résulte de la confirmation de livraison.
    """
    return sorted(TRANSITIONS[actuel] - {"livree"})


def verifier_transition(actuel: str, cible: str) -> None:
    if cible == actuel:
        raise Conflit(f"La commande est déjà au statut « {actuel} »")
    if cible == "livree":
        raise Conflit(
            "Le statut « livree » ne peut pas être posé directement : "
            "il résulte de la confirmation de livraison"
        )
    if cible not in TRANSITIONS[actuel]:
        possibles = statuts_possibles(actuel)
        if possibles:
            liste = ", ".join(possibles)
        elif actuel == "terminee":
            liste = "aucun (la remise au client se confirme par la livraison)"
        else:
            liste = "aucun (statut final)"
        raise Conflit(f"Transition interdite : {actuel} → {cible}. Statuts possibles : {liste}")


def est_en_retard(date_livraison_prevue: date, statut: str, aujourdhui: date | None = None) -> bool:
    """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
    aujourdhui = aujourdhui or date.today()
    return date_livraison_prevue < aujourdhui and statut not in STATUTS_FINAUX
