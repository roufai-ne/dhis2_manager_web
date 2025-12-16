# Test Backend - Commandes cURL

Guide pour tester le backend sans modifier le frontend.

---

## Prérequis

1. **Serveur lancé** :
   ```bash
   cd dhis2_manager_web
   python run.py
   ```

2. **Métadonnées chargées** :
   - Via l'interface web : Configuration → Charger metadata.json

3. **Fichier Excel de test** :
   - Créer un fichier avec plusieurs onglets
   - OU utiliser le fichier généré par l'application desktop

---

## Tests avec cURL

### 1. Upload d'un fichier Excel

```bash
curl -X POST http://localhost:5000/calculator/api/upload-excel \
  -F "file=@TEST_MultiOnglets_20251215.xlsx" \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

**Réponse attendue** :
```json
{
  "success": true,
  "message": "Fichier chargé avec succès",
  "filename": "TEST_MultiOnglets_20251215.xlsx"
}
```

---

### 2. Récupérer la liste des onglets

```bash
curl -X GET http://localhost:5000/calculator/api/get-sheets \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

**Réponse attendue** :
```json
{
  "success": true,
  "sheets": [
    "Premier Cycle",
    "Deuxième Cycle",
    "Données Normales",
    "Troisième Cycle"
  ],
  "count": 4
}
```

---

### 3. Traiter en mode normal (ancien comportement)

```bash
curl -X POST http://localhost:5000/calculator/api/process-template \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json"
```

**Comportement** : Traite l'onglet "Données" en mode normal (rétrocompatible).

---

### 4. Traiter un onglet spécifique en mode normal

```bash
curl -X POST http://localhost:5000/calculator/api/process-template \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json" \
  -d '{
    "sheet_name": "Premier Cycle",
    "mode": "normal"
  }'
```

---

### 5. Traiter en mode tableau croisé

```bash
curl -X POST http://localhost:5000/calculator/api/process-template \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json" \
  -d '{
    "sheet_name": "Premier Cycle",
    "mode": "pivot",
    "data_element_id": "h3F7ZGKD3kl"
  }'
```

**Note** : Remplacez `h3F7ZGKD3kl` par un ID de data element valide de vos métadonnées.

**Réponse attendue** :
```json
{
  "success": true,
  "stats": {
    "total_rows": 4,
    "total_columns": 4,
    "valid_rows": 12,
    "errors": {
      "org_not_found": 0,
      "invalid_value": 2
    },
    "error_rate": 12.5
  },
  "preview": [
    {
      "dataElement": "h3F7ZGKD3kl",
      "period": "2024",
      "orgUnit": "abc123",
      "categoryOptionCombo": "def456",
      "attributeOptionCombo": "def456",
      "value": "150"
    }
  ],
  "total_values": 12,
  "json_filename": "DHIS2_Import_20251215_143052.json"
}
```

---

### 6. Test validation erreur (mode pivot sans DE)

```bash
curl -X POST http://localhost:5000/calculator/api/process-template \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json" \
  -d '{
    "sheet_name": "Premier Cycle",
    "mode": "pivot"
  }'
```

**Réponse attendue** :
```json
{
  "error": "data_element_id requis en mode tableau croisé"
}
```

**Status** : 400

---

## Obtenir le cookie de session

### Méthode 1 : Via le navigateur

1. Ouvrez l'application web dans votre navigateur
2. Ouvrez les DevTools (F12)
3. Onglet "Application" → "Cookies"
4. Copiez la valeur du cookie `session`

### Méthode 2 : Via curl avec authentification

```bash
# Connectez-vous d'abord
curl -c cookies.txt http://localhost:5000/

# Puis utilisez le fichier de cookies
curl -b cookies.txt -X GET http://localhost:5000/calculator/api/get-sheets
```

---

## Tests Python (alternative à cURL)

Créez un fichier `test_backend.py` :

