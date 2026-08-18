"""Génération d'un jeu de données synthétique.

Sert uniquement à développer et tester la chaîne de traitement en attendant
l'export réel de l'OCP. La structure des colonnes reproduit celle décrite en
annexe B du rapport ; elle devra être ajustée dès réception des vraies données.

Usage :
    python -m donnees_exemple           (depuis analyse/src/)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "data" / "raw" / "exemple_mouvements.xlsx"

FAMILLES = ["Roulements", "Courroies", "Filtres", "Pompes",
            "Électrique", "Robinetterie", "Lubrifiants"]
FOURNISSEURS = [f"FRS-{i:02d}" for i in range(1, 13)]


def generer(n_articles=300, date_debut="2023-01-01", date_fin="2025-12-31", graine=42):
    """Construit une table de mouvements de stock plausible.

    Trois profils de demande sont mélangés pour que la classification XYZ ait
    du sens : régulière, saisonnière et intermittente.
    """
    rng = np.random.default_rng(graine)
    jours = pd.date_range(date_debut, date_fin, freq="D")
    jours_np = jours.to_numpy()
    jour_de_lannee = np.asarray(jours.dayofyear, dtype=float)

    articles = pd.DataFrame({
        "code_article": [f"ART-{i:05d}" for i in range(1, n_articles + 1)],
        "famille": rng.choice(FAMILLES, n_articles),
        "fournisseur": rng.choice(FOURNISSEURS, n_articles),
        # Valeur unitaire très dispersée : c'est ce qui fait exister la classe A.
        "prix_unitaire": np.round(rng.lognormal(mean=4.0, sigma=1.6, size=n_articles), 2),
        "delai_theorique": rng.choice([15, 30, 45, 60, 90], n_articles),
        "profil": rng.choice(["regulier", "saisonnier", "intermittent"],
                             n_articles, p=[0.35, 0.25, 0.40]),
    })

    lignes = []
    for art in articles.itertuples(index=False):
        if art.profil == "regulier":
            n_mouvements = rng.integers(120, 300)
            taille = lambda k: np.maximum(1, rng.normal(20, 4, k).round())
        elif art.profil == "saisonnier":
            n_mouvements = rng.integers(60, 160)
            taille = lambda k: np.maximum(1, rng.normal(25, 12, k).round())
        else:  # intermittent
            n_mouvements = rng.integers(3, 25)
            taille = lambda k: np.maximum(1, rng.poisson(4, k))

        if art.profil == "saisonnier":
            # Pics en début et milieu d'année (arrêts techniques).
            poids = 1 + 0.9 * np.sin(2 * np.pi * jour_de_lannee / 182.5) ** 2
            poids = poids / poids.sum()
            dates = rng.choice(jours_np, size=n_mouvements, p=poids)
        else:
            dates = rng.choice(jours_np, size=n_mouvements)

        quantites = taille(n_mouvements).astype(int)
        lignes.append(pd.DataFrame({
            "code_article": art.code_article,
            "designation": f"{art.famille} réf. {art.code_article[-5:]}",
            "famille": art.famille,
            "fournisseur": art.fournisseur,
            "date_mouvement": pd.to_datetime(dates),
            "type_mouvement": "SORTIE",
            "quantite": quantites,
            "prix_unitaire": art.prix_unitaire,
            # Délai réel = délai théorique + retard, souvent positif :
            # c'est cette dispersion qui alimente sigma_L.
            "delai_livraison": np.maximum(
                1, art.delai_theorique + rng.normal(5, 12, n_mouvements)).round().astype(int),
        }))

    mouvements = pd.concat(lignes, ignore_index=True)
    mouvements = mouvements.sort_values("date_mouvement").reset_index(drop=True)

    # Stock disponible simulé, cohérent avec l'ordre de grandeur des sorties.
    conso_moy = mouvements.groupby("code_article")["quantite"].mean()
    mouvements["stock_disponible"] = (
        mouvements["code_article"].map(conso_moy)
        * rng.uniform(3, 40, len(mouvements))
    ).round().astype(int)

    return mouvements


if __name__ == "__main__":
    df = generer()
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(SORTIE, index=False)
    print(f"{len(df):,} mouvements pour {df['code_article'].nunique()} articles")
    print(f"période : {df['date_mouvement'].min():%Y-%m-%d} -> {df['date_mouvement'].max():%Y-%m-%d}")
    print(f"écrit dans : {SORTIE}")
