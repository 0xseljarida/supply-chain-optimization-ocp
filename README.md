# Optimisation de la Supply Chain — PFA OCP

> Répondre à la demande tout en maîtrisant les coûts, la qualité et les volumes.

Projet de Fin d'Année — filière Intelligence Artificielle et Cybersécurité,
ENSA Béni Mellal. Stage au sein du groupe OCP.

## Contenu du dépôt

```
PFA_OCP/            rapport LaTeX (modèle IACS adapté au sujet)
analyse/
  src/
    stock.py            formules de gestion de stock (SS, ROP, EOQ, ABC, XYZ)
    pipeline.py         chaîne complète : export brut -> paramètres de gestion
    donnees_exemple.py  jeu de données synthétique, le temps d'obtenir le vrai
  notebooks/
    01_exploration.ipynb  exploration pas à pas
  dashboard/
    app.py              tableau de bord Streamlit
    theme.py            palette et gabarit des figures
  data/raw/           exports reçus  (jamais versionnés)
  data/processed/     résultats calculés (jamais versionnés)
IACS_Template/      modèle LaTeX d'origine, laissé intact comme référence
PFA1/               rapport de stage de l'an dernier, pour référence
```

## Installation

```bash
python3 -m venv ~/pfa
source ~/pfa/bin/activate
pip install -r analyse/requirements.txt
```

Debian interdit l'installation de paquets à l'échelle du système :
l'environnement virtuel n'est pas optionnel.

Pour compiler le rapport, il faut en plus une distribution LaTeX :

```bash
sudo apt install texlive-full latexmk biber
```

## Utilisation

```bash
source ~/pfa/bin/activate

# 1. Générer un jeu de données d'exemple (en attendant l'export OCP)
cd analyse/src && python donnees_exemple.py

# 2. Lancer la chaîne de traitement
python pipeline.py
#    ... ou sur un export réel :
python pipeline.py --source ../data/raw/export_ocp.xlsx

# 3. Ouvrir le tableau de bord
cd ../.. && streamlit run analyse/dashboard/app.py

# 4. Compiler le rapport
cd PFA_OCP && latexmk -pdf -shell-escape main.tex
```

## Données

Les données de l'OCP ne sont **jamais** versionnées : `.gitignore` exclut
`analyse/data/raw/` et `analyse/data/processed/` ainsi que tout fichier
Excel ou CSV. Seul le jeu d'exemple généré porte un nom en `exemple_*`.

## Hypothèses à valider

Trois paramètres ne proviennent pas des données et doivent être arrêtés avec
les équipes de l'OCP — ils sont regroupés en tête de `analyse/src/pipeline.py` :

| Paramètre | Valeur provisoire | À confirmer avec |
|---|---|---|
| `COUT_PASSATION` | 400 MAD par commande | Service achats |
| `TAUX_POSSESSION` | 22 % par an | Contrôle de gestion |
| Taux de service cible par segment | 85 % à 98 % | Exploitation / maintenance |

Le carnet `01_exploration.ipynb` contient une analyse de sensibilité à ces
hypothèses : à présenter avec les résultats, jamais séparément.
