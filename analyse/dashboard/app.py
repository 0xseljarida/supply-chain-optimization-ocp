"""Tableau de bord d'aide à la décision — gestion des stocks.

Lancement :
    streamlit run analyse/dashboard/app.py

Le tableau de bord lit le fichier produit par analyse/src/pipeline.py. Si ce
fichier n'existe pas, il propose de lancer la chaîne de traitement sur le jeu
de données d'exemple.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import stock                      # noqa: E402
import theme                      # noqa: E402

FICHIER_PARAMETRES = RACINE / "data" / "processed" / "parametres_stock.xlsx"

st.set_page_config(page_title="Gestion des stocks — OCP",
                   page_icon="📦", layout="wide")


# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------

@st.cache_data
def charger_parametres(chemin: Path):
    params = pd.read_excel(chemin, sheet_name="Parametres", index_col=0)
    conso = pd.read_excel(chemin, sheet_name="Conso_mensuelle", index_col=0)
    return params, conso


def mode_couleur() -> str:
    """Aligne la palette des figures sur le thème actif de Streamlit."""
    return "sombre" if st.get_option("theme.base") == "dark" else "clair"


def format_mad(valeur: float) -> str:
    """Formate un montant en milliers de MAD, séparateur d'espace."""
    return f"{valeur:,.0f}".replace(",", " ")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def figure_pareto(params: pd.DataFrame, mode: str) -> go.Figure:
    """Courbe de Pareto : part cumulée de la valeur consommée."""
    c = theme.couleurs(mode)
    valeurs = params["valeur_conso_annuelle"].sort_values(ascending=False)
    cumul = 100 * valeurs.cumsum() / valeurs.sum()
    rang = 100 * (pd.Series(range(1, len(cumul) + 1)) / len(cumul))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rang, y=cumul.to_numpy(), mode="lines",
        line=dict(color=c["series"][0], width=2),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
        hovertemplate="%{x:.0f} %% des références<br>"
                      "%{y:.0f} %% de la valeur<extra></extra>",
    ))
    # Repère du seuil A : lu directement, sans avoir à croiser deux axes.
    fig.add_hline(y=80, line=dict(color=c["axe"], width=1, dash="dot"),
                  annotation_text="80 % de la valeur",
                  annotation_font=dict(color=c["encre_attenuee"], size=12),
                  annotation_position="top right")

    fig.update_layout(title="Concentration de la valeur consommée")
    fig.update_xaxes(title_text="Part cumulée des références (%)", ticksuffix=" %")
    fig.update_yaxes(title_text="Part cumulée de la valeur (%)",
                     range=[0, 101], ticksuffix=" %")
    return theme.appliquer(fig, mode)


def figure_matrice(params: pd.DataFrame, mode: str) -> go.Figure:
    """Matrice ABC x XYZ : nombre de références par segment."""
    c = theme.couleurs(mode)
    table = (pd.crosstab(params["classe_abc"], params["classe_xyz"])
             .reindex(index=["A", "B", "C"], columns=["X", "Y", "Z"], fill_value=0))

    fig = go.Figure(go.Heatmap(
        z=table.to_numpy(), x=list(table.columns), y=list(table.index),
        colorscale=[[i / (len(theme.SEQUENTIEL) - 1), col]
                    for i, col in enumerate(theme.SEQUENTIEL)],
        xgap=2, ygap=2,                       # gap de surface entre les cases
        showscale=False,
        text=table.to_numpy(), texttemplate="%{text}",
        textfont=dict(size=15, family=theme.POLICE),
        hovertemplate="Segment %{y}%{x} : %{z} références<extra></extra>",
    ))
    fig.update_layout(
        title="Références par segment — ABC (valeur) × XYZ (régularité)")
    fig.update_xaxes(title_text="", side="top", showline=False, ticks="")
    fig.update_yaxes(title_text="", autorange="reversed")
    return theme.appliquer(fig, mode, hauteur=300)


def figure_valeur_par_classe(params: pd.DataFrame, mode: str) -> go.Figure:
    """Valeur de stock actuelle et cible, par classe ABC."""
    c = theme.couleurs(mode)
    agg = (params.groupby("classe_abc")[["valeur_stock_actuel", "valeur_stock_cible"]]
           .sum().reindex(["A", "B", "C"]).fillna(0) / 1000)

    fig = go.Figure()
    for i, (colonne, nom) in enumerate([("valeur_stock_actuel", "Stock actuel"),
                                        ("valeur_stock_cible", "Stock cible")]):
        fig.add_trace(go.Bar(
            x=list(agg.index), y=agg[colonne], name=nom,
            marker=dict(color=c["series"][i], cornerradius=4),
            text=[f"{v:,.0f}".replace(",", " ") for v in agg[colonne]],
            textposition="outside",
            textfont=dict(color=c["encre_secondaire"], size=12),
            hovertemplate=nom + " — classe %{x}<br>%{y:,.0f} kMAD<extra></extra>",
        ))
    fig.update_layout(title="Valeur de stock par classe ABC (kMAD)",
                      barmode="group", bargap=0.35, bargroupgap=0.06)
    fig.update_yaxes(title_text="")
    return theme.appliquer(fig, mode, legende=True)


