#!/bin/bash

# Script de nettoyage pour DHIS2 Manager
# Supprime les fichiers temporaires et de développement

echo "🧹 Nettoyage des fichiers inutiles..."

# Répertoire de base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Compteur
count=0

# Supprimer __pycache__
echo "Suppression des __pycache__..."
find "$BASE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
count=$((count + $(find "$BASE_DIR" -type d -name "__pycache__" 2>/dev/null | wc -l)))

# Supprimer .pyc
echo "Suppression des fichiers .pyc..."
find "$BASE_DIR" -type f -name "*.pyc" -delete 2>/dev/null
count=$((count + $(find "$BASE_DIR" -type f -name "*.pyc" 2>/dev/null | wc -l)))

# Supprimer .pytest_cache
echo "Suppression des .pytest_cache..."
find "$BASE_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null

# Supprimer node_modules si présent
if [ -d "$BASE_DIR/node_modules" ]; then
    echo "Suppression de node_modules..."
    rm -rf "$BASE_DIR/node_modules"
    count=$((count + 1))
fi

# Supprimer fichiers nul
echo "Suppression des fichiers 'nul'..."
find "$BASE_DIR" -name "nul" -type f -delete 2>/dev/null

# Supprimer fichiers temporaires
echo "Suppression des fichiers temporaires..."
find "$BASE_DIR" -name "*.tmp" -type f -delete 2>/dev/null
find "$BASE_DIR" -name "*.bak" -type f -delete 2>/dev/null
find "$BASE_DIR" -name "*~" -type f -delete 2>/dev/null

# Supprimer anciens logs
if [ -d "$BASE_DIR/logs" ]; then
    echo "Suppression des anciens logs..."
    find "$BASE_DIR/logs" -name "*.log.*" -mtime +30 -delete 2>/dev/null
fi

# Supprimer sessions expirées
if [ -d "$BASE_DIR/sessions" ]; then
    echo "Suppression des sessions expirées..."
    find "$BASE_DIR/sessions" -type f -mtime +7 -delete 2>/dev/null
fi

# Supprimer uploads temporaires
if [ -d "$BASE_DIR/uploads" ]; then
    echo "Suppression des uploads temporaires..."
    find "$BASE_DIR/uploads" -type f -mtime +1 -delete 2>/dev/null
fi

# Supprimer fichiers de test
echo "Suppression des fichiers de test..."
find "$BASE_DIR" -name "test_*.json" -type f -delete 2>/dev/null
find "$BASE_DIR" -name "test_*.csv" -type f -delete 2>/dev/null

echo "✅ Nettoyage terminé!"
echo "📊 Environ $count éléments supprimés"

# Afficher l'espace disque libéré
if command -v du &> /dev/null; then
    echo "💾 Espace utilisé par le projet:"
    du -sh "$BASE_DIR"
fi
