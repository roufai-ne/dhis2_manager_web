#!/bin/bash
# Installation de Docker Engine sur Ubuntu Focal (20.04)
# Script automatique pour DHIS2 Manager v5.0

set -e

echo "==================================="
echo "Installation Docker sur Ubuntu 20.04"
echo "==================================="

# 1. Désinstaller anciennes versions
echo ""
echo "1/7 - Nettoyage des anciennes installations..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# 2. Mise à jour
echo ""
echo "2/7 - Mise à jour des paquets..."
sudo apt-get update

# 3. Installation des prérequis
echo ""
echo "3/7 - Installation des prérequis..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 4. Ajout de la clé GPG Docker
echo ""
echo "4/7 - Ajout de la clé GPG Docker..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 5. Ajout du repository Docker
echo ""
echo "5/7 - Ajout du repository Docker..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 6. Installation Docker Engine
echo ""
echo "6/7 - Installation de Docker Engine..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 7. Configuration permissions
echo ""
echo "7/7 - Configuration des permissions..."
sudo usermod -aG docker $USER

# Démarrage Docker
echo ""
echo "Démarrage de Docker..."
sudo systemctl start docker
sudo systemctl enable docker

# Vérification
echo ""
echo "==================================="
echo "Vérification de l'installation"
echo "==================================="
echo ""
docker --version
docker compose version
echo ""

# Test
echo "Test de Docker..."
sudo docker run hello-world

echo ""
echo "==================================="
echo "✅ Installation terminée!"
echo "==================================="
echo ""
echo "⚠️  IMPORTANT: Vous devez vous déconnecter et reconnecter"
echo "    pour que les permissions du groupe docker soient effectives."
echo ""
echo "    Ensuite, testez avec:"
echo "    docker run hello-world"
echo ""
echo "    Si vous voyez une erreur de permission, lancez:"
echo "    newgrp docker"
echo ""