def figure_arbitrage(params: pd.DataFrame, mode: str) -> go.Figure:
    """Valeur totale du stock de sécurité en fonction du taux de service cible.

    C'est la figure d'arbitrage : elle montre à partir de quel niveau chaque
    point de service supplémentaire devient disproportionnellement coûteux.
    """
    c = theme.couleurs(mode)
    taux = [0.80, 0.85, 0.90, 0.925, 0.95, 0.96, 0.97, 0.98, 0.99, 0.995, 0.999]

    delai_mois = params["delai_moyen_j"] / 30.0
    ecart_delai_mois = params["delai_ecart_j"].fillna(0.0) / 30.0
    valeurs = []
    for t in taux:
        ss = stock.stock_securite(
            sigma_demande=params["demande_mensuelle_ecart"].fillna(0.0),
            demande_moyenne=params["demande_mensuelle_moy"],
            delai_moyen=delai_mois, sigma_delai=ecart_delai_mois,
            taux_service=t)
        valeurs.append(float((ss * params["prix_unitaire"]).sum()) / 1000)

    fig = go.Figure(go.Scatter(
        x=[100 * t for t in taux], y=valeurs, mode="lines+markers",
        line=dict(color=c["series"][0], width=2),
        marker=dict(size=8, color=c["series"][0],
                    line=dict(width=2, color=c["surface"])),
        hovertemplate="Taux de service %{x:.1f} %%<br>"
                      "Stock de sécurité %{y:,.0f} kMAD<extra></extra>",
    ))
    fig.update_layout(title="Arbitrage taux de service / valeur du stock de sécurité")
    fig.update_xaxes(title_text="Taux de service cible (%)", ticksuffix=" %")
    fig.update_yaxes(title_text="Stock de sécurité (kMAD)")
    return theme.appliquer(fig, mode)


def figure_historique(conso: pd.DataFrame, code: str, mode: str) -> go.Figure:
    """Historique mensuel de consommation d'une référence."""
    c = theme.couleurs(mode)
    serie = conso.loc[code]

    fig = go.Figure(go.Bar(
        x=list(serie.index), y=serie.to_numpy(),
        marker=dict(color=c["series"][0], cornerradius=4),
        hovertemplate="%{x}<br>%{y:,.0f} unités<extra></extra>",
    ))
    fig.update_layout(title=f"Consommation mensuelle — {code}", bargap=0.3)
    fig.update_yaxes(title_text="Quantité")
    return theme.appliquer(fig, mode, hauteur=300)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("Gestion des stocks — tableau de bord")

if not FICHIER_PARAMETRES.exists():
    st.warning(
        f"Fichier introuvable : `{FICHIER_PARAMETRES}`\n\n"
        "Lancer d'abord la chaîne de traitement :\n\n"
        "```bash\n"
        "cd analyse/src\n"
        "python donnees_exemple.py   # jeu de données d'exemple\n"
        "python pipeline.py\n"
        "```")
    st.stop()

params, conso = charger_parametres(FICHIER_PARAMETRES)
mode = mode_couleur()

# --- Filtres : une seule rangée, au-dessus des figures ---
f1, f2, f3 = st.columns([2, 2, 2])
familles = f1.multiselect("Famille", sorted(params["famille"].dropna().unique()))
classes = f2.multiselect("Classe ABC", ["A", "B", "C"])
segments = f3.multiselect("Régularité XYZ", ["X", "Y", "Z"])

vue = params
if familles:
    vue = vue[vue["famille"].isin(familles)]
if classes:
    vue = vue[vue["classe_abc"].isin(classes)]
if segments:
    vue = vue[vue["classe_xyz"].isin(segments)]

if vue.empty:
    st.info("Aucune référence ne correspond à ces filtres.")
    st.stop()

# --- Indicateurs de tête ---
actuel = vue["valeur_stock_actuel"].sum() / 1000
cible = vue["valeur_stock_cible"].sum() / 1000
ecart = cible - actuel
dormantes = int((vue["part_mois_sans_conso"] >= 0.9).sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Références", f"{len(vue):,}".replace(",", " "))
k2.metric("Valeur stock actuelle", f"{format_mad(actuel)} kMAD")
k3.metric("Valeur stock cible", f"{format_mad(cible)} kMAD",
          delta=f"{format_mad(ecart)} kMAD", delta_color="inverse")
k4.metric("Références quasi dormantes", f"{dormantes}",
          help="Aucune consommation sur au moins 90 % des mois de la période")

st.divider()

g1, g2 = st.columns(2)
g1.plotly_chart(figure_pareto(vue, mode), width='stretch')
g2.plotly_chart(figure_matrice(vue, mode), width='stretch')

g3, g4 = st.columns(2)
g3.plotly_chart(figure_valeur_par_classe(vue, mode), width='stretch')
g4.plotly_chart(figure_arbitrage(vue, mode), width='stretch')

st.divider()

# --- Fiche par référence ---
st.subheader("Fiche référence")
code = st.selectbox("Référence", sorted(vue.index),
                    format_func=lambda c: f"{c} — {params.loc[c, 'designation']}")

fiche = params.loc[code]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Segment", fiche["segment"])
c2.metric("Stock de sécurité", f"{fiche['stock_securite']:,.0f}".replace(",", " "))
c3.metric("Point de commande", f"{fiche['point_commande']:,.0f}".replace(",", " "))
c4.metric("Quantité de commande", f"{fiche['quantite_commande']:,.0f}".replace(",", " "))

st.plotly_chart(figure_historique(conso, code, mode), width='stretch')

st.divider()

# --- Vue tableau : lecture sans dépendre de la couleur, et export ---
st.subheader("Tableau des paramètres")
colonnes = ["designation", "famille", "classe_abc", "classe_xyz", "segment",
            "demande_mensuelle_moy", "cv", "delai_moyen_j", "taux_service_cible",
            "stock_securite", "point_commande", "quantite_commande",
            "valeur_stock_actuel", "valeur_stock_cible", "ecart_valeur"]
st.dataframe(vue[colonnes], width='stretch', height=380)

st.download_button(
    "Exporter la sélection (CSV)",
    vue[colonnes].to_csv().encode("utf-8"),
    file_name="parametres_stock.csv", mime="text/csv")
