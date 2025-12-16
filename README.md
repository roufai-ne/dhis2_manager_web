# DHIS2 Data Manager - Web Edition v5.0

Une plateforme web moderne pour la transformation et le formatage de données DHIS2, développée avec Flask et Python.

**Auteur:** Amadou Roufai  
**Version:** 5.0 Web Edition  
**Date:** Décembre 2025

## 📋 Table des Matières

- [Aperçu](#-aperçu)
- [Fonctionnalités](#-fonctionnalités)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Architecture](#-architecture)
- [Déploiement](#-déploiement)
- [Dépannage](#-dépannage)

## 🎯 Aperçu

DHIS2 Data Manager est une application web qui facilite la préparation et la transformation de données pour l'importation dans DHIS2. Elle permet de :

- ✅ Importer et valider des métadonnées DHIS2
- ✅ Générer des templates Excel formatés pour la saisie
- ✅ Traiter les données et générer des payloads JSON DHIS2
- ✅ Valider les données avant l'import

## ✨ Fonctionnalités

### Module Configuration
- Import de fichiers JSON de métadonnées DHIS2
- Validation automatique de structure
- Statistiques détaillées (organisations, datasets, éléments)
- Gestion de session sécurisée

### Module Générateur
- Création de templates Excel pré-formatés
- Sélection hiérarchique des organisations (jsTree)
- Support de tous les types de période DHIS2
- Protection des colonnes techniques

### Module Calculateur
- Import et traitement d'Excel remplis
- Validation complète des données
- Génération de payload JSON compatible DHIS2
- Rapport d'erreurs détaillé

### Interface Utilisateur
- Design responsive avec Tailwind CSS
- Notifications toast animées
- Upload par drag & drop
- États de chargement visuels

## 🚀 Installation

### Prérequis

- **Python**: 3.14.0 ou supérieur
- **pip**: Gestionnaire de packages Python
- **Espace disque**: ~100 MB

### Étapes

1. **Cloner ou télécharger le projet**

2. **Créer un environnement virtuel**
```bash
python -m venv venv
```

3. **Activer l'environnement**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

5. **Configuration**
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

6. **Lancer l'application**
```bash
python run.py
```

Application accessible sur: `http://localhost:5000`

## 📖 Utilisation

### Workflow Complet

#### 1. Configuration
1. Module **Configuration**
2. Importer JSON métadonnées DHIS2
3. Vérifier les statistiques

#### 2. Génération
1. Module **Générateur**
2. Sélectionner dataset et organisations
3. Entrer période (ex: 2024, 202401)
4. Télécharger template Excel

#### 3. Saisie
1. Ouvrir Excel téléchargé
2. Remplir colonne **value** uniquement
3. Ne pas modifier colonnes techniques

#### 4. Calcul
1. Module **Calculateur**
2. Importer Excel rempli
3. Traiter et vérifier statistiques
4. Télécharger JSON

#### 5. Import DHIS2
- Via Import/Export dans DHIS2
- Ou via API: `POST /api/dataValueSets`

## 🏗️ Architecture

### Stack Technique

**Backend:**
- Flask 3.0.0
- Python 3.14.0
- pandas 2.2.0+
- openpyxl 3.1.2

**Frontend:**
- Tailwind CSS 3.4.0
- jQuery 3.7.1
- Dropzone.js 5
- jsTree 3.3.15

### Structure

```
dhis2_manager_web/
├── app/
│   ├── routes/         # Routes Flask
│   ├── services/       # Logique métier
│   ├── templates/      # Templates HTML
│   └── static/         # CSS, JS
├── sessions/           # Sessions temporaires
├── venv/              # Environnement virtuel
├── .env               # Configuration
├── requirements.txt   # Dépendances
└── run.py            # Point d'entrée
```

## 🚢 Déploiement

### Production avec Gunicorn

1. **Installer Gunicorn**
```bash
pip install gunicorn
```

2. **Configuration Production**
```env
FLASK_ENV=production
SECRET_KEY=votre-clé-secrète
```

3. **Lancer**
```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

### Avec Nginx

Configuration `/etc/nginx/sites-available/dhis2-manager`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /path/to/dhis2_manager_web/app/static;
    }

    client_max_body_size 50M;
}
```

### Service Systemd

`/etc/systemd/system/dhis2-manager.service`:

```ini
[Unit]
Description=DHIS2 Data Manager
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/dhis2_manager_web
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🐛 Dépannage

### Problèmes Courants

**Application ne démarre pas:**
```bash
python --version  # Vérifier >= 3.14
pip install --upgrade -r requirements.txt
```

**Sessions expirées:**
- Augmenter `PERMANENT_SESSION_LIFETIME` dans `.env`

**Erreurs de chemin:**
- Vérifier que `sessions/` existe à la racine
- Permissions d'écriture

**Fichiers Excel corrompus:**
```bash
pip install --upgrade pandas openpyxl
```

### Logs

Activer debug mode dans `run.py`:
```python
app.run(debug=True)
```

## 📝 Support

- Page **Aide** dans l'application
- Vérifier les logs
- Contacter: Amadou Roufai

---

**Version:** 5.0 Web Edition  
**Dernière mise à jour:** Décembre 2025
