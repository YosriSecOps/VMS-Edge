# Plateforme de Surveillance Vidéo Intelligente 🛡️📹

Une application moderne de vidéosurveillance intelligente développée en Python. Elle utilise la vision par ordinateur (OpenCV) et le Machine Learning pour la reconnaissance faciale, couplée à un tatouage numérique (Watermarking DCT) pour sécuriser les preuves (Forensique) et un système d'alerte en temps réel via Telegram.

## 🌟 Fonctionnalités Principales

*   **Multithreading Dynamique** : Supporte l'ajout à la volée de multiples caméras (Webcam USB, Caméras IP/Smartphones) sans aucun ralentissement.
*   **Intelligence Artificielle Isolée** : Chaque flux vidéo exécute sa propre boucle de détection (Haar Cascade) et de reconnaissance faciale (LBPH).
*   **Système d'Anti-Spam Telegram** : Filtre intelligent des alertes (Cooldown de 15s) pour envoyer des notifications sur votre téléphone (avec photo) sans vous spammer ou surcharger l'API.
*   **Sécurisation Forensique (DCT)** : Chaque capture de visage non autorisé est tatouée numériquement (Watermark invisible) avec la date et le nom de la caméra, garantissant l'authenticité de la preuve juridique.
*   **Dashboard UI/UX Premium** : Interface graphique moderne et fluide développée avec `CustomTkinter` (Mode Sombre, Glassmorphism, Grilles dynamiques).
*   **Recherche Avancée & Statistiques** : Base de données SQLite embarquée avec moteur de recherche (par caméra, plage horaire, statut) et graphiques analytiques (Matplotlib).
*   **Conformité RGPD** : Script de nettoyage intégré pour supprimer automatiquement les données vidéo obsolètes.

## 🚀 Installation & Lancement

1. Clonez ce dépôt :
   ```bash
   git clone https://github.com/votre-nom/surveillance-intelligente.git
   cd surveillance-intelligente
   ```

2. Installez les dépendances requises :
   ```bash
   pip install -r requirements.txt
   ```

3. Lancez le Dashboard principal :
   ```bash
   python admin_dashboard.py
   ```

## 🔐 Configuration Telegram (Important)
Pour activer les alertes sur votre téléphone :
1. Créez un Bot sur Telegram via **@BotFather** et obtenez votre `TOKEN`.
2. Trouvez votre `CHAT_ID` via **@userinfobot**.
3. Dans le fichier `dynamic_surveillance.py`, remplacez les variables `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID` par vos identifiants.

*(Note: Ces variables ne doivent jamais être uploadées telles quelles sur GitHub pour des raisons de sécurité).*

## 🛠️ Stack Technique
*   **Langage** : Python 3.11+
*   **Interface Graphique** : CustomTkinter (UI), Matplotlib (Charts)
*   **Vision par ordinateur** : OpenCV, Pillow
*   **Base de données** : SQLite3
*   **Réseau** : Module Requests (API REST Telegram)

## 👤 Auteur
Projet développé dans le cadre de la création d'une architecture distribuée robuste.
