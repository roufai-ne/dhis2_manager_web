# 🔄 Mode Mapping TCD Amélioré

**Date :** 15 décembre 2025  
**Amélioration :** Support des TCD avec cellules fusionnées + détection automatique

## 🎯 Problème Résolu

### Format TCD Typique (Excel avec cellules fusionnées)

```
┌──────────┬────────────┬──────┬──────────┬─────────────────────┐
│ NOM_ETAB │ GROUP_AGE  │ SEXE │  CYCLE   │ Nombre de NOMS_PREN │
├──────────┼────────────┼──────┼──────────┼─────────────────────┤
│ CFDA     │ [ 22 - 24[ │  F   │ 1er cycle│          5          │
│          │ [ 22 - 24[ │  M   │ 1er cycle│          4          │  ← Cellule NOM_ETAB fusionnée
│          │ [ 24 - 26[ │  F   │ 1er cycle│          3          │
├──────────┼────────────┼──────┼──────────┼─────────────────────┤
│ CPSP     │ [ 20 - 22[ │  F   │ 1er cycle│          6          │
│          │ [ 20 - 22[ │  M   │ 1er cycle│          3          │  ← Cellule NOM_ETAB fusionnée
│          │ [ 22 - 24[ │  F   │ 1er cycle│         11          │
└──────────┴────────────┴──────┴──────────┴─────────────────────┘
```

**Problèmes avant l'amélioration :**
- ❌ Cellules vides dues aux fusions → Lignes ignorées
- ❌ Nom de colonne variable → Mapping manuel fastidieux
- ❌ Colonnes catégories → COC non résolu

**Solutions implémentées :**
- ✅ **Fill Down automatique** des cellules fusionnées
- ✅ **Détection automatique** de la colonne de valeurs
- ✅ **Fuzzy Matching COC** pour les catégories

## 📋 Fonctionnalités Ajoutées

### 1. Fill Down Automatique (`_apply_fill_down`)

**Fonctionnement :**
```python
# Avant fill down
NOM_ETAB  | GROUP_AGE | SEXE
----------|-----------|-----
CFDA      | [22-24[   | F
(vide)    | [22-24[   | M    ← ❌ Organisation perdue
(vide)    | [24-26[   | F    ← ❌ Organisation perdue

# Après fill down
NOM_ETAB  | GROUP_AGE | SEXE
----------|-----------|-----
CFDA      | [22-24[   | F
CFDA      | [22-24[   | M    ← ✅ CFDA propagé
CFDA      | [24-26[   | F    ← ✅ CFDA propagé
```

**Colonnes concernées :**
- Colonne organisation (`org_column`)
- Colonnes catégories (depuis `category_mapping`)

**Méthode :** `pandas.DataFrame.ffill()` (forward fill)

### 2. Détection Automatique des Colonnes (`_detect_value_columns`)

**Algorithme :**
1. Identifier les colonnes structurelles (org, catégories, DE mappés)
2. Chercher les colonnes avec mots-clés : `nombre`, `effectif`, `total`, `count`, `somme`
3. Ou colonnes de type numérique
4. Retourner les colonnes candidates

**Exemple :**
```python
Colonnes du fichier: ['NOM_ETAB', 'GROUP_AGE', 'SEXE', 'Nombre de NOMS_PRENOMS']

Détection:
- 'NOM_ETAB'              → Structurelle (org)
- 'GROUP_AGE'             → Structurelle (catégorie)
- 'SEXE'                  → Structurelle (catégorie)
- 'Nombre de NOMS_PRENOMS'→ ✅ DÉTECTÉE (contient "Nombre")
```

### 3. Mapping Automatique DE

Si `data_element_mapping` est vide :
1. Détecte les colonnes de valeurs
2. Récupère le premier DE du dataset
3. Crée un mapping automatique : `{first_de_id: detected_column}`

