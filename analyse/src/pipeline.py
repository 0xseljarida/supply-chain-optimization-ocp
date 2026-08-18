"""Chaîne de traitement : de l'export brut aux paramètres de gestion.

Étapes : chargement -> contrôles -> agrégation mensuelle -> segmentation
ABC/XYZ -> calcul des paramètres (SS, ROP, EOQ) -> export.

Usage :
    python pipeline.py                       (depuis analyse/src/)
    python pipeline.py --source ../data/raw/mon_export.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import stock

RACINE = Path(__file__).resolve().parents[1]
SOURCE_DEFAUT = RACINE / "data" / "raw" / "exemple_mouvements.xlsx"
SORTIE_DEFAUT = RACINE / "data" / "processed" / "parametres_stock.xlsx"

# --- Hypothèses de coûts : à valider avec les services concernés ---
COUT_PASSATION = 400.0      # coût de passation d'une commande (MAD)
TAUX_POSSESSION = 0.22      # coût annuel de possession, en % de la valeur article
TAUX_SERVICE_DEFAUT = 0.95


# ---------------------------------------------------------------------------

def charger(source: Path) -> pd.DataFrame:
    """Lit l'export et normalise les types."""
    lire = pd.read_excel if source.suffix in {".xlsx", ".xls"} else pd.read_csv
    df = lire(source)
    df["date_mouvement"] = pd.to_datetime(df["date_mouvement"])
    return df


