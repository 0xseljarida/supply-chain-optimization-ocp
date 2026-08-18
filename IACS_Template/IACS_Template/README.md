# Template LaTeX — Rapport de PFE IACS
## Intelligence Artificielle et Cybersécurité
### ENSA Béni Mellal — Université Sultan Moulay Slimane

---

## Structure du projet

```
IACS_PFE_Template/
├── main.tex                    # Fichier principal (inclut page de garde,
│                               #   frontmatter, bibliographie, annexes)
├── references.bib              # Bibliographie (BibTeX)
├── .latexmkrc                  # Configuration latexmk
├── .gitignore
├── README.md
├── config/
│   ├── packages.tex            # Packages, couleurs, styles
│   └── glossary.tex            # Acronymes et abréviations
├── chapters/
│   ├── introduction.tex        # Introduction générale
│   ├── chapter1.tex            # Chapitre I  : Contexte et problématique
│   ├── chapter2.tex            # Chapitre II : État de l'art
│   ├── chapter3.tex            # Chapitre III: Conception et réalisation
│   └── conclusion.tex          # Conclusion générale
└── figures/                    # Dossier pour les images
    └── (placer logo_ensa.png ici)
```

## Page de garde

- **Logo ENSA** à gauche (placeholder inclus, décommenter `\includegraphics`)
- **Texte université** aligné à droite (Université Sultan Moulay Slimane, ENSA, Béni Mellal)
- **N° d'ordre** aligné à droite
- **Couleur principale** : bleu foncé `#000099`
- Pas de bande latérale

## Compilation

```bash
# Avec latexmk (recommandé)
latexmk -pdf -shell-escape main.tex

# Manuellement
pdflatex -shell-escape main.tex
biber main
makeglossaries main
pdflatex -shell-escape main.tex
pdflatex -shell-escape main.tex
```

## Palette de couleurs

| Couleur          | Code HEX  | Usage                        |
|------------------|-----------|------------------------------|
| Bleu foncé       | `#000099` | Couleur principale           |
| Bleu très foncé  | `#000066` | Sections secondaires         |
| Bleu moyen       | `#3366CC` | Accents, liens               |
| Bleu très clair  | `#E8EEFF` | Fonds de boîtes              |
| Vert IA          | `#06D6A0` | Définitions, succès          |
| Orange alerte    | `#F77F00` | Avertissements               |
| Rouge alerte     | `#D62828` | Erreurs critiques            |

## Contenu intégré dans main.tex

- Page de garde TikZ
- Avant-propos, Résumé (FR), ملخص (AR), Abstract (EN)
- Dédicace, Remerciements
- Sommaire, Liste des figures/tableaux/algorithmes/abréviations
- Bibliographie (avec guide de format IEEE)
- Annexes (code Docker, tableau descriptif)

## Contenu dans les chapitres

- Figures TikZ (organigrammes, architectures, Gantt, UML, CNN, matrice de confusion)
- Tableaux colorés (tabularx, multirow, booktabs)
- Algorithmes (algorithm2e, en français)
- Code source Python (listings)
- Équations mathématiques numérotées
- Listes à puces / numérotées
- Boîtes : `\iacsnote{}`, `\iacswarning{}`, `\iacsdefinition{}{}`

---
**Filière IACS** — ENSA Béni Mellal — 2025-2026
