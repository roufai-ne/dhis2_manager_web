# 📊 Mode TCD Multi-Data Elements

**Date :** 15 décembre 2025  
**Amélioration :** Support des tableaux croisés dynamiques avec plusieurs data elements

## 🎯 Problème Résolu

### Avant
❌ Le mode TCD ne supportait qu'UN SEUL data element pour toutes les lignes  
❌ Nécessitait de créer un fichier séparé par indicateur  
❌ Interface limitée avec sélection d'un seul DE

### Après
✅ Support automatique de PLUSIEURS data elements  
✅ Détection automatique depuis la première colonne  
✅ Un seul fichier pour tous les indicateurs d'un TCD

## 📋 Format de Fichier Supporté

### Structure Attendue

```
┌─────────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Indicateur          │ Struct A │ Struct B │ Struct C │ Struct D │
├─────────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Nombre de Licence   │    150   │    200   │    180   │    165   │
│ Nombre de Master    │     80   │     95   │     88   │     92   │
│ Nombre de Doctorat  │     12   │     18   │     15   │     10   │
│ Taux de réussite    │   85.5   │   90.2   │   87.8   │   89.1   │
└─────────────────────┴──────────┴──────────┴──────────┴──────────┘
```

### Règles de Format

1. **Première colonne** = Noms des data elements (indicateurs)
2. **Autres colonnes** = Noms ou codes des organisations (structures)
3. **Cellules** = Valeurs numériques à importer
4. **Correspondance** :
   - Noms des indicateurs doivent matcher avec les data elements DHIS2
   - Noms des structures doivent matcher avec les organisations DHIS2

## 🔧 Modes de Fonctionnement

### Mode 1 : Multi-DE Automatique (Nouveau ✨)

**Utilisation :** Fichiers TCD avec plusieurs indicateurs différents

**Configuration :**
```json
{
  "sheet_name": "TCD Étudiants",
  "mode": "pivot",
  "period": "2024"
  // data_element_id : NON FOURNI
}
```

**Fonctionnement :**
1. Lit la première colonne pour obtenir les noms d'indicateurs
2. Pour chaque ligne, cherche le data element correspondant dans les métadonnées
3. Génère les dataValues avec le bon DE pour chaque ligne

**Exemple de Mapping :**
```
"Nombre de Licence"  → Recherche dans metadata.de_name_to_id
                     → Trouve "dE1x2y3z4a5"
                     → Utilise ce DE pour toute la ligne

"Nombre de Master"   → Recherche dans metadata.de_name_to_id
                     → Trouve "dE6x7y8z9b0"
                     → Utilise ce DE pour toute la ligne
```

### Mode 2 : Mono-DE (Ancien, toujours supporté)

**Utilisation :** TCD où toutes les lignes représentent le même indicateur

**Configuration :**
```json
{
  "sheet_name": "Répartition par structure",
  "mode": "pivot",
  "data_element_id": "dE1x2y3z4a5",
  "period": "2024"
}
```

**Fonctionnement :**
- Utilise le même `data_element_id` pour toutes les lignes
- Ignore les noms dans la première colonne

## 💡 Exemples d'Utilisation

### Exemple 1 : Effectifs Universitaires

**Fichier Excel :**
```
Indicateur                    │ USSGB │ USTB │ UMN │ UNA
──────────────────────────────┼───────┼──────┼─────┼─────
Effectif Licence Science      │  450  │  320 │ 280 │ 510
Effectif Licence Lettres      │  380  │  290 │ 310 │ 420
Effectif Master Science       │   85  │   62 │  58 │  95
Effectif Master Lettres       │   72  │   58 │  64 │  78
Effectif Doctorat             │   18  │   15 │  12 │  22
```

**Résultat :**
- **5 data elements** détectés automatiquement
- **4 organisations** détectées
- **20 dataValues** générées (5 × 4)

### Exemple 2 : Indicateurs de Santé

**Fichier Excel :**
```
Indicateur                    │ CS_Nord │ CS_Sud │ CS_Est │ CS_Ouest
──────────────────────────────┼─────────┼────────┼────────┼──────────
Consultations prénatales      │   1250  │  1180  │  1320  │   1410
Accouchements assistés        │    420  │   395  │   445  │    480
Vaccinations DTC3             │    890  │   825  │   910  │    975
Malnutrition aiguë            │     32  │    28  │    35  │     30
```

**Résultat :**
- **4 data elements** détectés
- **4 centres de santé** détectés
- **16 dataValues** générées

