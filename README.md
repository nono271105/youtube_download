# YouTube Video Downloader 🎬

Une application graphique moderne pour télécharger facilement des vidéos ou de l’audio depuis YouTube, réalisée avec Python, CustomTkinter et yt-dlp.

## Fonctionnalités

- Téléchargement de vidéos YouTube en plusieurs qualités (1080p, 720p, 480p, 360p)
- Téléchargement de l’audio uniquement (MP3)
- Affichage des informations de la vidéo (titre, durée, auteur)
- Sélection du dossier de destination

## Installation

1. **Clone le dépôt ou copie le fichier `YTB DWNL.py` dans un dossier.**
2. **Installe les dépendances nécessaires :**

```sh
pip install customtkinter yt-dlp
```

> **Remarque :** Pour la conversion audio MP3, `ffmpeg` doit être installé sur le système.

### Installer ffmpeg sur Mac :

```sh
brew install ffmpeg
```

## Utilisation

Lance simplement le script :

```sh
python YTB\ DWNL.py
```

- Colle le lien d’une vidéo YouTube.
- Choisis la qualité ou "Audio uniquement".
- Sélectionne le dossier de destination si besoin.
- Clique sur "Télécharger" !
- Tu peux aussi cliquer sur "Obtenir les informations" pour voir les détails de la vidéo avant de télécharger.
