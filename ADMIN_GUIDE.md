# 🛡️ Interface Administration - DHIS2 Manager v5.0

## Accès Admin

### Configuration

Dans votre fichier `.env`, configurez les identifiants admin:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=votre_mot_de_passe_securise
```

**⚠️ IMPORTANT:** Changez le mot de passe par défaut en production!

### Connexion

1. Accédez à `/admin/login`
2. Entrez vos identifiants admin
3. Vous serez redirigé vers la page des logs

Une fois connecté, un onglet "Admin" apparaît dans la navigation.

---

## Fonctionnalités

### 📋 Page des Logs

**URL:** `/admin/logs`

Affiche les 500 dernières entrées de log avec:
- **Horodatage** - Date et heure de l'événement
- **Niveau** - INFO, WARNING, ERROR, DEBUG
- **Utilisateur** - Nom d'utilisateur DHIS2 ou admin
- **IP** - Adresse IP de l'utilisateur
- **Message** - Description de l'activité

#### Filtres disponibles:
- **Par niveau:** INFO, WARNING, ERROR, DEBUG
- **Par utilisateur:** Recherche par nom d'utilisateur
- **Par message:** Recherche dans le contenu des messages

#### Statistiques en temps réel:
- Nombre total de logs affichés
- Compteurs par niveau (INFO, WARNING, ERROR)

---

## Activités Loggées

Les activités suivantes sont automatiquement enregistrées avec le contexte utilisateur:

### Connexions DHIS2
```
[user:admin] [ip:192.168.1.100] Connexion DHIS2 réussie - URL: https://play.dhis2.org/dev
```

### Déconnexions
```
[user:admin] [ip:192.168.1.100] Déconnexion DHIS2 - URL: https://play.dhis2.org/dev
```

### Uploads de fichiers
```
[user:dhis2user] [ip:192.168.1.50] Upload fichier Excel: data_2024.xlsx
```

### Génération de JSON
```
[user:dhis2user] [ip:192.168.1.50] Génération JSON DHIS2 - 150 dataValues
```

### Erreurs
```
[user:anonymous] [ip:192.168.1.75] ERROR: Échec connexion DHIS2 - Invalid credentials
```

---

## Sécurité

### Accès Restreint

- Seuls les utilisateurs connectés avec les identifiants admin peuvent accéder aux logs
- Les sessions admin sont séparées des sessions utilisateurs normales
- Déconnexion automatique si non authentifié

### Bonnes Pratiques

1. **Mot de passe fort:**
   ```bash
   # Générer un mot de passe sécurisé
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Ne jamais commiter .env:**
   ```bash
   # Déjà dans .gitignore
   .env
   ```

3. **Logs en production:**
   - Les logs sont rotatifs (10 MB max par fichier)
   - 10 fichiers de backup conservés
   - Nettoyage automatique des anciens logs

4. **HTTPS en production:**
   - Obligatoire pour protéger les identifiants admin
   - Utilisez Let's Encrypt ou un certificat commercial

---

## API Logs (optionnel)

### Endpoint JSON

**URL:** `/admin/api/logs`

**Méthode:** GET

**Authentification:** Session admin requise

**Paramètres:**
- `limit` (int) - Nombre de logs (défaut: 100)
- `level` (string) - Filtrer par niveau (INFO, WARNING, ERROR, DEBUG)
- `user` (string) - Filtrer par utilisateur

**Exemple:**
```bash
curl -X GET "http://localhost:5000/admin/api/logs?limit=50&level=ERROR" \
  -H "Cookie: session=<votre-session>"
```

**Réponse:**
```json
{
  "logs": [
    {
      "timestamp": "2025-12-18 10:30:45",
      "level": "ERROR",
      "user": "admin",
      "ip": "192.168.1.100",
      "message": "Échec connexion DHIS2",
      "raw": "[2025-12-18 10:30:45] ERROR [user:admin] [ip:192.168.1.100] Échec connexion DHIS2"
    }
  ],
  "count": 1
}
```

---

## Déconnexion

Pour vous déconnecter de l'interface admin:
- Cliquez sur "Déconnexion" dans la page des logs
- Ou accédez à `/admin/logout`

---

## Dépannage

### Je ne vois pas l'onglet "Admin"
- Vérifiez que vous êtes connecté avec les identifiants admin
- Rafraîchissez la page

### Identifiants incorrects
- Vérifiez le fichier `.env`
- Vérifiez que `ADMIN_USERNAME` et `ADMIN_PASSWORD` sont correctement définis
- Redémarrez l'application après modification du .env

### Logs vides
- Vérifiez que le fichier `logs/app.log` existe
- Vérifiez les permissions du dossier `logs/`
- Déclenchez quelques activités (connexion DHIS2, upload fichier)

### Erreur "Not Found" sur /admin/logs
- Vérifiez que le blueprint admin est bien enregistré dans `app/__init__.py`
- Redémarrez l'application

---

## Maintenance

### Rotation des Logs

Les logs sont automatiquement rotatifs:
- Taille max: 10 MB par fichier
- Fichiers backup: 10
- Ancien format: `app.log.1`, `app.log.2`, etc.

### Nettoyage Manuel

```bash
# Supprimer les anciens logs (> 30 jours)
find logs/ -name "*.log.*" -mtime +30 -delete

# Ou utiliser le script de nettoyage
./cleanup.sh
```

---

## Support

Pour toute question ou problème:
- Consultez la documentation dans `DEPLOYMENT.md`
- Vérifiez les logs d'erreur
- Contactez l'administrateur système

---

**Version:** 5.0  
**Dernière mise à jour:** Décembre 2025
