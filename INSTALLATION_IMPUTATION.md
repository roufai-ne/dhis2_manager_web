# Installation et démarrage du module d'imputation

## Prérequis

Le module d'imputation est déjà intégré à l'application DHIS2 Manager Web. Vous devez simplement installer les nouvelles dépendances.

## Installation des dépendances

### 1. Activer l'environnement virtuel

```bash
# Windows
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web
venv\Scripts\activate

# Linux/Mac
cd /path/to/dhis2_manager_web
source venv/bin/activate
```

### 2. Installer les nouvelles dépendances

Les dépendances suivantes ont été ajoutées au fichier `requirements.txt` :
- `scipy>=1.11.0` : Pour les calculs statistiques et corrélations
- `scikit-learn>=1.3.0` : Pour les algorithmes d'imputation (KNN, etc.)

```bash
pip install -r requirements.txt
```

Ou installer uniquement les nouvelles dépendances :

```bash
pip install scipy>=1.11.0 scikit-learn>=1.3.0
```

## Vérification de l'installation

Exécutez le script de test pour vérifier que tout fonctionne :

```bash
python test_imputation_module.py
```

Si tous les tests passent, vous verrez :

```
================================================================================
RÉSUMÉ DES TESTS
================================================================================
[OK] Tous les tests sont passés avec succès!

Le module d'imputation est prêt à être utilisé.
Accédez à l'interface web via: http://localhost:5000/imputation
================================================================================
```

## Démarrage de l'application

```bash
python run.py
```

L'application sera accessible à l'adresse : **http://localhost:5000**

## Accès au module d'imputation

### Option 1 : Depuis la page d'accueil
1. Ouvrez votre navigateur à l'adresse http://localhost:5000
2. Cliquez sur la carte **"Imputation Automatique"** (icône orange avec baguette magique)

### Option 2 : Accès direct
Accédez directement à : **http://localhost:5000/imputation**

## Structure des fichiers créés

Le module d'imputation a ajouté les fichiers suivants à l'application :

```
dhis2_manager_web/
├── app/
│   ├── routes/
│   │   └── imputation.py                # Routes du module
│   ├── services/
│   │   ├── column_analyzer.py           # Analyse des colonnes
│   │   ├── correlation_engine.py        # Calcul des corrélations
│   │   └── imputation_engine.py         # Moteur d'imputation
│   └── templates/
│       └── imputation.html              # Interface utilisateur
├── README_IMPUTATION.md                  # Documentation complète
├── INSTALLATION_IMPUTATION.md            # Ce fichier
└── test_imputation_module.py             # Script de test
```

## Fichiers modifiés

Les fichiers suivants ont été mis à jour pour intégrer le module :

1. **app/__init__.py** : Ajout du blueprint `imputation`
2. **app/templates/index.html** : Ajout de la carte du module sur la page d'accueil
3. **requirements.txt** : Ajout de scipy et scikit-learn

## Utilisation rapide

### Étape 1 : Préparer vos données
- Format : Excel (.xlsx, .xls) ou CSV
- Contenu : Données avec valeurs manquantes à imputer
- Taille max : 50 Mo

### Étape 2 : Upload
1. Allez sur http://localhost:5000/imputation
2. Glissez-déposez votre fichier ou cliquez sur "Parcourir"
3. Attendez l'analyse automatique

### Étape 3 : Analyse
- Consultez le résumé de qualité
- Visualisez les détails par colonne
- Identifiez les valeurs manquantes et aberrantes

### Étape 4 : Configuration
- Cliquez sur "Obtenir recommandations automatiques"
- Le système recommande la meilleure méthode pour chaque colonne
- Examinez les variables prédictives utilisées

### Étape 5 : Exécution
- Cliquez sur "Exécuter l'imputation"
- Attendez le traitement
- Consultez le rapport détaillé

### Étape 6 : Téléchargement
- Téléchargez votre fichier Excel corrigé
- Toutes les valeurs manquantes sont remplies

## Exemples de fichiers de test

Vous pouvez créer un fichier de test simple avec le script suivant :

```python
import pandas as pd
import numpy as np

# Créer des données avec valeurs manquantes
np.random.seed(42)
data = {
    'Nom': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Henry'],
    'Age': [25, np.nan, 30, np.nan, 28, 35, np.nan, 40],
    'Sexe': ['F', 'M', 'M', 'M', 'F', np.nan, 'F', 'M'],
    'Salaire': [50000, 55000, np.nan, 60000, 52000, np.nan, 58000, 65000],
    'Diplome': ['Licence', 'Master', 'Master', np.nan, 'Licence', 'Doctorat', 'Master', 'Doctorat']
}

df = pd.DataFrame(data)
df.to_excel('test_imputation.xlsx', index=False)
print("Fichier test_imputation.xlsx créé avec succès!")
```

## Dépannage

### Erreur : "Module not found: scipy"
```bash
pip install scipy>=1.11.0
```

### Erreur : "Module not found: sklearn"
```bash
pip install scikit-learn>=1.3.0
```

### Erreur : "No module named 'app.services.column_analyzer'"
Vérifiez que vous êtes dans le bon répertoire et que tous les fichiers ont été créés :
```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web
ls app/services/column_analyzer.py
ls app/services/correlation_engine.py
ls app/services/imputation_engine.py
```

### L'interface ne s'affiche pas correctement
1. Videz le cache du navigateur (Ctrl+F5)
2. Vérifiez la console JavaScript pour les erreurs (F12)
3. Redémarrez l'application Flask

### Les fichiers uploadés ne sont pas traités
Vérifiez que le dossier `uploads/` existe :
```bash
mkdir uploads
```

## Support

Pour toute question ou problème :
1. Consultez le fichier [README_IMPUTATION.md](README_IMPUTATION.md) pour la documentation complète
2. Exécutez le script de test : `python test_imputation_module.py`
3. Vérifiez les logs de l'application dans `logs/app.log`

## Prochaines étapes

Une fois le module installé et testé :
1. Lisez la documentation complète dans [README_IMPUTATION.md](README_IMPUTATION.md)
2. Testez avec vos propres fichiers de données
3. Explorez les différentes méthodes d'imputation disponibles
4. Consultez les recommandations automatiques pour comprendre le choix des méthodes

Bon travail avec le module d'imputation automatique!
