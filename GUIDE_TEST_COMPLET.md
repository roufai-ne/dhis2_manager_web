# Guide de Test Complet - Multi-Onglets & Tableaux Croisés

## 🎯 Objectif

Tester la nouvelle fonctionnalité permettant de :
- Sélectionner l'onglet d'un fichier Excel à traiter
- Choisir entre mode normal et mode tableau croisé
- Traiter des données en mode pivot avec sélection de data element

---

## 📋 Prérequis

### 1. Métadonnées chargées

Assurez-vous d'avoir chargé les métadonnées :
- Ouvrez http://localhost:5000/configuration
- Chargez `metadata.json`
- Vérifiez que les organisations et data elements sont présents

### 2. Fichier Excel de test

Créez un fichier Excel avec plusieurs onglets. Vous pouvez utiliser le script fourni :

**Créer `create_test_file.py` :**

```python
import pandas as pd

# Onglet 1 : Données normales (mode template)
data_normal = {
    'Structure': ['Faculté A', 'Faculté B', 'Faculté C'],
    'Data Element': ['Inscrits', 'Inscrits', 'Inscrits'],
    'Période': ['2024', '2024', '2024'],
    'Valeur': [150, 200, 180]
}
df_normal = pd.DataFrame(data_normal)

# Onglet 2 : Tableau croisé (mode pivot)
data_pivot = {
    'Indicateur': ['Inscrits', 'Diplômés', 'Abandons'],
    'Faculté A': [150, 45, 10],
    'Faculté B': [200, 60, 12],
    'Faculté C': [180, 55, 8]
}
df_pivot = pd.DataFrame(data_pivot)

# Onglet 3 : Autre tableau croisé
data_pivot2 = {
    'Indicateur': ['Garçons', 'Filles', 'Total'],
    'Faculté A': [80, 70, 150],
    'Faculté B': [110, 90, 200],
    'Faculté C': [95, 85, 180]
}
df_pivot2 = pd.DataFrame(data_pivot2)

# Sauvegarder
with pd.ExcelWriter('TEST_Multi_20251215.xlsx') as writer:
    df_normal.to_excel(writer, sheet_name='Données', index=False)
    df_pivot.to_excel(writer, sheet_name='Premier Cycle', index=False)
    df_pivot2.to_excel(writer, sheet_name='Deuxième Cycle', index=False)

print("✅ Fichier TEST_Multi_20251215.xlsx créé avec succès")
print("   - Onglet 'Données' : mode normal")
print("   - Onglet 'Premier Cycle' : tableau croisé")
print("   - Onglet 'Deuxième Cycle' : tableau croisé")
```

**Exécuter :**
```bash
python create_test_file.py
```

---

## 🧪 Scénarios de test

### Test 1 : Fichier mono-onglet (Rétrocompatibilité)

**Objectif** : Vérifier que l'ancien comportement fonctionne toujours

**Étapes** :
1. Créez un fichier Excel avec UN SEUL onglet nommé "Données"
2. Ouvrez http://localhost:5000/calculator
3. Uploadez le fichier
4. ✅ Le sélecteur d'onglets NE doit PAS apparaître
5. ✅ Le mode "Normal" est sélectionné par défaut
6. Cliquez "Traiter"
7. ✅ Le fichier est traité normalement

**Résultat attendu** : Fonctionne exactement comme avant

---

### Test 2 : Fichier multi-onglets + Mode normal

**Objectif** : Vérifier la sélection d'onglets en mode normal

**Étapes** :
1. Ouvrez http://localhost:5000/calculator
2. Uploadez `TEST_Multi_20251215.xlsx`
3. ✅ Le sélecteur d'onglets APPARAÎT avec badge "3 onglets"
4. ✅ Les 3 onglets sont listés dans le dropdown
5. Sélectionnez "Premier Cycle"
6. ✅ Le mode "Normal" est sélectionné (carte bleue)
7. Cliquez "Traiter"
8. ✅ Vérifiez dans les logs : `Traitement du template (onglet: Premier Cycle, mode: normal)`

