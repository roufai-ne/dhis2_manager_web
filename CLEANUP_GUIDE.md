# ===========================
# FICHIERS À SUPPRIMER - DHIS2 Manager v5.0
# ===========================

## 📁 Racine du projet (dhis2_manager/)

### Fichiers Python obsolètes
- aggregate_data.py                    # Ancien script, remplacé par app web
- aggregate_students.py                # Ancien script, remplacé par app web
- analyze_dataset.py                   # Ancien script, remplacé par app web
- create_test_file.py                  # Fichier de test
- list_anthropic_models.py            # Script utilitaire dev
- list_models.py                      # Script utilitaire dev
- verify_features.py                  # Script de vérification dev

### Fichiers de données temporaires
- dataset.json                        # Données de test
- metadata.json                       # Métadonnées de test
- dhis2_manager.log                  # Ancien log
- nul                                # Fichier vide
- TEST_MultiOnglets_20251215_0937.xlsx # Fichier de test

### Documentation obsolète (v4.3)
- CHANGELOG_v4.3.md
- DEMARRAGE_RAPIDE_v4.3.md
- README_v4.3.md
- GUIDE_TABLEAUX_CROISES.md          # Ancien guide
- PLAN_MIGRATION_WEB.md              # Terminé
- POUR_VOIR_LES_MODIFICATIONS.txt    # Obsolète
- remaniemement.md                   # Ancien plan

### Répertoires temporaires
- __pycache__/                       # Cache Python
- logs/ (ancien)                     # Déplacé dans dhis2_manager_web/
- sessions/ (ancien)                 # Déplacé dans dhis2_manager_web/
- venv/ (racine)                     # Environnement virtuel à recréer
- .claude/                           # Fichiers temporaires Claude

---

## 📁 Application web (dhis2_manager_web/)

### Documentation de développement (à archiver)
- AMELIORATIONS_MAPPING_IA.md
- BACKEND_MODIFICATIONS_COMPLETE.md
- CORRECTIFS.md
- DESIGN_OVERHAUL.md
- FRONTEND_MODIFICATIONS_COMPLETE.md
- FUZZY_MATCHING_COC.md
- GUIDE_TEST_COMPLET.md
- MODE_MAPPING_TCD_AMELIORE.md
- MODE_TCD_MULTI_DE.md
- PHASE2_COMPLETE.md
- PLAN_MULTI_ONGLETS_WEB.md
- README_MULTI_ONGLETS.md
- RECOMMENDATIONS.md
- SECURITY_IMPROVEMENTS.md
- SUIVI_DEVELOPPEMENT.md
- TEST_BACKEND_CURL.md
- TESTING_GUIDE.md
- TROUBLESHOOTING.md

### Fichiers de test
- create_test_file.py
- test_metadata.json
- dataValueSets_2022-01-01_2022-12-31.csv
- effectif_etudiant.json
- verify_features.py
- verify_install.py
- verify_simple.py

### Fichiers temporaires
- nul

### Répertoires à nettoyer
- __pycache__/                       # Cache Python
- .pytest_cache/                     # Cache pytest
- node_modules/                      # Modules Node.js (si Tailwind non utilisé)
- venv/                             # Environnement virtuel (à recréer)
- sessions/* (garder .gitkeep)      # Sessions expirées
- logs/* (garder .gitkeep)          # Anciens logs

---

## 🗑️ Commandes de nettoyage

### Windows (PowerShell)
```powershell
# Aller dans dhis2_manager_web/
cd dhis2_manager_web

# Exécuter le script de nettoyage
.\cleanup.bat

# OU nettoyer manuellement
Remove-Item -Recurse -Force __pycache__, .pytest_cache, node_modules, venv
```

### Linux/Mac (Bash)
```bash
# Aller dans dhis2_manager_web/
cd dhis2_manager_web

# Rendre le script exécutable
chmod +x cleanup.sh

# Exécuter le script
./cleanup.sh

# OU nettoyer manuellement
rm -rf __pycache__ .pytest_cache node_modules venv
find . -name "*.pyc" -delete
find . -name "nul" -delete
```

---

## 📦 Fichiers à GARDER

### Configuration
- .env.example
- .gitignore
- .dockerignore
- Dockerfile
- docker-compose.yml
- requirements.txt
- package.json (si Tailwind utilisé)
- tailwind.config.js (si Tailwind utilisé)

### Application
- run.py
- app/ (tout le répertoire)
- nginx/nginx.conf

### Documentation importante
- README.md (nouveau)
- DEPLOYMENT.md (nouveau)
- CHANGELOG.md
- INTEGRATION_XLS.MD (spécifications techniques)

### Structure
- sessions/.gitkeep
- logs/.gitkeep
- uploads/.gitkeep

---

## ✅ Checklist de nettoyage

- [ ] Sauvegarder les données importantes
- [ ] Exécuter cleanup.sh ou cleanup.bat
- [ ] Supprimer les fichiers de documentation obsolètes
- [ ] Supprimer les anciens scripts Python (racine)
- [ ] Supprimer les fichiers de test
- [ ] Nettoyer sessions/ et logs/ expirés
- [ ] Supprimer node_modules/ si non utilisé
- [ ] Supprimer venv/ (sera recréé)
- [ ] Vérifier que .gitignore est à jour
- [ ] Tester le build Docker

---

## 🎯 Après nettoyage

### Vérification
```bash
# Taille du projet
du -sh .

# Nombre de fichiers
find . -type f | wc -l

# Build Docker
docker-compose build

# Test
docker-compose up
curl http://localhost:5000/health
```

### Résultat attendu
- Taille projet: ~50-100 MB (sans venv/node_modules)
- Fichiers: ~150-200 fichiers
- Build Docker: Succès ✅
- Health check: {"status":"healthy"} ✅

---

**Note**: Archiver la documentation de développement au lieu de la supprimer si vous souhaitez garder l'historique du projet.
