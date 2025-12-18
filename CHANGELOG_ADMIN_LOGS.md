# Changelog - Système de Logs Admin

## Version 1.1 - 18 Décembre 2025

### 🔧 Corrections

#### Capture du nom d'utilisateur DHIS2
**Problème**: Tous les logs affichaient "anonymous" au lieu du nom d'utilisateur DHIS2 connecté.

**Solution**: 
1. **Déconnexion DHIS2** (`configuration.py`):
   - Déplacé `log_activity()` AVANT la suppression de `session['dhis2_username']`
   - Maintenant le username est capturé correctement lors de la déconnexion

2. **Logs d'activité ajoutés**:
   - ✅ Connexion DHIS2 (avec URL et statistiques)
   - ✅ Déconnexion DHIS2 (avec URL)
   - ✅ Upload fichier Excel (avec nom de fichier)
   - ✅ Génération template Excel (avec dataset, période, nb organisations, nb lignes)
   - ✅ Génération CSV noms (avec dataset, période, nb organisations, nb lignes)
   - ✅ Traitement template Excel (avec onglet, nb valeurs)
   - ✅ Mapping personnalisé (avec dataset, période, nb valeurs, mode)

### 📊 Exemple de Logs

```
[2025-12-18 14:30:15] INFO [user:john.doe] [ip:192.168.1.100] Connexion DHIS2 réussie - URL: https://dhis2.example.com - Stats: {'dataSets': 25, 'dataElements': 450}
[2025-12-18 14:32:45] INFO [user:john.doe] [ip:192.168.1.100] Upload fichier Excel - Nom: donnees_sante_2024.xlsx
[2025-12-18 14:33:20] INFO [user:john.doe] [ip:192.168.1.100] Génération template Excel - Dataset: Rapport_Mensuel, Période: 202412, Organisations: 15, Lignes: 450
[2025-12-18 14:35:10] INFO [user:john.doe] [ip:192.168.1.100] Mapping personnalisé - Dataset: Rapport_Mensuel, Période: 202412, Valeurs: 1200, Mode: values
[2025-12-18 15:00:00] INFO [user:john.doe] [ip:192.168.1.100] Déconnexion DHIS2 - URL: https://dhis2.example.com
```

### 🔍 Traçabilité

Chaque action importante effectuée par un utilisateur DHIS2 connecté est maintenant tracée avec:
- **Utilisateur**: Nom d'utilisateur DHIS2 (ou 'admin' pour l'interface admin)
- **IP**: Adresse IP de l'utilisateur
- **Action**: Description détaillée avec paramètres
- **Timestamp**: Date et heure précises

### 🎯 Actions Tracées

| Action | Information Capturée |
|--------|---------------------|
| Connexion DHIS2 | URL, statistiques métadonnées |
| Déconnexion DHIS2 | URL |
| Upload Excel | Nom du fichier |
| Génération Template | Dataset, période, nb organisations, nb lignes |
| Génération CSV | Dataset, période, nb organisations, nb lignes |
| Traitement Template | Onglet, nb valeurs générées |
| Mapping Personnalisé | Dataset, période, nb valeurs, mode traitement |

### 📈 Pagination des Logs

- Affichage par **50 logs par page**
- Navigation intuitive avec boutons précédent/suivant
- Numéros de pages avec ellipses (...)
- Information "Page X sur Y (Z logs)"
- Pagination respecte les filtres actifs

### 🗑️ Effacement des Logs

- Bouton "Effacer Logs" dans l'interface admin
- Confirmation avant suppression
- Préserve les logs système (démarrage application)
- Action elle-même tracée dans les logs

### 🔐 Sécurité

- Seuls les administrateurs peuvent voir les logs
- Username DHIS2 stocké dans session sécurisée
- Logs ne contiennent pas de mots de passe ou données sensibles

## Fichiers Modifiés

### `app/routes/configuration.py`
```python
# Ligne 306-309: Log AVANT suppression session
logger.info("Déconnexion DHIS2")
log_activity(f"Déconnexion DHIS2 - URL: {url}", 'info')
# Puis suppression session...
```

### `app/routes/generator.py`
```python
# Import
from app.utils.activity_logger import log_activity

# Ligne 217: Log génération template
log_activity(f"Génération template Excel - Dataset: {dataset_name}...", 'info')

# Ligne 298: Log génération CSV
log_activity(f"Génération CSV noms - Dataset: {dataset_name}...", 'info')
```

### `app/routes/calculator.py`
```python
# Import
from app.utils.activity_logger import log_activity

# Ligne 109: Log upload Excel
log_activity(f"Upload fichier Excel - Nom: {filename}", 'info')

# Ligne 246: Log traitement template
log_activity(f"Traitement Template Excel - Onglet: {sheet_name}...", 'info')

# Ligne 364: Log mapping personnalisé
log_activity(f"Mapping personnalisé - Dataset: {dataset_id}...", 'info')
```

### `app/templates/admin_logs.html`
```javascript
// Pagination côté client (50 logs/page)
const logsPerPage = 50;
let currentPage = 1;

// Fonction paginateLogs() pour afficher la page courante
// Fonction renderPagination() pour les contrôles de navigation
```

## Tests

### Scénario de Test
1. ✅ Connexion DHIS2 → Log avec username DHIS2
2. ✅ Upload Excel → Log avec username DHIS2
3. ✅ Génération template → Log avec username DHIS2
4. ✅ Mapping → Log avec username DHIS2
5. ✅ Déconnexion DHIS2 → Log avec username DHIS2
6. ✅ Pagination des logs (>50 entrées)
7. ✅ Effacement des logs

### Vérification dans l'interface Admin
- Accéder à `/admin/login`
- Identifiant: `admin`
- Mot de passe: `changeme123`
- Consulter `/admin/logs`
- Vérifier que les usernames DHIS2 apparaissent correctement

## Notes Techniques

### Flux de Session
```
1. User se connecte à DHIS2
   ↓
2. session['dhis2_username'] = username
   ↓
3. log_activity() lit session['dhis2_username']
   ↓
4. Logs affichent [user:username]
```

### Ordre Critique
```python
# ❌ MAUVAIS: Username déjà supprimé
session.pop('dhis2_username', None)
log_activity("Déconnexion")  # Affichera [user:anonymous]

# ✅ BON: Username encore présent
log_activity("Déconnexion")  # Affichera [user:john.doe]
session.pop('dhis2_username', None)
```