**Résultat attendu** : L'onglet "Premier Cycle" est traité en mode normal

---

### Test 3 : Mode tableau croisé SANS data element

**Objectif** : Vérifier la validation du data element

**Étapes** :
1. Uploadez `TEST_Multi_20251215.xlsx`
2. Sélectionnez l'onglet "Premier Cycle"
3. Cliquez sur la carte "Tableau Croisé" (violet)
4. ✅ Le panneau violet "Options pivot" APPARAÎT
5. ✅ Le dropdown "Data Element" est visible
6. NE SÉLECTIONNEZ PAS de data element
7. Cliquez "Traiter"
8. ✅ Message d'erreur : "Veuillez sélectionner un Data Element pour le mode tableau croisé"

**Résultat attendu** : Le traitement est bloqué avec un message d'erreur

---

### Test 4 : Mode tableau croisé complet

**Objectif** : Traiter un tableau croisé avec succès

**Étapes** :
1. Uploadez `TEST_Multi_20251215.xlsx`
2. Sélectionnez l'onglet "Premier Cycle"
3. Cliquez sur la carte "Tableau Croisé"
4. ✅ Le panneau violet apparaît
5. Sélectionnez un data element dans le dropdown
6. Cliquez "Traiter"
7. ✅ Vérifiez les logs : `Traitement tableau croisé: Premier Cycle avec DE=abc123`
8. ✅ Vérifiez les statistiques affichées
9. ✅ Téléchargez le JSON généré
10. Ouvrez le JSON et vérifiez :
    - Toutes les valeurs ont le même `dataElement` (celui sélectionné)
    - Les `orgUnit` correspondent aux noms des colonnes
    - Les valeurs sont correctes

**Résultat attendu** :
```json
{
  "dataValues": [
    {
      "dataElement": "abc123",
      "period": "2024",
      "orgUnit": "orgId_FacA",
      "categoryOptionCombo": "default",
      "attributeOptionCombo": "default",
      "value": "150"
    },
    ...
  ]
}
```

---

### Test 5 : Changement dynamique de mode

**Objectif** : Vérifier le comportement interactif de l'interface

**Étapes** :
1. Uploadez un fichier
2. Cliquez "Tableau Croisé"
3. ✅ Le panneau violet APPARAÎT
4. Cliquez "Mode Normal"
5. ✅ Le panneau violet DISPARAÎT
6. Cliquez à nouveau "Tableau Croisé"
7. ✅ Le panneau violet RÉAPPARAÎT
8. ✅ Le dropdown de data elements est chargé

**Résultat attendu** : L'interface réagit instantanément aux changements

---

### Test 6 : Traiter plusieurs onglets successivement

**Objectif** : Vérifier qu'on peut traiter plusieurs onglets sans recharger

**Étapes** :
1. Uploadez `TEST_Multi_20251215.xlsx`
2. Sélectionnez "Premier Cycle" + Mode pivot + Data Element "Inscrits"
3. Cliquez "Traiter" → ✅ Succès
4. Sans recharger la page, changez l'onglet à "Deuxième Cycle"
5. Gardez le mode pivot et le data element "Inscrits"
6. Cliquez "Traiter" → ✅ Succès
7. Changez le data element à "Diplômés"
8. Cliquez "Traiter" → ✅ Succès

**Résultat attendu** : Chaque traitement utilise les bons paramètres

---

## 🔍 Vérifications détaillées

### Vérifier les logs

Consultez `logs/app.log` :

```bash
tail -f dhis2_manager_web/logs/app.log
```

