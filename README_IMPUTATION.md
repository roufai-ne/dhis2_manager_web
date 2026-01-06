# Module d'Imputation Automatique de Données

## Vue d'ensemble

Le module d'imputation automatique est un composant intégré à l'application **DHIS2 Manager Web** qui permet d'analyser automatiquement la qualité des données et de compléter intelligemment les valeurs manquantes en utilisant les corrélations entre colonnes.

## Fonctionnalités principales

### 1. Analyse automatique des données
- **Détection automatique des types** : Numérique (continu/discret), Catégoriel (nominal/ordinal), Booléen, Date, Texte
- **Statistiques descriptives** : Moyenne, médiane, mode, écart-type, quartiles, skewness, kurtosis
- **Détection des anomalies** : Valeurs manquantes, valeurs aberrantes (méthode IQR), problèmes de format
- **Score de qualité** : Calcul d'un score de qualité (0-100) pour chaque colonne

### 2. Moteur de corrélation
- **Corrélations mixtes** : Support de tous types de variables
  - Numérique vs Numérique : Corrélation de Spearman
  - Catégoriel vs Catégoriel : V de Cramér
  - Numérique vs Catégoriel : Ratio de corrélation (Eta)
- **Sélection automatique** : Identification des meilleures variables prédictives
- **Matrice de corrélation** : Visualisation des relations entre colonnes

### 3. Stratégies d'imputation multiples

#### Méthodes simples
- Moyenne, Médiane, Mode
- Valeur constante
- Forward fill / Backward fill (pour séries temporelles)

#### Méthodes par groupe
- Imputation hiérarchique avec fallback progressif
- Moyenne/Médiane/Mode par groupe de variables corrélées
- Exemple : Moyenne par (SEXE, DIPLOME, STATUT) → (SEXE, DIPLOME) → (SEXE) → Globale

#### Méthodes avancées
- **KNN Imputer** : K plus proches voisins
- Support des variables catégorielles via encodage

### 4. Sélection automatique de la méthode
Le système recommande automatiquement la meilleure méthode selon :
- Le type de données
- Le pourcentage de valeurs manquantes
- La force des corrélations avec autres colonnes
- La présence de valeurs aberrantes

## Architecture du module

```
app/
├── routes/
│   └── imputation.py              # Blueprint Flask avec tous les endpoints
├── services/
│   ├── column_analyzer.py         # Service d'analyse des colonnes
│   ├── correlation_engine.py      # Moteur de calcul des corrélations
│   └── imputation_engine.py       # Moteur d'imputation principal
└── templates/
    └── imputation.html            # Interface utilisateur (Alpine.js + Tailwind)
```

## Workflow utilisateur

### Étape 1 : Upload du fichier
- Formats acceptés : Excel (.xlsx, .xls), CSV
- Taille maximale : 50 Mo
- Détection automatique de l'encodage et du séparateur (CSV)
- Support des fichiers Excel multi-feuilles

### Étape 2 : Analyse de la qualité
- Résumé global : nombre de lignes, colonnes, valeurs manquantes, score qualité
- Tableau détaillé par colonne :
  - Type détecté
  - Nombre et pourcentage de valeurs manquantes
  - Nombre de valeurs aberrantes
  - Score de qualité (barre de progression colorée)

### Étape 3 : Configuration de l'imputation
- Recommandations automatiques pour chaque colonne
- Affichage de la méthode recommandée
- Affichage des variables prédictives utilisées
- Possibilité de personnalisation (à venir)

### Étape 4 : Résultats et téléchargement
- Rapport détaillé des corrections effectuées
- Nombre de valeurs imputées par colonne
- Méthode utilisée pour chaque colonne
- Téléchargement du fichier Excel corrigé

## Endpoints API

### Upload et analyse
```
POST /imputation/upload
→ Upload fichier et analyse initiale

POST /imputation/change-sheet
→ Change la feuille Excel active

GET /imputation/analysis/<file_id>
→ Analyse détaillée par colonne
```

### Corrélations et recommandations
```
GET /imputation/correlations/<file_id>
→ Matrice de corrélation complète

GET /imputation/recommendations/<file_id>
→ Recommandations d'imputation par colonne
```

### Exécution et résultats
```
POST /imputation/execute
→ Exécute l'imputation selon la configuration
Body: {
    "file_id": "uuid",
    "configuration": {
        "column_name": {
            "method": "knn",
            "parameters": {...}
        }
    }
}

GET /imputation/download/<file_id>
→ Télécharge le fichier imputé

GET /imputation/report/<file_id>
→ Rapport d'imputation JSON
```

### Gestion
```
POST /imputation/clear
→ Nettoie la session et supprime les fichiers temporaires
```

