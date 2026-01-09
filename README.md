# Image Optimizer Script (Python)

Script Python pour **optimiser des images automatiquement** à partir d’un dossier source.

## Fonctionnalités

- Détection automatique **paysage / portrait**
- Redimensionnement **sans crop**
  - Le côté le plus long = **3333 px**
  - Ratio conservé
- Définition de la densité **DPI = 53**
- Compression via **TinyPNG (Tinify API)**
- Conversion vers :
  - **JPG**
  - **WEBP**
  - **AVIF** (si support installé)
- Renommage automatique des fichiers (SEO / filesystem safe)
- Parcours **récursif** possible des dossiers

---

## Prérequis

- Python **3.9+**
- pip
- Une clé API **TinyPNG**

---

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/your-repo/image-optimizer.git
cd image-optimizer
```

### 2. Installer les dépendances

```bash
pip install pillow tinify

# Pour le support AVIF - OPTIONNEL
pip install pillow-avif-plugin
```

### 3. Définir variable d'environnement

```bash
export TINIFY_KEY="VOTRE_CLE_API"
```

### 4. Commmandes

| Option             | Description                    |
| ------------------ | ------------------------------ |
| `--out ./output`   | Dossier de sortie              |
| `--recursive`      | Parcourt les sous-dossiers     |
| `--rename`         | Renomme les fichiers           |
| `--tinypng`        | Active la compression TinyPNG  |
| `--quality 85`     | Qualité JPG / WEBP / AVIF      |
| `--keep-structure` | Conserve l’arborescence source |

```bash
# Base
python optimize_images.py ./images

# Opti simple
python optimize_images.py ./images --out ./output

# Renommé + sous-dossiers
python optimize_images.py ./images --recursive --rename

# complète
python optimize_images.py ./images \
  --out ./output \
  --recursive \
  --rename \
  --tinypng \
  --quality 85
```