## 🚨 Gestion des Erreurs

### Erreur 1 : Data Element Non Trouvé
```
Ligne : "Effectif Master Chimie"
Erreur : Data element non trouvé dans les métadonnées
Action : Ligne ignorée, erreur comptabilisée
```

**Solution :**
- Vérifier l'orthographe exacte dans DHIS2
- Utiliser le nom exact (sensible à la casse)
- Ou utiliser le mode mono-DE si tous identiques

### Erreur 2 : Organisation Non Trouvée
```
Colonne : "Université de Maradi"
Erreur : Organisation non trouvée
Action : Colonne entière ignorée
```

**Solution :**
- Vérifier que l'organisation existe dans les métadonnées
- Utiliser le code au lieu du nom (plus fiable)
- Vérifier l'orthographe

### Erreur 3 : Valeurs Manquantes
```
Valeur : (vide) ou "N/A"
Action : Cellule ignorée (normal)
```

## 📊 Statistiques Retournées

```json
{
  "total_rows": 5,
  "total_columns": 4,
  "valid_rows": 18,
  "unique_data_elements": 5,
  "errors": {
    "org": 2,
    "value": 0,
    "de_not_found": 2,
    "de_name_empty": 0
  },
  "error_rate": 10.0
}
```

**Interprétation :**
- `total_rows` : Nombre de lignes dans le TCD
- `total_columns` : Nombre d'organisations (colonnes)
- `valid_rows` : Nombre de dataValues générées
- `unique_data_elements` : Nombre de DE différents utilisés
- `errors.de_not_found` : Lignes ignorées (DE introuvable)

## 🎓 Bonnes Pratiques

### ✅ À Faire

1. **Noms Exacts**
   - Utiliser les noms EXACTS des data elements DHIS2
   - Respecter la casse et l'orthographe

2. **Codes d'Organisation**
   - Préférer les codes aux noms (plus fiables)
   - Exemple : `"CS001"` plutôt que `"Centre de Santé Nord"`

3. **Période Explicite**
   - Toujours spécifier la période dans la requête
   - Format selon le type : `"2024"`, `"202401"`, `"2024Q1"`, etc.

4. **Validation**
   - Vérifier les statistiques retournées
   - Examiner les erreurs avant import

### ❌ À Éviter

1. **Noms Approximatifs**
   - ❌ `"Licence"` au lieu de `"Effectif Licence"`
   - ❌ Abréviations non officielles

2. **Colonnes Vides**
   - Enlever les colonnes de totaux/moyennes
   - Garder uniquement les structures réelles

3. **Valeurs Non Numériques**
   - ❌ `"N/A"`, `"Non disponible"`, `"-"`
   - ✅ Laisser la cellule vide

4. **Mélange de Formats**
   - Garder un format homogène dans tout le fichier
   - Ne pas mélanger TCD et format normal

## 🔄 Comparaison avec l'Ancien Mode

| Aspect | Ancien Mode | Nouveau Mode |
|--------|-------------|--------------|
| **Data Elements** | 1 seul (fixe) | N illimité (auto-détecté) |
| **Fichiers requis** | 1 par indicateur | 1 pour tous |
| **Configuration** | `data_element_id` requis | `data_element_id` optionnel |
| **Flexibilité** | Limitée | Complète |
| **Vitesse** | Rapide | Rapide |
| **Cas d'usage** | TCD mono-indicateur | TCD multi-indicateurs |

## 🚀 Évolutions Futures

### Prochaines Améliorations

1. **Fill Down Automatique**
   ```python
   # Pour les cellules fusionnées verticalement
   df[structural_cols] = df[structural_cols].ffill()
   ```

2. **Détection Intelligente des Colonnes**
   ```python
   # Identifier automatiquement colonne indicateurs vs colonnes structures
   indicator_col = detect_indicator_column(df)
   org_cols = [c for c in df.columns if c != indicator_col]
   ```

3. **Support des Catégories dans TCD**
   ```python
   # Ex: Colonne "USSGB - Homme", "USSGB - Femme"
   # Parser pour extraire org + catégorie
   ```

4. **Interface Simplifiée**
   - Upload TCD → Détection auto → Un clic pour importer
   - Pas besoin de sélectionner DE manuellement

---

**Conclusion :** Le nouveau mode TCD multi-DE rend l'import de tableaux croisés dynamiques **beaucoup plus simple et naturel**, en détectant automatiquement les data elements depuis le fichier Excel.
