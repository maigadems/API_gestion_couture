from datetime import date, timedelta

import pytest

from app.exceptions import Conflit
from app.services.workflow import (
    STATUTS_FINAUX,
    TRANSITIONS,
    est_en_retard,
    statuts_possibles,
    verifier_transition,
)


def test_table_des_transitions_conforme_a_l_enonce():
    assert TRANSITIONS == {
        "en_attente": {"en_coupe", "annulee"},
        "en_coupe": {"en_couture", "annulee"},
        "en_couture": {"essayage", "terminee", "annulee"},
        "essayage": {"retouches", "terminee", "annulee"},
        "retouches": {"essayage", "terminee", "annulee"},
        "terminee": {"livree"},
        "livree": set(),
        "annulee": set(),
    }


def test_statuts_possibles_tries_et_sans_livree():
    assert statuts_possibles("en_attente") == ["annulee", "en_coupe"]
    assert statuts_possibles("terminee") == []
    assert statuts_possibles("livree") == []


def test_message_de_transition_interdite_cite_les_statuts_possibles():
    with pytest.raises(Conflit) as erreur:
        verifier_transition("en_attente", "terminee")
    assert erreur.value.detail == (
        "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe"
    )


def test_rg13_meme_statut_refuse():
    with pytest.raises(Conflit, match="déjà au statut"):
        verifier_transition("en_coupe", "en_coupe")


def test_rg13_livree_jamais_pose_directement():
    with pytest.raises(Conflit, match="confirmation de livraison"):
        verifier_transition("terminee", "livree")


def test_transition_autorisee_ne_leve_rien():
    verifier_transition("retouches", "essayage")


@pytest.mark.parametrize("statut", STATUTS_FINAUX)
def test_statuts_finaux_sans_issue(statut):
    with pytest.raises(Conflit, match="aucun"):
        verifier_transition(statut, "en_coupe")


def test_rg11_en_retard_seulement_si_date_depassee_et_statut_non_final():
    aujourdhui = date(2026, 6, 15)
    hier, demain = aujourdhui - timedelta(days=1), aujourdhui + timedelta(days=1)
    assert est_en_retard(hier, "en_couture", aujourdhui)
    assert not est_en_retard(aujourdhui, "en_couture", aujourdhui)
    assert not est_en_retard(demain, "en_couture", aujourdhui)
    assert not est_en_retard(hier, "livree", aujourdhui)
    assert not est_en_retard(hier, "annulee", aujourdhui)