def controler(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applique les contrôles de qualité et renvoie (données nettoyées, journal).

    Le journal alimente le tableau 'Contrôles de qualité' du rapport.
    """
    journal = []
    n0 = len(df)

    df = df.drop_duplicates()
    journal.append(("Doublons supprimés", n0 - len(df)))

    n = len(df)
    df = df.dropna(subset=["code_article", "date_mouvement", "quantite"])
    journal.append(("Lignes à champ clé manquant", n - len(df)))

    n = len(df)
    df = df[df["quantite"] > 0]
    journal.append(("Quantités nulles ou négatives", n - len(df)))

    journal.append(("Lignes retenues", len(df)))
    journal.append(("Références distinctes", df["code_article"].nunique()))

    return df.reset_index(drop=True), pd.DataFrame(journal, columns=["Contrôle", "Nombre"])


def consommation_mensuelle(df: pd.DataFrame) -> pd.DataFrame:
    """Matrice références x mois, les mois sans consommation valant 0.

    Le remplissage par des zéros est essentiel : sans lui, le coefficient de
    variation serait sous-estimé pour les articles à demande intermittente.
    """
    sorties = df[df["type_mouvement"] == "SORTIE"].copy()
    sorties["mois"] = sorties["date_mouvement"].dt.to_period("M")

    conso = (sorties.groupby(["code_article", "mois"])["quantite"].sum()
             .unstack(fill_value=0))

    mois_complets = pd.period_range(sorties["mois"].min(), sorties["mois"].max(), freq="M")
    return conso.reindex(columns=mois_complets, fill_value=0)


def profil_articles(df: pd.DataFrame, conso: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par référence : demande, variabilité, délai, valeur."""
    n_mois = conso.shape[1]

    profil = pd.DataFrame(index=conso.index)
    profil["demande_mensuelle_moy"] = conso.mean(axis=1)
    profil["demande_mensuelle_ecart"] = conso.std(axis=1, ddof=1)
    profil["demande_annuelle"] = profil["demande_mensuelle_moy"] * 12
    profil["mois_sans_conso"] = (conso == 0).sum(axis=1)
    profil["part_mois_sans_conso"] = profil["mois_sans_conso"] / n_mois

    attributs = (df.groupby("code_article")
                 .agg(designation=("designation", "first"),
                      famille=("famille", "first"),
                      fournisseur=("fournisseur", "first"),
                      prix_unitaire=("prix_unitaire", "median"),
                      delai_moyen_j=("delai_livraison", "mean"),
                      delai_ecart_j=("delai_livraison", "std"),
                      stock_actuel=("stock_disponible", "last")))

    profil = profil.join(attributs)
    profil["valeur_conso_annuelle"] = profil["demande_annuelle"] * profil["prix_unitaire"]
    profil["cv"] = stock.coefficient_variation(conso.to_numpy(), axis=1)
    return profil


def segmenter(profil: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les classes ABC, XYZ et le segment croisé."""
    profil = profil.copy()
    profil["classe_abc"] = stock.classer_abc(profil["valeur_conso_annuelle"].to_numpy())
    profil["classe_xyz"] = stock.classer_xyz(profil["cv"].to_numpy())
    profil["segment"] = profil["classe_abc"] + profil["classe_xyz"]
    return profil


def taux_service_par_segment(segment: pd.Series) -> pd.Series:
    """Taux de service cible différencié : plus la référence pèse, plus on protège.

    Ces valeurs sont un point de départ à arbitrer avec les équipes.
    """
    cible = {"AX": 0.98, "AY": 0.97, "AZ": 0.95,
             "BX": 0.95, "BY": 0.95, "BZ": 0.92,
             "CX": 0.92, "CY": 0.90, "CZ": 0.85}
    return segment.map(cible).fillna(TAUX_SERVICE_DEFAUT)


def calculer_parametres(profil: pd.DataFrame,
                        taux_service=None) -> pd.DataFrame:
    """Calcule SS, ROP et EOQ pour chaque référence.

    Demande et délai sont ramenés au mois pour rester homogènes.
    """
    res = profil.copy()
    if taux_service is None:
        taux_service = taux_service_par_segment(res["segment"])
    res["taux_service_cible"] = taux_service

    delai_mois = res["delai_moyen_j"] / 30.0
    ecart_delai_mois = res["delai_ecart_j"].fillna(0.0) / 30.0

    res["stock_securite"] = stock.stock_securite(
        sigma_demande=res["demande_mensuelle_ecart"].fillna(0.0),
        demande_moyenne=res["demande_mensuelle_moy"],
        delai_moyen=delai_mois,
        sigma_delai=ecart_delai_mois,
        taux_service=res["taux_service_cible"],
    )
    res["point_commande"] = stock.point_de_commande(
        res["demande_mensuelle_moy"], delai_mois, res["stock_securite"])

    cout_possession = TAUX_POSSESSION * res["prix_unitaire"]
    res["quantite_commande"] = stock.quantite_economique(
        res["demande_annuelle"], COUT_PASSATION, cout_possession)

    # Stock moyen cible = demi-lot de réapprovisionnement + stock de sécurité.
    res["stock_cible_moyen"] = res["quantite_commande"] / 2.0 + res["stock_securite"]
    res["valeur_stock_actuel"] = res["stock_actuel"] * res["prix_unitaire"]
    res["valeur_stock_cible"] = res["stock_cible_moyen"] * res["prix_unitaire"]
    res["ecart_valeur"] = res["valeur_stock_cible"] - res["valeur_stock_actuel"]

    res["rotation_actuelle"] = stock.taux_rotation(
        res["demande_annuelle"], res["stock_actuel"])
    res["rotation_cible"] = stock.taux_rotation(
        res["demande_annuelle"], res["stock_cible_moyen"])

    return res.round(2)


def executer(source: Path = SOURCE_DEFAUT, sortie: Path = SORTIE_DEFAUT):
    df = charger(source)
    df, journal = controler(df)
    conso = consommation_mensuelle(df)
    profil = segmenter(profil_articles(df, conso))
    parametres = calculer_parametres(profil)

    sortie.parent.mkdir(parents=True, exist_ok=True)
    conso_export = conso.copy()
    conso_export.columns = conso_export.columns.astype(str)
    with pd.ExcelWriter(sortie) as writer:
        parametres.to_excel(writer, sheet_name="Parametres")
        journal.to_excel(writer, sheet_name="Controles", index=False)
        conso_export.to_excel(writer, sheet_name="Conso_mensuelle")

    return parametres, journal, conso


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=SOURCE_DEFAUT)
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    args = ap.parse_args()

    parametres, journal, conso = executer(args.source, args.sortie)

    print(journal.to_string(index=False))
    print()
    print("Répartition par segment :")
    print(pd.crosstab(parametres["classe_abc"], parametres["classe_xyz"]))
    print()
    print(f"Valeur stock actuelle : {parametres['valeur_stock_actuel'].sum():>15,.0f}")
    print(f"Valeur stock cible    : {parametres['valeur_stock_cible'].sum():>15,.0f}")
    print(f"Écart                 : {parametres['ecart_valeur'].sum():>15,.0f}")
    print()
    print(f"écrit dans : {args.sortie}")