**Exemple :**
```python
# Configuration minimale
{
  "org_column": "NOM_ETAB",
  "category_mapping": {
    "age_cat_id": "GROUP_AGE",
    "sex_cat_id": "SEXE"
  },
  "data_element_mapping": {}  # ← VIDE !
}

# Résultat
✓ Colonne détectée: "Nombre de NOMS_PRENOMS"
✓ Mapping créé automatiquement avec le 1er DE du dataset
```

## 🔧 Utilisation

### Configuration Minimale (Auto-détection)

```json
{
  "org_column": "NOM_ETAB",
  "category_mapping": {
    "age_category_id": "GROUP_AGE",
    "sex_category_id": "SEXE"
  },
  "data_element_mapping": {},
  "dataset_id": "dataset_xyz",
  "period": "2024"
}
```

### Configuration Complète (Mapping Explicite)

```json
{
  "org_column": "NOM_ETAB",
  "category_mapping": {
    "kBLMDgSaxVk": "GROUP_AGE",
    "rWLrZL8rDQU": "SEXE"
  },
  "data_element_mapping": {
    "dE_effectif_id": "Nombre de NOMS_PRENOMS"
  },
  "dataset_id": "dataset_xyz",
  "period": "2024",
  "processing_mode": "values"
}
```

## 📊 Workflow Complet

### Étape 1 : Chargement du Fichier
```python
df = pd.read_excel(filepath)
# Colonnes: ['NOM_ETAB', 'GROUP_AGE', 'SEXE', 'CYCLE', 'Nombre de NOMS_PRENOMS']
```

### Étape 2 : Fill Down Automatique
```python
df = _apply_fill_down(df, 'NOM_ETAB', category_mapping)
# Les cellules fusionnées sont remplies avec la dernière valeur non-vide
```

**Résultat :**
```
Avant:                          Après:
NOM_ETAB | GROUP_AGE           NOM_ETAB | GROUP_AGE
---------|----------           ---------|----------
CFDA     | [22-24[             CFDA     | [22-24[
         | [22-24[             CFDA     | [22-24[  ← Rempli
         | [24-26[             CFDA     | [24-26[  ← Rempli
CPSP     | [20-22[             CPSP     | [20-22[
         | [20-22[             CPSP     | [20-22[  ← Rempli
```

### Étape 3 : Détection Colonne de Valeurs (si mapping vide)
```python
detected_cols = _detect_value_columns(df, ...)
# Détecte: ['Nombre de NOMS_PRENOMS']
```

### Étape 4 : Traitement Ligne par Ligne
```python
Pour chaque ligne:
  1. Résoudre organisation: NOM_ETAB → org_id
  2. Résoudre catégories: GROUP_AGE + SEXE → COC (fuzzy matching)
  3. Récupérer valeur: 'Nombre de NOMS_PRENOMS' → value
  4. Créer dataValue
```

### Étape 5 : Génération dataValues
```json
{
  "dataElement": "dE_effectif_id",
  "period": "2024",
  "orgUnit": "org_CFDA_id",
  "categoryOptionCombo": "coc_22-24_F_id",  ← Résolu par fuzzy matching
  "attributeOptionCombo": "default",
  "value": "5"
}
```

## 🎓 Exemple Complet

### Fichier Excel Input
```
NOM_ETAB | GROUP_AGE  | SEXE | CYCLE     | Nombre de NOMS_PRENOMS
---------|------------|------|-----------|----------------------
CFDA     | [ 22 - 24[ | F    | 1er cycle | 5
         | [ 22 - 24[ | M    | 1er cycle | 4
         | [ 24 - 26[ | F    | 1er cycle | 3
CPSP     | [ 20 - 22[ | F    | 1er cycle | 6
         | [ 22 - 24[ | F    | 1er cycle | 11
         | [ 24 - 26[ | M    | 1er cycle | 5
ESEG     | [ 18 - 20[ | F    | 1er cycle | 1
         | [ 20 - 22[ | F    | 1er cycle | 34
```

