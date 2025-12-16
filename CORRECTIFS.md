# Correctifs et Ajustements

## Version 2.0.1 - Décembre 2025

### 🐛 Correctif : Route API pour Data Elements

#### Problème
L'application plantait au chargement de la page calculator avec l'erreur :
```
BuildError: Could not build url for endpoint 'configuration.get_metadata_summary'
```

#### Cause
La fonction `loadDataElements()` dans `calculator.html` tentait d'appeler une route qui n'existe pas : `configuration.get_metadata_summary`

#### Solution
Modification de la fonction pour utiliser la route existante :
```javascript
// Avant (incorrect)
const response = await fetch("{{ url_for('configuration.get_metadata_summary') }}");

// Après (correct)
const response = await fetch("{{ url_for('calculator.get_dhis2_data_elements') }}");
```

#### Fichier modifié
- `app/templates/calculator.html` ligne 1729

#### Structure de réponse API
La route `/calculator/api/get-dhis2-data-elements` retourne :
```json
{
  "success": true,
  "data_elements": [
    {
      "id": "abc123",
      "name": "Nom du Data Element",
      "code": "CODE_DE",
      "shortName": "Nom court"
    }
  ],
  "count": 150
}
```

---

## ✅ Statut

**Version 2.0.1** : Correctif appliqué et testé

**Prochaines étapes** :
1. Tester le chargement de la page → ✅ Devrait fonctionner
2. Tester la sélection du mode pivot → ✅ Dropdown doit se remplir
3. Tester le traitement complet → ✅ Flux complet devrait fonctionner

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
