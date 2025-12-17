# Guide de Déploiement - DHIS2 Manager v5.0

## 📋 Table des matières

1. [Prérequis](#prérequis)
2. [Déploiement avec Docker](#déploiement-avec-docker)
3. [Déploiement manuel](#déploiement-manuel)
4. [Configuration](#configuration)
5. [Sécurité](#sécurité)
6. [Monitoring et Maintenance](#monitoring-et-maintenance)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Prérequis

### Pour Docker
- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum (4GB recommandé)
- 5GB espace disque

### Pour déploiement manuel
- Python 3.11+
- pip
- Serveur web (Nginx/Apache)
- 2GB RAM minimum
- 5GB espace disque

---

## 🐳 Déploiement avec Docker (Recommandé)

### 1. Préparation

```bash
# Cloner le repository
git clone <repository-url>
cd dhis2_manager_web

# Créer le fichier .env depuis l'exemple
cp .env.example .env

# Éditer .env et changer le SECRET_KEY
nano .env
```

### 2. Configuration du SECRET_KEY

Générer une clé secrète forte:

```bash
# Python 3.6+
python -c "import secrets; print(secrets.token_hex(32))"

# OU Python 2.7+ / Python 3 (toutes versions)
python -c "import os, binascii; print(binascii.hexlify(os.urandom(32)).decode())"

# OU PowerShell (Windows)
python -c "import os; import binascii; print(binascii.hexlify(os.urandom(32)).decode())"

# OU générer en ligne
# Linux/Mac: openssl rand -hex 32
```

Copier la sortie dans `.env`:
```env
SECRET_KEY=votre_cle_secrete_generee_ici
```

### 3. Build et démarrage

```bash
# Build de l'image
docker-compose build

# Démarrage en arrière-plan
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

### 4. Vérification

```bash
# Vérifier que le conteneur tourne
docker-compose ps

# Tester l'application
curl http://localhost:5000/health
```

L'application est maintenant accessible sur: **http://localhost:5000**

### 5. Déploiement avec Nginx (Production)

```bash
# Créer les certificats SSL (exemple avec Let's Encrypt)
# Ou placer vos certificats dans nginx/ssl/

# Éditer nginx/nginx.conf pour configurer votre domaine

# Démarrer avec le profil production
docker-compose --profile production up -d
```

---

## 🔨 Déploiement Manuel

### 1. Installation des dépendances

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
pip install gunicorn  # Serveur WSGI pour production
```

### 2. Configuration

```bash
# Créer .env
cp .env.example .env
nano .env

# Créer les répertoires nécessaires
mkdir -p logs sessions uploads
```

### 3. Démarrage

#### Mode développement
```bash
python run.py
```

#### Mode production avec Gunicorn
```bash
gunicorn --bind 0.0.0.0:5000 \
         --workers 4 \
         --threads 2 \
         --timeout 120 \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         run:app
```

### 4. Configuration Nginx (optionnel)

Créer `/etc/nginx/sites-available/dhis2-manager`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }

    location /static {
        alias /path/to/dhis2_manager_web/app/static;
        expires 30d;
    }
}
```

Activer et redémarrer:
```bash
sudo ln -s /etc/nginx/sites-available/dhis2-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Service Systemd

Créer `/etc/systemd/system/dhis2-manager.service`:

```ini
[Unit]
Description=DHIS2 Manager Web Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/dhis2_manager_web
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Activer et démarrer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dhis2-manager
sudo systemctl start dhis2-manager
sudo systemctl status dhis2-manager
```

---

## ⚙️ Configuration

### Variables d'environnement (.env)

| Variable | Description | Défaut | Obligatoire |
|----------|-------------|--------|-------------|
| SECRET_KEY | Clé secrète Flask | - | ✅ |
| FLASK_ENV | Environnement (production/development) | production | ❌ |
| MAX_CONTENT_LENGTH | Taille max upload (octets) | 104857600 | ❌ |
| SESSION_TYPE | Type de session | filesystem | ❌ |
| PERMANENT_SESSION_LIFETIME | Durée session (secondes) | 3600 | ❌ |
| LOG_LEVEL | Niveau de log | INFO | ❌ |

### Volumes Docker persistants

Les données suivantes sont persistées:
- `sessions/` - Sessions utilisateurs
- `logs/` - Logs applicatifs
- `uploads/` - Fichiers uploadés temporaires

---

## 🔒 Sécurité

### Checklist de sécurité

- [ ] Changer le SECRET_KEY par une valeur unique et forte
- [ ] Utiliser HTTPS en production (certificat SSL/TLS)
- [ ] Configurer un pare-feu (UFW, iptables)
- [ ] Limiter l'accès réseau au minimum nécessaire
- [ ] Mettre à jour régulièrement les dépendances
- [ ] Activer les logs et monitoring
- [ ] Configurer des backups réguliers
- [ ] Utiliser des mots de passe forts pour DHIS2
- [ ] Restreindre les permissions des fichiers

### Génération de certificats SSL

#### Avec Let's Encrypt (gratuit)
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

#### Auto-signé (développement uniquement)
```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

### Sécurisation des fichiers

```bash
# Permissions appropriées
chmod 600 .env
chmod 700 sessions/ logs/ uploads/
chown -R www-data:www-data sessions/ logs/ uploads/
```

---

## 📊 Monitoring et Maintenance

### Vérification de santé

```bash
# Docker
docker-compose exec dhis2-manager curl http://localhost:5000/health

# Manuel
curl http://localhost:5000/health
```

### Logs

```bash
# Docker - Logs en temps réel
docker-compose logs -f

# Docker - Logs des 100 dernières lignes
docker-compose logs --tail=100

# Manuel
tail -f logs/app.log
tail -f logs/access.log
tail -f logs/error.log
```

### Nettoyage

```bash
# Nettoyer les sessions expirées (à planifier avec cron)
find sessions/ -type f -mtime +7 -delete

# Nettoyer les anciens logs
find logs/ -name "*.log.*" -mtime +30 -delete

# Nettoyer les uploads temporaires
find uploads/ -type f -mtime +1 -delete
```

### Cron jobs suggérés

```cron
# Nettoyage quotidien à 2h du matin
0 2 * * * find /path/to/dhis2_manager_web/sessions/ -type f -mtime +7 -delete
0 2 * * * find /path/to/dhis2_manager_web/uploads/ -type f -mtime +1 -delete

# Backup quotidien
0 3 * * * /path/to/backup-script.sh
```

### Mise à jour

```bash
# Docker
git pull
docker-compose down
docker-compose build
docker-compose up -d

# Manuel
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart dhis2-manager
```

---

## 🐛 Troubleshooting

### L'application ne démarre pas

```bash
# Vérifier les logs
docker-compose logs dhis2-manager

# Vérifier la configuration
docker-compose config

# Reconstruire l'image
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Erreurs de permission

```bash
# Corriger les permissions
sudo chown -R 1000:1000 sessions/ logs/ uploads/
sudo chmod -R 755 sessions/ logs/ uploads/
```

### Erreur "Secret key required"

```bash
# Vérifier que .env existe et contient SECRET_KEY
cat .env | grep SECRET_KEY

# Si absent, le générer
# Python 3.6+
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env

# OU Python 2.7+ / toutes versions
echo "SECRET_KEY=$(python -c 'import os, binascii; print(binascii.hexlify(os.urandom(32)).decode())')" >> .env
```

### Uploads échouent

```bash
# Vérifier MAX_CONTENT_LENGTH
grep MAX_CONTENT_LENGTH .env

# Augmenter la limite (100MB = 104857600)
echo "MAX_CONTENT_LENGTH=104857600" >> .env

# Pour Nginx, vérifier aussi client_max_body_size
```

### Performance lente

```bash
# Augmenter le nombre de workers Gunicorn
# Formule: (2 x CPU cores) + 1
# Éditer docker-compose.yml ou commande gunicorn

# Surveiller l'utilisation des ressources
docker stats dhis2-manager
```

### Erreurs de connexion DHIS2

- Vérifier que l'URL DHIS2 est accessible
- Tester avec curl: `curl -u username:password https://dhis2-url/api/system/info`
- Vérifier les credentials
- Vérifier le pare-feu/proxy

---

## 📞 Support

### Logs utiles pour le support

```bash
# Collecter les informations de débogage
docker-compose logs --tail=500 > debug.log
docker-compose ps >> debug.log
docker stats --no-stream >> debug.log
cat .env | grep -v SECRET_KEY >> debug.log
```

### Informations système

```bash
docker version
docker-compose version
python --version
uname -a
```

---

## 🚀 Déploiement sur serveurs cloud

### AWS EC2
1. Lancer une instance EC2 (Ubuntu 22.04 LTS)
2. Installer Docker et Docker Compose
3. Ouvrir les ports 80, 443 dans Security Groups
4. Suivre les étapes de déploiement Docker

### Azure VM
1. Créer une VM (Ubuntu 22.04 LTS)
2. Installer Docker et Docker Compose
3. Configurer NSG pour ports 80, 443
4. Suivre les étapes de déploiement Docker

### DigitalOcean Droplet
1. Créer un Droplet avec Docker One-Click App
2. SSH vers le droplet
3. Cloner et déployer l'application
4. Configurer un domaine dans DNS

---

## 📝 Notes importantes

- **Backups**: Sauvegardez régulièrement `sessions/` si vous stockez des données critiques
- **Sécurité**: Ne jamais commiter `.env` dans Git
- **Performance**: Ajustez le nombre de workers selon vos ressources
- **Maintenance**: Planifiez des fenêtres de maintenance pour les mises à jour

---

**Version**: 5.0  
**Dernière mise à jour**: Décembre 2025