```python
import requests

# Base URL
BASE_URL = "http://localhost:5000/calculator/api"

# Session (remplacez par votre cookie)
session = requests.Session()
# OU : session.cookies.set('session', 'YOUR_SESSION_VALUE')

def test_upload():
    with open('TEST_MultiOnglets.xlsx', 'rb') as f:
        response = session.post(
            f"{BASE_URL}/upload-excel",
            files={'file': f}
        )
    print("Upload:", response.json())

def test_get_sheets():
    response = session.get(f"{BASE_URL}/get-sheets")
    print("Sheets:", response.json())

def test_process_normal(sheet_name="Données"):
    response = session.post(
        f"{BASE_URL}/process-template",
        json={
            "sheet_name": sheet_name,
            "mode": "normal"
        }
    )
    print(f"Process {sheet_name}:", response.json())

def test_process_pivot(sheet_name, de_id):
    response = session.post(
        f"{BASE_URL}/process-template",
        json={
            "sheet_name": sheet_name,
            "mode": "pivot",
            "data_element_id": de_id
        }
    )
    print(f"Process pivot {sheet_name}:", response.json())

if __name__ == '__main__':
    # test_upload()
    test_get_sheets()
    # test_process_normal("Premier Cycle")
    # test_process_pivot("Premier Cycle", "h3F7ZGKD3kl")
```

**Exécution** :
```bash
python test_backend.py
```

---

## Vérifier les logs

Les logs sont écrits dans `dhis2_manager_web/logs/app.log` :

```bash
tail -f logs/app.log
```

**Logs attendus** :
```
INFO - Onglets détectés: ['Premier Cycle', 'Deuxième Cycle']
INFO - Traitement du template (onglet: Premier Cycle, mode: pivot)
INFO - Traitement tableau croisé: Premier Cycle avec DE=h3F7ZGKD3kl
WARNING - Organisation inconnue: Faculté XYZ
INFO - Traitement tableau croisé terminé: 150 valeurs valides
```

---

## Créer un fichier de test Excel simple

Si vous n'avez pas de fichier, créez-en un avec Python :

```python
import pandas as pd

# Onglet 1 : Tableau croisé
data1 = {
    'Indicateur': ['Inscrits', 'Diplômés', 'Abandons'],
    'Faculté A': [150, 45, 10],
    'Faculté B': [200, 60, 12],
    'Faculté C': [180, 55, 8]
}
df1 = pd.DataFrame(data1)

# Sauvegarder
with pd.ExcelWriter('TEST_Backend.xlsx') as writer:
    df1.to_excel(writer, sheet_name='Premier Cycle', index=False)

print("Fichier TEST_Backend.xlsx créé")
```

**Exécution** :
```bash
python create_test_file.py
```

---

## Dépannage

### Erreur : "Métadonnées non chargées"

**Cause** : Vous n'avez pas chargé les métadonnées dans la session.

**Solution** :
1. Ouvrez http://localhost:5000/configuration
2. Chargez le fichier `metadata.json`
3. Réessayez

---

### Erreur : "Aucun fichier uploadé"

**Cause** : Le fichier n'est pas en session.

**Solution** :
1. Uploadez d'abord le fichier avec `/api/upload-excel`
2. Utilisez le même cookie de session

---

### Erreur : "data_element_id requis"

**Cause** : Mode pivot sans `data_element_id`.

**Solution** :
```json
{
  "mode": "pivot",
  "data_element_id": "abc123"  // Ajoutez ceci
}
```

---

### Erreur : "Organisation inconnue"

**Cause** : Les noms de colonnes ne correspondent pas aux métadonnées.

**Solution** :
1. Vérifiez les noms exacts dans `metadata.json`
2. Renommez les colonnes Excel pour correspondre

---

## Checklist Test Backend

- [ ] Serveur lancé sur http://localhost:5000
- [ ] Métadonnées chargées via l'interface
- [ ] Fichier Excel de test créé
- [ ] Cookie de session récupéré
- [ ] Test upload fichier → ✅
- [ ] Test get-sheets → ✅
- [ ] Test process mode normal → ✅
- [ ] Test process mode pivot → ✅
- [ ] Test validation erreurs → ✅
- [ ] Logs vérifiés → ✅

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