**Logs attendus** :
```
INFO - Onglets détectés dans /path/file.xlsx: ['Données', 'Premier Cycle', 'Deuxième Cycle']
INFO - Traitement du template: /path/file.xlsx (onglet: Premier Cycle, mode: pivot)
INFO - Traitement tableau croisé: Premier Cycle avec DE=abc123
WARNING - Organisation inconnue: Faculté XYZ  (si une structure n'existe pas)
INFO - Traitement tableau croisé terminé: 9 valeurs valides
```

---

### Vérifier les statistiques affichées

Après un traitement, l'interface affiche :
- **Total de valeurs** : Nombre total de cellules traitées
- **Valeurs valides** : Cellules avec données valides
- **Erreurs** : Cellules avec erreurs (org non trouvée, valeur invalide)
- **Taux d'erreur** : Pourcentage

**Exemple pour un tableau 3x3** :
- Total rows: 3
- Total columns: 3
- Valid rows: 9 (si toutes les orgs sont trouvées)
- Errors: 0
- Error rate: 0%

---

### Vérifier le JSON généré

1. Après traitement, cliquez "Aperçu JSON"
2. Vérifiez la structure :

**Mode normal** :
- Les `dataElement` varient selon les lignes

**Mode pivot** :
- Tous les `dataElement` sont identiques (celui sélectionné)
- Les `orgUnit` correspondent aux noms des colonnes Excel

---

## 🐛 Problèmes possibles et solutions

### Problème 1 : "Métadonnées non chargées"

**Cause** : Les métadonnées ne sont pas en session

**Solution** :
1. Allez à http://localhost:5000/configuration
2. Chargez `metadata.json`
3. Réessayez

---

### Problème 2 : "Organisation inconnue"

**Cause** : Les noms de colonnes ne correspondent pas aux métadonnées

**Solution** :
1. Ouvrez `metadata.json`
2. Vérifiez les noms exacts des organisations
3. Renommez les colonnes Excel pour correspondre exactement
4. OU ajoutez des codes aux organisations dans les métadonnées

---

### Problème 3 : Le sélecteur d'onglets ne s'affiche pas

**Cause** : Le fichier n'a qu'un seul onglet OU erreur de chargement

**Solution** :
1. Ouvrez la console du navigateur (F12)
2. Vérifiez les erreurs JavaScript
3. Vérifiez que le fichier a bien plusieurs onglets

---

### Problème 4 : Le dropdown de data elements est vide

**Cause** : Les métadonnées n'ont pas de data elements

**Solution** :
1. Vérifiez que `metadata.json` contient une section `dataElements`
2. Rechargez les métadonnées
3. Vérifiez dans la console : "X data elements chargés"

---

## ✅ Checklist de test complète

- [ ] Test 1 : Fichier mono-onglet → ✅ Rétrocompatibilité
- [ ] Test 2 : Fichier multi-onglets + mode normal → ✅ Sélection onglet
- [ ] Test 3 : Mode pivot sans DE → ❌ Validation erreur
- [ ] Test 4 : Mode pivot complet → ✅ Traitement pivot
- [ ] Test 5 : Changement dynamique mode → ✅ Réactivité UI
- [ ] Test 6 : Traiter plusieurs onglets → ✅ Paramètres corrects
- [ ] Logs vérifiés → ✅ Messages corrects
- [ ] Statistiques affichées → ✅ Valeurs cohérentes
- [ ] JSON généré → ✅ Format DHIS2 correct

---

## 📊 Résultats attendus finaux

Si tous les tests passent :

✅ **Backend** : Traite correctement les deux modes
✅ **Frontend** : Interface réactive et intuitive
✅ **Rétrocompatibilité** : Ancien comportement préservé
✅ **Validation** : Erreurs détectées et signalées
✅ **Logs** : Traçabilité complète

---

## 📞 Support

En cas de problème :
1. Consultez les logs : `logs/app.log`
2. Ouvrez la console du navigateur (F12)
3. Vérifiez les métadonnées chargées
4. Vérifiez le format du fichier Excel

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
**Version** : 2.0
**Prêt à tester** : ✅
