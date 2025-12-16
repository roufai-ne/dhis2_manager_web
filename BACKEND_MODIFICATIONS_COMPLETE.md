# Backend - Modifications Terminées

## ✅ Ce qui a été fait

### 1. Service DataCalculator (`app/services/data_calculator.py`)

#### Nouvelle méthode : `get_excel_sheets()`
**Lignes 32-49**

```python
def get_excel_sheets(self, filepath: str) -> List[str]:
    """
    Récupère la liste des onglets d'un fichier Excel
    """
```

**Fonctionnalité** : Lit un fichier Excel et retourne la liste de tous ses onglets.

---

#### Méthode modifiée : `process_template_excel()`
**Lignes 51-78**

**Avant** :
```python
def process_template_excel(self, filepath: str) -> Tuple[List[Dict], Dict]:
    df = pd.read_excel(filepath, sheet_name="Données", skiprows=5)
```

**Après** :
```python
def process_template_excel(
    self,
    filepath: str,
    sheet_name: str = "Données",
    mode: str = "normal",
    data_element_id: Optional[str] = None
) -> Tuple[List[Dict], Dict]:
```

**Nouvelles capacités** :
- Accepte un nom d'onglet (`sheet_name`)
- Supporte 2 modes : `"normal"` ou `"pivot"`
- Route automatiquement vers la bonne méthode de traitement

---

#### Nouvelle méthode : `_process_normal_template()`
**Lignes 80-165**

- Extrait du code original de `process_template_excel()`
- Traite les templates normaux (générés par le générateur)
- Accepte maintenant le nom d'onglet en paramètre

---

#### Nouvelle méthode : `_process_pivot_table()`
**Lignes 167-258**

```python
def _process_pivot_table(
    self,
    filepath: str,
    sheet_name: str,
    data_element_id: str
) -> Tuple[List[Dict], Dict]:
```

**Fonctionnalité** :
- Lit un tableau croisé (structures en colonnes)
- Première colonne = indicateurs (ignorée)
- Autres colonnes = noms des structures
- Extrait les valeurs aux intersections
- Résout les organisations par code puis par nom
- Valide les valeurs numériques
- Retourne les dataValues au format DHIS2

**Gestion des erreurs** :
- Organisations non trouvées : comptées et loggées
- Valeurs invalides : ignorées
- Statistiques détaillées retournées

---

### 2. Routes API (`app/routes/calculator.py`)

#### Nouvelle route : `/api/get-sheets`
**Lignes 123-154**

**Méthode** : `GET`

**Réponse** :
```json
{
  "success": true,
  "sheets": ["Premier Cycle", "Deuxième Cycle", "Données"],
  "count": 3
}
```

**Usage** : Appelée après upload d'un fichier pour lister les onglets disponibles.

---

#### Route modifiée : `/api/process-template`
**Lignes 157-206**

**Méthode** : `POST`

**Avant** :
- Aucun paramètre
- Traitait toujours l'onglet "Données"
- Mode normal uniquement

**Après** :
- Accepte un body JSON avec paramètres

**Body JSON** :
```json
{
  "sheet_name": "Premier Cycle",  // Optionnel, défaut: "Données"
  "mode": "pivot",                // Optionnel, défaut: "normal"
  "data_element_id": "abc123"     // Requis si mode="pivot"
}
```

**Validation** :
- Si `mode="pivot"` et `data_element_id` manquant → Erreur 400

**Réponse** : Inchangée (compatible avec l'ancien frontend)

---

## 🔄 Rétrocompatibilité

### ✅ Ancien comportement préservé

**Si aucun paramètre fourni** :
```javascript
// Appel sans body JSON
POST /api/process-template
// Comportement: sheet_name="Données", mode="normal"
// ✅ Fonctionne exactement comme avant
```

**Fichiers existants** :
- Les templates générés par le générateur fonctionnent toujours
- Aucune migration nécessaire

---

## 📝 Modifications résumées

| Fichier | Lignes modifiées | Ajouts | Suppressions |
|---------|------------------|--------|--------------|
| `data_calculator.py` | 32-258 | +127 | 0 |
| `calculator.py` | 123-206 | +84 | 0 |
| **Total** | | **+211 lignes** | **0 ligne** |

---

## 🧪 Tests à effectuer

### Test 1 : get_excel_sheets
```bash
# Upload un fichier Excel
POST /calculator/api/upload-excel

# Récupérer les onglets
GET /calculator/api/get-sheets

# Résultat attendu:
{
  "success": true,
  "sheets": ["Sheet1", "Sheet2", ...],
  "count": N
}
```

### Test 2 : Mode normal (rétrocompatibilité)
```bash
POST /calculator/api/process-template
# (sans body JSON)

# Résultat: Traite l'onglet "Données" en mode normal
# ✅ Compatible avec ancien frontend
```

### Test 3 : Mode normal avec onglet spécifique
```bash
POST /calculator/api/process-template
Content-Type: application/json

{
  "sheet_name": "Premier Cycle",
  "mode": "normal"
}

# Résultat: Traite l'onglet "Premier Cycle" en mode normal
```

### Test 4 : Mode tableau croisé
```bash
POST /calculator/api/process-template
Content-Type: application/json

{
  "sheet_name": "Inscriptions",
  "mode": "pivot",
  "data_element_id": "h3F7ZGKD3kl"
}

# Résultat: Traite le tableau croisé de l'onglet "Inscriptions"
```

### Test 5 : Validation erreurs
```bash
POST /calculator/api/process-template
Content-Type: application/json

{
  "mode": "pivot"
  // data_element_id manquant
}

# Résultat attendu:
{
  "error": "data_element_id requis en mode tableau croisé"
}
# Status: 400
```

---

## 📊 Logs

Les logs ont été améliorés pour suivre le traitement :

```
INFO - Onglets détectés dans /path/file.xlsx: ['Sheet1', 'Sheet2']
INFO - Traitement du template: /path/file.xlsx (onglet: Sheet1, mode: normal)
INFO - Traitement tableau croisé: Sheet1 avec DE=h3F7ZGKD3kl
WARNING - Organisation inconnue: Faculté XYZ
INFO - Traitement tableau croisé terminé: 150 valeurs valides
```

---

## 🚀 Prochaines étapes

### Frontend à faire

1. **Ajouter interface sélection onglets**
   - Afficher dropdown si multiple sheets
   - Charger sheets via `/api/get-sheets`

2. **Ajouter sélecteur de mode**
   - Radio buttons: "Normal" / "Tableau croisé"
   - Afficher sélecteur DE si mode pivot

3. **Modifier JavaScript**
   - Construire body JSON avec sheet_name, mode, data_element_id
   - Envoyer à `/api/process-template`

Voir [PLAN_MULTI_ONGLETS_WEB.md](PLAN_MULTI_ONGLETS_WEB.md) pour les détails.

---

## ✅ Checklist Backend

- [x] Méthode `get_excel_sheets()`
- [x] Méthode `_process_pivot_table()`
- [x] Modifier `process_template_excel()`
- [x] Route `/api/get-sheets`
- [x] Modifier route `/api/process-template`
- [x] Rétrocompatibilité préservée
- [x] Logs améliorés
- [x] Gestion d'erreurs
- [ ] Tests unitaires (à faire)
- [ ] Frontend (à faire)

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
**Version** : 2.0 (Backend)
**Statut** : ✅ Backend terminé, Frontend à faire
