"""Formules de gestion des stocks.

Toutes les fonctions sont vectorisées : elles acceptent indifféremment des
scalaires ou des tableaux NumPy / Series pandas, ce qui permet de les appliquer
à l'ensemble du portefeuille de références en une seule opération.

Convention d'unités : la demande et le délai doivent être exprimés dans la même
unité de temps (par exemple demande mensuelle et délai en mois).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

JOURS_PAR_AN = 365.0


# ---------------------------------------------------------------------------
# Stock de sécurité et point de commande
# ---------------------------------------------------------------------------

def coefficient_securite(taux_service):
    """Coefficient z correspondant à un taux de service cible.

    taux_service : probabilité de ne pas être en rupture sur un cycle,
                   strictement comprise entre 0 et 1 (ex. 0.95).
    """
    taux_service = np.asarray(taux_service, dtype=float)
    if np.any((taux_service <= 0) | (taux_service >= 1)):
        raise ValueError("taux_service doit être strictement compris entre 0 et 1")
    return norm.ppf(taux_service)


def stock_securite(sigma_demande, demande_moyenne, delai_moyen,
                   sigma_delai=0.0, taux_service=0.95):
    """Stock de sécurité avec demande et délai incertains.

        SS = z * sqrt(L * sigma_d^2 + d_moyen^2 * sigma_L^2)

    Poser sigma_delai=0 revient au cas classique SS = z * sigma_d * sqrt(L).
    """
    z = coefficient_securite(taux_service)
    variance = (np.asarray(delai_moyen, dtype=float) * np.asarray(sigma_demande, dtype=float) ** 2
                + np.asarray(demande_moyenne, dtype=float) ** 2
                * np.asarray(sigma_delai, dtype=float) ** 2)
    return z * np.sqrt(variance)


def point_de_commande(demande_moyenne, delai_moyen, stock_secu):
    """Niveau de stock déclenchant le réapprovisionnement : ROP = d * L + SS."""
    return np.asarray(demande_moyenne, dtype=float) * np.asarray(delai_moyen, dtype=float) + stock_secu


# ---------------------------------------------------------------------------
# Quantité de commande
# ---------------------------------------------------------------------------

def quantite_economique(demande_annuelle, cout_passation, cout_possession_unitaire):
    """Quantité économique de commande (modèle de Wilson) : Q* = sqrt(2DS/H).

    cout_possession_unitaire : coût annuel de possession d'une unité, soit le
    produit du taux de possession par la valeur unitaire de l'article.
    """
    demande_annuelle = np.asarray(demande_annuelle, dtype=float)
    cout_possession_unitaire = np.asarray(cout_possession_unitaire, dtype=float)
    if np.any(cout_possession_unitaire <= 0):
        raise ValueError("cout_possession_unitaire doit être strictement positif")
    return np.sqrt(2.0 * demande_annuelle * cout_passation / cout_possession_unitaire)


def cout_total_annuel(quantite, demande_annuelle, cout_passation,
                      cout_possession_unitaire):
    """Coût annuel de passation + possession pour une quantité de commande donnée."""
    quantite = np.asarray(quantite, dtype=float)
    return (demande_annuelle / quantite * cout_passation
            + quantite / 2.0 * cout_possession_unitaire)


# ---------------------------------------------------------------------------
# Indicateurs de performance
# ---------------------------------------------------------------------------

def taux_rotation(consommation_annuelle, stock_moyen):
    """Nombre de renouvellements du stock sur l'année."""
    stock_moyen = np.asarray(stock_moyen, dtype=float)
    return np.divide(consommation_annuelle, stock_moyen,
                     out=np.full_like(stock_moyen, np.nan, dtype=float),
                     where=stock_moyen > 0)


def couverture_jours(consommation_annuelle, stock_moyen):
    """Nombre de jours de consommation couverts par le stock moyen."""
    rotation = taux_rotation(consommation_annuelle, stock_moyen)
    return np.divide(JOURS_PAR_AN, rotation,
                     out=np.full_like(np.asarray(rotation, dtype=float), np.nan),
                     where=rotation > 0)


def coefficient_variation(serie_demande, axis=-1):
    """CV = écart-type / moyenne. Renvoie NaN si la demande moyenne est nulle."""
    serie = np.asarray(serie_demande, dtype=float)
    moyenne = np.nanmean(serie, axis=axis)
    ecart_type = np.nanstd(serie, axis=axis, ddof=1)
    return np.divide(ecart_type, moyenne,
                     out=np.full_like(np.atleast_1d(moyenne), np.nan, dtype=float),
                     where=np.atleast_1d(moyenne) > 0)


# ---------------------------------------------------------------------------
# Classification du portefeuille
# ---------------------------------------------------------------------------

def classer_abc(valeurs, seuils=(0.80, 0.95)):
    """Classification ABC par valeur cumulée décroissante (principe de Pareto).

    valeurs : valeur de consommation annuelle par référence (array-like).
    seuils  : parts cumulées séparant A/B puis B/C.

    Convention retenue : une référence appartient à la classe A si la valeur
    cumulée *après* l'avoir incluse reste sous le premier seuil. La référence
    qui franchit un seuil bascule donc dans la classe inférieure. C'est une
    convention parmi d'autres ; à mentionner dans le rapport.

    Renvoie un tableau de labels 'A', 'B' ou 'C' dans l'ordre d'entrée.
    """
    valeurs = np.asarray(valeurs, dtype=float)
    total = np.nansum(valeurs)
    if total <= 0:
        raise ValueError("la valeur totale du portefeuille doit être positive")

    ordre = np.argsort(-np.nan_to_num(valeurs))
    cumul = np.cumsum(valeurs[ordre]) / total

    labels_tries = np.where(cumul <= seuils[0], "A",
                            np.where(cumul <= seuils[1], "B", "C"))

    labels = np.empty(valeurs.shape, dtype="<U1")
    labels[ordre] = labels_tries
    return labels


def classer_xyz(cv, seuils=(0.5, 1.0)):
    """Classification XYZ par régularité de la demande.

    X : demande régulière (CV <= seuils[0])
    Y : demande variable  (seuils[0] < CV <= seuils[1])
    Z : demande erratique (CV > seuils[1], ou CV indéfini)
    """
    cv = np.asarray(cv, dtype=float)
    return np.where(np.isnan(cv), "Z",
                    np.where(cv <= seuils[0], "X",
                             np.where(cv <= seuils[1], "Y", "Z")))
