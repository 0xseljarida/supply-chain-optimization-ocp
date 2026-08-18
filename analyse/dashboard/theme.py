"""Palette et gabarit Plotly du tableau de bord.

Palette validée en modes clair et sombre (séparation daltonisme et contraste).
Les couleurs sont assignées par rôle, jamais recyclées d'une figure à l'autre :
une même entité garde sa couleur partout dans le tableau de bord.
"""

from __future__ import annotations

import plotly.graph_objects as go

# --- Palette catégorielle : 3 emplacements, ordre fixe ---
CATEGORIEL = {
    "clair":  ["#2a78d6", "#eb6834", "#1baf7a"],
    "sombre": ["#3987e5", "#d95926", "#199e70"],
}

# --- Rampe séquentielle (magnitude) : une seule teinte, clair -> foncé ---
SEQUENTIEL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf",
              "#1c5cab", "#184f95", "#104281", "#0d366b"]

# --- Couleurs d'état : réservées, jamais utilisées comme couleur de série ---
ETAT = {"bon": "#0ca30c", "attention": "#fab219",
        "serieux": "#ec835a", "critique": "#d03b3b"}

CHROME = {
    "clair": {
        "surface": "#fcfcfb", "plan": "#f9f9f7",
        "encre": "#0b0b0b", "encre_secondaire": "#52514e", "encre_attenuee": "#898781",
        "grille": "#e1e0d9", "axe": "#c3c2b7",
    },
    "sombre": {
        "surface": "#1a1a19", "plan": "#0d0d0d",
        "encre": "#ffffff", "encre_secondaire": "#c3c2b7", "encre_attenuee": "#898781",
        "grille": "#2c2c2a", "axe": "#383835",
    },
}

POLICE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def couleurs(mode: str = "clair") -> dict:
    """Renvoie l'ensemble des couleurs du mode demandé."""
    c = dict(CHROME[mode])
    c["series"] = CATEGORIEL[mode]
    return c


def appliquer(fig: go.Figure, mode: str = "clair", hauteur: int = 340,
              legende: bool = False) -> go.Figure:
    """Applique le gabarit commun : chrome discret, survol actif, axes sobres.

    legende=False par défaut : une figure à série unique se passe de légende,
    son titre nomme déjà la grandeur représentée.
    """
    c = couleurs(mode)
    # La légende occupe une bande sous le titre : la marge haute la réserve,
    # sinon les deux se chevauchent.
    marge_haute = 78 if legende else 52
    fig.update_layout(
        height=hauteur,
        margin=dict(l=8, r=16, t=marge_haute, b=8),
        paper_bgcolor=c["surface"],
        plot_bgcolor=c["surface"],
        font=dict(family=POLICE, size=13, color=c["encre_secondaire"]),
        title=dict(font=dict(size=15, color=c["encre"]),
                   x=0, xanchor="left", y=1, yanchor="top", pad=dict(t=14)),
        showlegend=legende,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0, title_text="",
                    font=dict(size=12, color=c["encre_secondaire"])),
        hoverlabel=dict(font=dict(family=POLICE, size=12),
                        bgcolor=c["surface"], bordercolor=c["axe"]),
    )
    titre_axe = dict(font=dict(size=12, color=c["encre_attenuee"]))
    fig.update_xaxes(showgrid=False, zeroline=False,
                     linecolor=c["axe"], tickcolor=c["axe"],
                     title=titre_axe,
                     tickfont=dict(color=c["encre_attenuee"], size=12))
    fig.update_yaxes(showgrid=True, gridcolor=c["grille"], gridwidth=1,
                     zeroline=False, showline=False, ticks="",
                     title=titre_axe,
                     tickfont=dict(color=c["encre_attenuee"], size=12))
    return fig
