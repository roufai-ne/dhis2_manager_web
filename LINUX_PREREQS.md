# 📦 Prérequis Linux - DHIS2 Manager v5.0

## Installation des Paquets Requis

### Pour Ubuntu/Debian

```bash
# Mise à jour des paquets
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Installer Git
sudo apt install -y git

# REDÉMARRER la session pour que Docker fonctionne sans sudo
# Déconnectez-vous et reconnectez-vous, ou:
newgrp docker
```

### Pour CentOS/RHEL/Fedora

```bash
# Mise à jour
sudo yum update -y

# Installer Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Installer Git
sudo yum install -y git

# Redémarrer session
newgrp docker
```

---

## ⚠️ IMPORTANT: Avec Docker, Python n'est PAS nécessaire!

**Docker inclut tout ce qui est nécessaire** dans l'image. Vous n'avez pas besoin d'installer Python sur votre machine Linux.

### Pourquoi?
- L'image Docker contient Python 3.11
- Toutes les dépendances sont dans le conteneur
- Votre système reste propre

---

## Vérification de l'Installation

```bash
# Vérifier Docker
docker --version
# Attendu: Docker version 20.10+ ou plus récent

docker-compose --version
# Attendu: Docker Compose version 2.0+ ou plus récent

# Vérifier Git
git --version
# Attendu: git version 2.x+

# Tester Docker (sans sudo)
docker run hello-world
# Si erreur "permission denied", relancer: newgrp docker
```

---

## Déploiement avec Docker (Recommandé)

```bash
# 1. Cloner le projet
git clone <url-repository>
cd dhis2_manager_web

# 2. Copier .env
cp .env.example .env

# 3. Générer SECRET_KEY (sur votre machine locale ou avec Docker)
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_hex(32))"

# 4. Éditer .env et coller la clé
nano .env

# 5. Build et démarrer
docker-compose build
docker-compose up -d

# 6. Vérifier
docker-compose ps
curl http://localhost:5000/health
```

---

## Déploiement Manuel (Si vous ne voulez PAS Docker)

### Paquets Requis

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    build-essential libpq-dev nginx git curl

# CentOS/RHEL
sudo yum install -y python3.11 python3-pip gcc gcc-c++ \
    postgresql-devel nginx git curl
```

### Installation

```bash
# 1. Aller dans le répertoire
cd /opt
sudo git clone <url-repository> dhis2-manager
cd dhis2-manager/dhis2_manager_web
sudo chown -R $USER:$USER .

# 2. Créer environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# 3. Installer dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
# Générer SECRET_KEY
python -c "import os, binascii; print(binascii.hexlify(os.urandom(32)).decode())"
# Éditer .env et coller la clé
nano .env

# 5. Créer répertoires
mkdir -p logs sessions uploads
chmod 755 logs sessions uploads

# 6. Démarrer
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app
```

---

## Configuration Pare-feu

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Ressources Minimales

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| RAM | 2 GB | 4 GB |
| CPU | 1 core | 2 cores |
| Disque | 5 GB | 10 GB |
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |

---

## Troubleshooting Installation

### Docker: "permission denied"
```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Redémarrer session
newgrp docker

# OU se déconnecter/reconnecter
exit
# SSH à nouveau
```

### Python 3.11 non disponible (Ubuntu < 22.04)
```bash
# Ajouter PPA deadsnakes
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### Port 5000 déjà utilisé
```bash
# Trouver le processus
sudo lsof -i :5000

# Tuer le processus
sudo kill -9 <PID>

# OU utiliser un autre port dans docker-compose.yml
ports:
  - "8000:5000"  # Accéder via port 8000
```

---

## Prochaines Étapes

### Avec Docker (Recommandé) ✅
1. ✅ Installer Docker + Docker Compose + Git
2. ✅ Cloner le projet
3. ✅ Configurer .env
4. ✅ `docker-compose up -d`
5. ✅ Accéder à http://server-ip:5000

### Sans Docker
1. ✅ Installer Python 3.11 + dépendances
2. ✅ Suivre les étapes d'installation manuelle
3. ✅ Configurer Nginx + Systemd
4. ✅ Configurer SSL

**Recommandation**: Utilisez Docker pour une installation plus simple et isolée! 🐳
