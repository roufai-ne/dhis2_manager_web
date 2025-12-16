# 🔧 Initialisation Git - DHIS2 Manager

## Pour Windows

```powershell
# Aller dans le répertoire
cd dhis2_manager_web

# Exécuter le script
.\init-git.bat
```

## Pour Linux/Mac

```bash
# Aller dans le répertoire
cd dhis2_manager_web

# Rendre le script exécutable
chmod +x init-git.sh

# Exécuter
./init-git.sh
```

## Configuration Git (optionnel)

Si première fois avec Git:

```bash
git config --global user.name "Votre Nom"
git config --global user.email "votre.email@example.com"
```

## Créer Repository sur GitHub

1. Aller sur https://github.com/new
2. Créer un nouveau repository "dhis2-manager"
3. Ne pas initialiser avec README (déjà fait)
4. Copier l'URL du repository

## Lier et Pousser

```bash
# Ajouter le remote
git remote add origin https://github.com/votre-username/dhis2-manager.git

# Pousser le code
git push -u origin main

# Ou si erreur "main" n'existe pas:
git branch -M main
git push -u origin main
```

## Commandes Git Utiles

```bash
# Voir l'état
git status

# Voir l'historique
git log --oneline

# Ajouter des changements
git add .
git commit -m "Description des changements"
git push

# Créer une branche
git checkout -b feature/nouvelle-fonctionnalite

# Fusionner
git checkout main
git merge feature/nouvelle-fonctionnalite
```

## .gitignore

Le fichier `.gitignore` est configuré pour exclure:
- `venv/` - Environnement virtuel
- `.env` - Variables d'environnement sensibles
- `__pycache__/` - Cache Python
- `node_modules/` - Modules Node
- `logs/*` - Logs (sauf .gitkeep)
- `sessions/*` - Sessions (sauf .gitkeep)
- `uploads/*` - Uploads temporaires (sauf .gitkeep)

## Fichiers Inclus

✅ Code source complet
✅ Documentation
✅ Configuration Docker
✅ Scripts de déploiement
✅ .gitkeep pour répertoires vides
❌ .env (créer depuis .env.example)
❌ venv/ (à recréer)
❌ Données temporaires

## Vérification

Après initialisation, vous devriez voir:

```bash
$ git status
On branch main
nothing to commit, working tree clean

$ git log --oneline
abc1234 Initial commit - DHIS2 Manager v5.0
```

## Troubleshooting

### "fatal: not a git repository"
```bash
# Réexécuter init-git.bat ou init-git.sh
```

### "failed to push some refs"
```bash
# Forcer le push (première fois seulement)
git push -u origin main --force
```

### Erreur authentification GitHub
```bash
# Utiliser token personnel au lieu du mot de passe
# Créer un token: GitHub > Settings > Developer settings > Personal access tokens
```

---

**Prêt!** Votre code est maintenant versionné et prêt à être partagé! 🚀