## Technologies utilisées

### Backend
- **Flask** : Framework web
- **Pandas** : Manipulation de données
- **NumPy** : Calculs numériques
- **SciPy** : Tests statistiques et corrélations
- **Scikit-learn** : KNNImputer, SimpleImputer, preprocessing

### Frontend
- **Alpine.js** : Réactivité de l'interface
- **Tailwind CSS** : Styles
- **Font Awesome** : Icônes

## Configuration

### Variables d'environnement
Aucune configuration spécifique requise. Le module utilise la configuration de base de l'application DHIS2 Manager.

### Paramètres modifiables
Dans le code source, vous pouvez ajuster :
- `min_correlation` : Seuil minimum de corrélation (défaut: 0.3)
- `max_predictors` : Nombre maximum de prédicteurs (défaut: 5)
- `n_neighbors` : Nombre de voisins pour KNN (défaut: 5)

## Exemples d'utilisation

### Cas d'usage 1 : Données démographiques incomplètes
**Problème** : Fichier avec dates de naissance manquantes

**Solution automatique** :
- Détection : Colonne DATE_NAISSANCE = numérique
- Analyse : 41% de valeurs manquantes
- Corrélations : SEXE (η=0.72), DIPLOME (η=0.65), STATUT (η=0.58)
- Méthode : Imputation hiérarchique par groupe
  - Moyenne par (SEXE, DIPLOME, STATUT)
  - Fallback : Moyenne par (SEXE, DIPLOME)
  - Fallback : Moyenne par SEXE
  - Fallback : Moyenne globale

### Cas d'usage 2 : Données catégorielles
**Problème** : Valeurs de STATUT manquantes

**Solution automatique** :
- Détection : Colonne STATUT = catégoriel nominal
- Analyse : 15% de valeurs manquantes
- Corrélations : DIPLOME (V=0.55), SEXE (V=0.38)
- Méthode : Mode par groupe (DIPLOME, SEXE)

### Cas d'usage 3 : Données numériques avec outliers
**Problème** : Revenus avec valeurs aberrantes et manquantes

**Solution automatique** :
- Détection : Colonne REVENU = numérique continu
- Analyse : 23 outliers détectés (méthode IQR), 8% manquants
- Recommandation : Traiter outliers avant imputation
- Méthode : Médiane (robuste aux outliers)

## Matrice de décision automatique

| Type de donnée | % Manquant | Corrélation | Méthode recommandée |
|----------------|------------|-------------|---------------------|
| Numérique | < 5% | Faible | Médiane |
| Numérique | < 5% | Forte | Moyenne par groupe |
| Numérique | 5-20% | Faible | Médiane |
| Numérique | 5-20% | Forte | KNN / Moyenne par groupe |
| Numérique | 20-40% | Toute | KNN |
| Numérique | > 40% | Toute | KNN + Avertissement fiabilité |
| Catégoriel | < 10% | Faible | Mode global |
| Catégoriel | < 10% | Forte | Mode par groupe |
| Catégoriel | 10-30% | Forte | Mode par groupe |
| Catégoriel | > 30% | Toute | Mode + Avertissement |
| Date | Toute | Moyenne | Médiane des dates |

## Limitations et améliorations futures

### Limitations actuelles
- Pas de validation croisée implémentée (placeholder dans le code)
- Pas de support pour MICE (Multiple Imputation by Chained Equations)
- Pas de support pour Random Forest Imputer
- Configuration manuelle limitée dans l'interface

### Améliorations prévues
1. **Validation croisée** : Masquage aléatoire de 10% des valeurs pour mesurer la précision
2. **Algorithmes avancés** : MICE, Random Forest, Deep Learning
3. **Visualisations** :
   - Heatmap des valeurs manquantes
   - Distributions avant/après imputation
   - Matrice de corrélation interactive
4. **Export de rapport** : PDF avec graphiques et statistiques
5. **Configuration avancée** : Permettre à l'utilisateur de choisir manuellement les méthodes
6. **Historique** : Sauvegarder l'historique des imputations effectuées

## Intégration avec DHIS2 Manager

Le module d'imputation est entièrement intégré à l'application DHIS2 Manager Web :
- **Authentification** : Utilise le système de session de l'application
- **Logging** : Logs centralisés avec `activity_logger`
- **File handling** : Réutilise `FileHandler` existant
- **Excel operations** : Compatible avec `ExcelService`
- **UI/UX** : Design cohérent avec le reste de l'application

## Support et contribution

Pour toute question ou suggestion d'amélioration :
- Créer une issue dans le dépôt du projet
- Contacter l'équipe de développement DSI

## License

Ce module fait partie de l'application DHIS2 Manager Web développée pour le MESRIT Niger.
