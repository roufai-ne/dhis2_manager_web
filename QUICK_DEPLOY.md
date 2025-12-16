# 🚀 Guide Rapide de Déploiement - DHIS2 Manager v5.0

## ✅ Checklist Pré-Déploiement

### 1. Nettoyage du Projet
```bash
cd dhis2_manager_web

# Windows
.\cleanup.bat

# Linux/Mac
chmod +x cleanup.sh
./cleanup.sh
```

### 2. Configuration Environnement
```bash
# Copier le template
cp .env.example .env

# Générer SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Éditer .env et remplacer SECRET_KEY
nano .env  # ou notepad .env sur Windows
```

### 3. Vérification des Fichiers
```bash
# Fichiers essentiels présents
✅ Dockerfile
✅ docker-compose.yml
✅ .dockerignore
✅ requirements.txt
✅ .env (créé depuis .env.example)
✅ run.py
✅ app/

# Répertoires avec .gitkeep
✅ sessions/.gitkeep
✅ logs/.gitkeep
✅ uploads/.gitkeep
```

---

## 🐳 Déploiement Docker (Production)

### Déploiement Simple
```bash
# 1. Build
docker-compose build

# 2. Démarrer
docker-compose up -d

# 3. Vérifier
docker-compose ps
docker-compose logs -f

# 4. Test santé
curl http://localhost:5000/health
```

### Déploiement avec Nginx
```bash
# 1. Configurer SSL (optionnel)
mkdir -p nginx/ssl
# Placer cert.pem et key.pem dans nginx/ssl/

# 2. Éditer nginx/nginx.conf si nécessaire

# 3. Démarrer avec Nginx
docker-compose --profile production up -d
```

---

## 🖥️ Déploiement Manuel (Serveur Linux)

### Installation
```bash
# 1. Prérequis
sudo apt update
sudo apt install python3.11 python3-pip python3-venv nginx

# 2. Cloner/Copier le projet
cd /opt
sudo git clone <repository> dhis2-manager
cd dhis2-manager/dhis2_manager_web
sudo chown -R $USER:$USER .

# 3. Environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
nano .env  # Changer SECRET_KEY

# 5. Créer répertoires
mkdir -p logs sessions uploads
chmod 755 logs sessions uploads
```

### Service Systemd
```bash
# 1. Créer le service
sudo nano /etc/systemd/system/dhis2-manager.service
```

Contenu:
```ini
[Unit]
Description=DHIS2 Manager Web Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/dhis2-manager/dhis2_manager_web
Environment="PATH=/opt/dhis2-manager/dhis2_manager_web/venv/bin"
ExecStart=/opt/dhis2-manager/dhis2_manager_web/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 run:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# 2. Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable dhis2-manager
sudo systemctl start dhis2-manager
sudo systemctl status dhis2-manager
```

### Configuration Nginx
```bash
# 1. Créer configuration
sudo nano /etc/nginx/sites-available/dhis2-manager
```

Contenu:
```nginx
server {
    listen 80;
    server_name votre-domaine.com;
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
        alias /opt/dhis2-manager/dhis2_manager_web/app/static;
        expires 30d;
    }
}
```

```bash
# 2. Activer et redémarrer
sudo ln -s /etc/nginx/sites-available/dhis2-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL avec Let's Encrypt
```bash
# 1. Installer certbot
sudo apt install certbot python3-certbot-nginx

# 2. Obtenir certificat
sudo certbot --nginx -d votre-domaine.com

# 3. Renouvellement automatique
sudo crontab -e
# Ajouter: 0 3 * * * certbot renew --quiet
```

---

## ☁️ Déploiement Cloud

### AWS EC2
```bash
# 1. Lancer EC2 (Ubuntu 22.04, t2.medium)
# 2. Ouvrir ports 22, 80, 443 dans Security Groups
# 3. SSH vers l'instance
ssh -i key.pem ubuntu@ec2-ip

# 4. Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 5. Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 6. Déployer
git clone <repository>
cd dhis2_manager_web
cp .env.example .env
nano .env  # Configurer
docker-compose up -d
```

### DigitalOcean Droplet
```bash
# 1. Créer Droplet (Docker One-Click, 2GB RAM)
# 2. SSH vers droplet
ssh root@droplet-ip

# 3. Déployer
git clone <repository>
cd dhis2_manager_web
cp .env.example .env
nano .env
docker-compose up -d
```

### Azure VM
```bash
# 1. Créer VM (Ubuntu 22.04, Standard B2s)
# 2. Configurer NSG (ports 22, 80, 443)
# 3. Suivre les étapes AWS EC2 ci-dessus
```

---

## 🔍 Vérification Post-Déploiement

### Tests de Base
```bash
# 1. Health check
curl http://localhost:5000/health
# Attendu: {"status":"healthy","service":"dhis2-manager","version":"5.0"}

# 2. Page d'accueil
curl -I http://localhost:5000/
# Attendu: HTTP/1.1 200 OK

# 3. Logs Docker
docker-compose logs --tail=50

# 4. Logs Manuel
tail -f logs/app.log
```

### Tests Fonctionnels
- [ ] Accès à la page d'accueil
- [ ] Upload de métadonnées
- [ ] Connexion DHIS2 API
- [ ] Upload de fichier Excel
- [ ] Génération de template
- [ ] Mode automatique TCD
- [ ] Export JSON
- [ ] Envoi vers DHIS2

---

## 📊 Monitoring

### Docker
```bash
# Stats en temps réel
docker stats dhis2-manager-web

# Logs
docker-compose logs -f --tail=100

# Redémarrage
docker-compose restart
```

### Systemd
```bash
# Status
sudo systemctl status dhis2-manager

# Logs
sudo journalctl -u dhis2-manager -f

# Redémarrage
sudo systemctl restart dhis2-manager
```

---

## 🔄 Maintenance

### Mise à Jour
```bash
# Docker
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Manuel
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart dhis2-manager
```

### Nettoyage Périodique
```bash
# Automatique (cron)
0 2 * * * find /path/to/sessions/ -type f -mtime +7 -delete
0 2 * * * find /path/to/uploads/ -type f -mtime +1 -delete
0 3 * * * find /path/to/logs/ -name "*.log.*" -mtime +30 -delete
```

### Backup
```bash
# Script backup
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup-$DATE.tar.gz sessions/ .env
# Copier vers stockage distant
```

---

## 🆘 Troubleshooting Rapide

### Application ne démarre pas
```bash
# Vérifier SECRET_KEY
grep SECRET_KEY .env

# Vérifier permissions
ls -la sessions/ logs/ uploads/

# Vérifier port 5000
sudo lsof -i :5000
```

### Erreurs 502 Bad Gateway
```bash
# Vérifier que l'app tourne
curl http://127.0.0.1:5000/health

# Redémarrer nginx
sudo systemctl restart nginx

# Vérifier logs nginx
sudo tail -f /var/log/nginx/error.log
```

### Performance lente
```bash
# Augmenter workers (docker-compose.yml)
--workers 8  # Au lieu de 4

# Vérifier ressources
docker stats
top
```

---

## 📞 Support

- **Documentation complète**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Nettoyage**: [CLEANUP_GUIDE.md](CLEANUP_GUIDE.md)
- **Issues**: GitHub Issues

---

**🎉 Félicitations! Votre application DHIS2 Manager est déployée!**

Accédez à: `http://votre-domaine-ou-ip:5000`
