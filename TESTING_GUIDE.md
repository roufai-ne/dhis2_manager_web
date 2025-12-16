# 🧪 Guide de Test - Phase 2 : Module de Configuration

## Prérequis
- ✅ Application lancée sur http://127.0.0.1:5000
- ✅ Navigateur moderne (Chrome, Firefox, Edge)

---

## Test 1 : Upload de fichier valide ✅

### Étapes
1. Accédez à http://127.0.0.1:5000/configuration
2. Glissez-déposez `test_metadata.json` dans la zone Dropzone
   - **OU** cliquez sur la zone et sélectionnez le fichier
3. Observez le loading spinner
4. Attendez la notification de succès verte
5. La page se recharge automatiquement

### Résultats attendus
- ✅ Notification verte : "Fichier chargé avec succès"
- ✅ Affichage d'un cadre violet avec les statistiques :
  - **Organisations** : 3
  - **Datasets** : 2
  - **Éléments** : 3
  - **Options** : 6
- ✅ Bouton "Effacer" visible en rouge
- ✅ L'alerte jaune "Aucune métadonnée chargée" disparaît

---

## Test 2 : Validation des erreurs ❌

### Test 2.1 : Fichier non-JSON
1. Créez un fichier texte `test.txt` avec du contenu
2. Essayez de l'uploader
3. **Attendu** : Message d'erreur "Type de fichier invalide"

### Test 2.2 : JSON invalide (syntaxe)
Créez `invalid_syntax.json` :
```json
{
  "organisationUnits": [
    {
      "id": "OU001",
      "name": "Test"  <-- Virgule manquante
    }
  }
}
```
1. Uploadez le fichier
2. **Attendu** : Erreur "Erreur JSON à la ligne X"

### Test 2.3 : JSON valide mais structure DHIS2 invalide
Créez `invalid_structure.json` :
```json
{
  "organisationUnits": [],
  "wrongField": []
}
```
1. Uploadez le fichier
2. **Attendu** : Erreurs de validation listées :
   - "Champs manquants : dataSets, dataElements"
   - "Aucune organisation trouvée"

---

## Test 3 : Gestion de session 🔄

### Étapes
1. Uploadez `test_metadata.json` (métadonnées chargées)
2. Ouvrez un nouvel onglet avec http://127.0.0.1:5000
3. Naviguez vers "Configuration"
4. **Attendu** : Les statistiques sont toujours affichées (persistance session)

### Test 3.2 : Navigation
1. Avec métadonnées chargées, cliquez sur "Accueil"
2. Cliquez sur "Configuration"
3. **Attendu** : Les statistiques sont toujours là

---

## Test 4 : Effacement des métadonnées 🗑️

### Étapes
1. Avec métadonnées chargées, cliquez sur le bouton "Effacer"
2. Confirmez l'alerte JavaScript
3. **Attendu** :
   - Notification "Métadonnées effacées avec succès"
   - Retour à l'état vide (alerte jaune réapparaît)
   - Statistiques disparues
   - Fichiers temporaires nettoyés

---

## Test 5 : Upload multiple 🔄

### Étapes
1. Uploadez `test_metadata.json` (succès)
2. Uploadez immédiatement un autre fichier sans rafraîchir
3. **Attendu** : 
   - Dropzone n'accepte qu'un seul fichier à la fois
   - Message "Vous ne pouvez uploader qu'un seul fichier"

---

## Test 6 : Taille de fichier 📦

### Étapes
1. Créez un fichier JSON > 50 MB (ou modifiez la limite dans le code pour tester)
2. Uploadez le fichier
3. **Attendu** : Erreur "Fichier trop volumineux"

---

## Test 7 : API endpoints 🔌

### Test avec curl/Postman

#### Status endpoint
```bash
curl http://127.0.0.1:5000/configuration/api/metadata/status
```
**Attendu (sans métadonnées)** :
```json
{
  "loaded": false
}
```

**Attendu (avec métadonnées)** :
```json
{
  "loaded": true,
  "filename": "test_metadata.json",
  "stats": {
    "org_units": 3,
    "data_sets": 2,
    ...
  }
}
```

#### Upload endpoint
```bash
curl -X POST -F "file=@test_metadata.json" http://127.0.0.1:5000/configuration/api/upload
```

---

## Test 8 : Interface utilisateur 🎨

### Vérifications visuelles
- ✅ Zone Dropzone change de couleur au survol
- ✅ Animation lors du drag-and-drop
- ✅ Loading spinner apparaît pendant le traitement
- ✅ Notifications apparaissent en haut à droite
- ✅ Notifications disparaissent après 5 secondes
- ✅ Design responsive (mobile, tablette, desktop)
- ✅ Icônes Font Awesome affichées correctement
- ✅ Gradient violet sur la carte des statistiques

---

## Test 9 : Console développeur 🔍

### Vérifier dans la console
1. Ouvrez F12 (DevTools)
2. Onglet Console
3. Uploadez un fichier
4. **Attendu** : 
   - Aucune erreur JavaScript
   - Messages de log pour les événements Dropzone
   - Requête POST vers `/configuration/api/upload`
   - Réponse 200 avec JSON de succès

### Onglet Network
1. Uploadez un fichier
2. **Attendu** :
   - Request Method : POST
   - Status : 200
   - Response : JSON avec `success: true`

---

## Checklist globale ✔️

- [ ] Upload fichier valide fonctionne
- [ ] Statistiques affichées correctement
- [ ] Validation des erreurs fonctionne
- [ ] Persistance en session fonctionne
- [ ] Navigation préserve les métadonnées
- [ ] Effacement fonctionne correctement
- [ ] Notifications animées
- [ ] Loading states visibles
- [ ] Design responsive
- [ ] Aucune erreur console
- [ ] API endpoints répondent correctement

---

## 🐛 Problèmes connus / À surveiller

1. **Session expiration** : Les métadonnées expirent après 2 heures (défaut Flask-Session)
2. **Fichiers temporaires** : Nettoyés au démarrage/arrêt de l'app
3. **Navigateurs anciens** : Dropzone.js nécessite un navigateur moderne

---

## 📝 Notes pour les développeurs

### Structure de session
```python
session['metadata'] = {
    'organisation_units': [...],
    'data_sets': [...],
    'data_elements': [...],
    ...
}
session['metadata_file'] = 'test_metadata.json'
```

### Endpoints disponibles
- `GET /configuration` : Page principale
- `POST /configuration/api/upload` : Upload de fichier
- `GET /configuration/api/metadata/status` : Statut
- `POST /configuration/clear` : Effacement

---

## ✅ Validation finale

Si tous les tests passent :
- ✅ Phase 2 validée
- ✅ Prêt pour Phase 3 (Générateur)
- ✅ Métadonnées disponibles pour les autres modules

**Bon test ! 🚀**
