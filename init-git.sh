#!/bin/bash

# Script d'initialisation Git pour DHIS2 Manager

echo "🔧 Initialisation du repository Git..."

# Vérifier si Git est installé
if ! command -v git &> /dev/null; then
    echo "❌ Git n'est pas installé. Installez-le d'abord."
    exit 1
fi

# Aller dans le répertoire dhis2_manager_web
cd "$(dirname "$0")"

# Vérifier si .git existe déjà
if [ -d ".git" ]; then
    echo "⚠️  Repository Git existe déjà!"
    read -p "Voulez-vous réinitialiser? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .git
        echo "✅ Repository supprimé"
    else
        echo "❌ Annulé"
        exit 0
    fi
fi

# Initialiser Git
git init
echo "✅ Repository Git initialisé"

# Configurer Git (optionnel - décommentez si nécessaire)
# git config user.name "Votre Nom"
# git config user.email "votre.email@example.com"

# Créer .gitignore s'il n'existe pas
if [ ! -f ".gitignore" ]; then
    echo "📝 Création de .gitignore..."
    cat > .gitignore << 'EOL'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environment
venv/
env/
ENV/
.venv

# Flask
instance/
.webassets-cache

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/*
!logs/.gitkeep

# Sessions and uploads
sessions/*
!sessions/.gitkeep
uploads/*
!uploads/.gitkeep

# Testing
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
package-lock.json

# Temporary files
nul
*.tmp
*.bak
*~

# Data files
test_*.json
test_*.csv
dataValueSets_*.csv
effectif_etudiant.json
EOL
    echo "✅ .gitignore créé"
fi

# Créer les .gitkeep si nécessaires
mkdir -p logs sessions uploads
touch logs/.gitkeep sessions/.gitkeep uploads/.gitkeep

# Ajouter tous les fichiers
echo "📦 Ajout des fichiers..."
git add .

# Premier commit
echo "💾 Premier commit..."
git commit -m "Initial commit - DHIS2 Manager v5.0

- Application web Flask pour gestion DHIS2
- Mode Template: Génération templates Excel
- Mode Automatique: Traitement TCD avec mapping intelligent
- Configuration Docker complète
- Documentation exhaustive
- Prêt pour déploiement production"

echo ""
echo "✅ Repository Git initialisé avec succès!"
echo ""
echo "📋 Prochaines étapes:"
echo "1. Créer un repository sur GitHub/GitLab"
echo "2. Ajouter le remote:"
echo "   git remote add origin <URL_REPOSITORY>"
echo "3. Pousser le code:"
echo "   git push -u origin main"
echo ""
echo "📊 Statistiques:"
git log --oneline
echo ""
git status
