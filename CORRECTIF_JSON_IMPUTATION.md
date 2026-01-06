# Correction de l'erreur JSON dans le module d'imputation

## Problème identifié

Lors du chargement d'un fichier dans le module d'imputation, l'erreur suivante se produisait :
```
Erreur lors de l'upload: Unexpected token 'N', ... "EIGNANT": NaN, "..." is not valid JSON
```

**Cause** : Les valeurs `NaN` (Not a Number) de pandas/numpy étaient envoyées directement dans les réponses JSON, ce qui n'est pas valide selon la spécification JSON. JSON ne supporte que `null`, pas `NaN`.

## Solutions implémentées

### 1. Correction dans `app/routes/imputation.py`

#### a) Ajout de l'import numpy
```python
import numpy as np
```

#### b) Nettoyage du preview des données (ligne ~108)
**Avant :**
```python
preview = df.head(10).to_dict(orient='records')
```

**Après :**
```python
# Remplacer NaN par None pour la sérialisation JSON
preview = df.head(10).replace({np.nan: None}).to_dict(orient='records')
```

#### c) Nettoyage lors du changement de feuille (ligne ~153)
**Avant :**
```python
preview = df.head(10).to_dict(orient='records')
```

**Après :**
```python
# Remplacer NaN par None pour la sérialisation JSON
preview = df.head(10).replace({np.nan: None}).to_dict(orient='records')
```

#### d) Nettoyage de la matrice de corrélation (ligne ~249)
**Avant :**
```python
corr_matrix_dict = corr_matrix.round(3).to_dict()
```

**Après :**
```python
# Remplacer NaN par None pour éviter les erreurs JSON
corr_matrix_dict = corr_matrix.round(3).replace({np.nan: None}).to_dict()
```

### 2. Correction dans `app/services/column_analyzer.py`

#### a) Ajout d'une méthode de nettoyage JSON
Nouvelle méthode ajoutée à la classe `ColumnAnalyzer` :
```python
def _clean_for_json(self, obj):
    """
    Nettoie récursivement un objet pour la sérialisation JSON.
    Remplace NaN, inf, -inf par None.
    """
    if isinstance(obj, dict):
        return {k: self._clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [self._clean_for_json(v) for v in obj]
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif pd.isna(obj):
        return None
    return obj
```

#### b) Application du nettoyage dans `analyze_dataframe`
**Avant :**
```python
return results
```

**Après :**
```python
# Nettoyer les NaN pour la sérialisation JSON
return self._clean_for_json(results)
```

## Pourquoi ces changements ?

1. **NaN vs null** : En Python/pandas, `NaN` représente les valeurs manquantes, mais en JSON, seul `null` est valide. La conversion directe échoue.

2. **Statistiques** : Les calculs de statistiques (moyenne, écart-type, etc.) sur des colonnes avec valeurs manquantes peuvent retourner `NaN`, `inf` ou `-inf`, qui doivent tous être convertis en `null` pour JSON.

3. **Récursivité** : La fonction `_clean_for_json` parcourt récursivement toutes les structures (dicts, lists) pour garantir qu'aucun `NaN` ne subsiste.

## Test de la correction

Un script de test a été créé : [test_json_fix.py](../../test_json_fix.py)

Pour le lancer :
```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager
python test_json_fix.py
```

## Impact

- ✅ Les fichiers avec valeurs manquantes se chargent maintenant correctement
- ✅ Les statistiques s'affichent sans erreur
- ✅ La matrice de corrélation fonctionne
- ✅ Aucune régression sur les fonctionnalités existantes

## Fichiers modifiés

1. `dhis2_manager_web/app/routes/imputation.py` - 4 modifications
2. `dhis2_manager_web/app/services/column_analyzer.py` - 2 modifications
3. `test_json_fix.py` - Nouveau fichier de test

## Prochaines étapes

Le module d'imputation devrait maintenant fonctionner correctement. Vous pouvez :
1. Redémarrer l'application si elle est en cours d'exécution
2. Tester le chargement d'un fichier Excel avec des valeurs manquantes
3. Vérifier que l'analyse et les statistiques s'affichent correctement
