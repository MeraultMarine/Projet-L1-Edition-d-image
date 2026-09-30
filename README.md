# Éditeur d'image Python

Petit éditeur d'image avec interface graphique, développé en Python avec **Tkinter**, **Pillow**, **NumPy** et **SciPy**.

>Projet réalisé en L1 pour découvrir la création d'interfaces graphiques avec Tkinter et le traitement d'image par manipulation de matrices de pixels.

## Fonctionnalités

**Fichier**
- Ouvrir une image (PNG, JPEG, etc.)
- Sauvegarder en PNG ou JPEG

**Filtres simples**
- Filtre vert
- Niveaux de gris
- Négatif
- Symétrie horizontale
- Fusion de deux images (avec curseur de mélange)
- Détection de bords (filtre de Sobel)

**Réglages avec aperçu en temps réel**
- Luminosité
- Contraste (courbe sigmoïde)
- Flou uniforme
- Flou gaussien
- Pixellisation

**Historique**
- Annuler / refaire (20 états)

## Raccourcis

| Raccourci | Action |
|-----------|--------|
| `Ctrl + Z` | Annuler |
| `Ctrl + Y` | Refaire |
| `Ctrl + S` | Sauvegarder |



## Utilisation

1. `Fichier > Ouvrir` pour charger une image.
2. Choisis un filtre dans le menu Filtres ou Réglages.
3. Pour les réglages, ajuste le curseur (aperçu en direct) puis clique sur Appliquer ou Annuler.
4. `Fichier > Sauvegarde` pour enregistrer le résultat.

## Principe

| Effet | Méthode |
|-------|---------|
| Niveaux de gris | Moyenne des canaux R, G, B |
| Négatif | `255 - pixel` |
| Luminosité | Multiplication par un facteur puis écrêtage à [0, 255] |
| Contraste | Sigmoïde renormalisée |
| Flou uniforme | Moyenne sur un voisinage `n × n` |
| Flou gaussien | Convolution avec un noyau 3×3 gaussien |
| Détection de bords | Flou gaussien + opérateur de Sobel + seuillage |
| Pixellisation | Réduction puis agrandissement en *nearest neighbor* |

## Dépendances

- Pillow
- NumPy
- SciPy
- Tkinter (inclus avec Python)