### Configuration
```json
{
  "org_column": "NOM_ETAB",
  "category_mapping": {
    "age_cat": "GROUP_AGE",
    "sex_cat": "SEXE"
  },
  "data_element_mapping": {},  ← Auto-détection
  "dataset_id": "ds_etudiants",
  "period": "2024"
}
```

### Traitement
1. **Fill down** : CFDA propagé sur lignes 2-3, CPSP sur lignes 5-6, etc.
2. **Détection** : Colonne "Nombre de NOMS_PRENOMS" détectée
3. **Mapping** : Utilisera le 1er DE du dataset "ds_etudiants"
4. **COC** : Fuzzy matching sur AGE + SEXE

### Output (8 dataValues)
```json
[
  {"dataElement": "de_xxx", "orgUnit": "CFDA", "categoryOptionCombo": "22-24_f", "value": "5"},
  {"dataElement": "de_xxx", "orgUnit": "CFDA", "categoryOptionCombo": "22-24_m", "value": "4"},
  {"dataElement": "de_xxx", "orgUnit": "CFDA", "categoryOptionCombo": "24-26_f", "value": "3"},
  {"dataElement": "de_xxx", "orgUnit": "CPSP", "categoryOptionCombo": "20-22_f", "value": "6"},
  ...
]
```

## 🚨 Gestion des Erreurs

### Erreur 1 : Colonne Non Détectée
```
❌ Aucune colonne de valeur détectée
```
**Cause :** Aucune colonne ne correspond aux critères (mots-clés + types)  
**Solution :** Fournir explicitement `data_element_mapping`

### Erreur 2 : COC Non Trouvé
```
⚠️ COC non trouvé pour: '[22-24[, F'
```
**Cause :** Combinaison de catégories inconnue dans DHIS2  
**Solution :** Vérifier les métadonnées ou utiliser fuzzy matching

### Erreur 3 : Organisation Non Trouvée
```
⚠️ Organisation non trouvée: CFDA
```
**Cause :** Nom/code ne match pas avec les métadonnées  
**Solution :** Utiliser le code exact ou vérifier l'orthographe

## 📈 Statistiques Retournées

```json
{
  "total_rows": 8,
  "valid_rows": 8,
  "errors": {
    "org_not_found": 0,
    "de_not_found": 0,
    "coc_not_found": 0,
    "invalid_value": 0,
    "empty_value": 0
  },
  "error_rate": 0.0
}
```

## 🔄 Comparaison Avant/Après

| Aspect | Avant | Après |
|--------|-------|-------|
| **Cellules fusionnées** | ❌ Lignes ignorées | ✅ Fill down auto |
| **Nom colonne variable** | ❌ Mapping manuel obligatoire | ✅ Détection auto |
| **Configuration** | ⚠️ Complexe | ✅ Minimale |
| **COC ordre** | ❌ Match strict | ✅ Fuzzy matching |
| **Maintenance** | ⚠️ Élevée | ✅ Faible |

## 🎯 Cas d'Usage Idéal

Ce mode amélioré est parfait pour :
- ✅ **TCD Excel** exportés avec cellules fusionnées
- ✅ **Fichiers administratifs** avec structure répétitive
- ✅ **Imports récurrents** où le nom de colonne peut varier
- ✅ **Données par catégories** (Age, Sexe, etc.)

## 🚀 Évolutions Futures

### Prochaines Améliorations

1. **Multi-colonnes de valeurs**
   - Détecter plusieurs colonnes de valeurs
   - Mapper automatiquement à plusieurs DE

2. **Smart Column Matching**
   - Matching approximatif sur les noms de colonnes
   - Ex: "Group Age" → "GROUP_AGE"

3. **Validation pré-import**
   - Vérifier les combinaisons COC avant traitement
   - Alerter sur les données problématiques

4. **Templates de configuration**
   - Sauvegarder les configurations réussies
   - Réutiliser pour des imports similaires

---

**Conclusion :** Le mode mapping amélioré combine désormais le meilleur de l'automatisation (détection, fill down, fuzzy matching) tout en restant flexible pour les cas complexes via configuration explicite.
