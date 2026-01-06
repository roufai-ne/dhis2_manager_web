# Module d'Imputation Automatique de Données
## Spécifications Techniques et Prompts de Développement

---

# TABLE DES MATIÈRES

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture du Module](#2-architecture-du-module)
3. [Prompts par Composant](#3-prompts-par-composant)
4. [Algorithmes d'Imputation](#4-algorithmes-dimputation)
5. [API et Endpoints](#5-api-et-endpoints)
6. [Interface Utilisateur](#6-interface-utilisateur)
7. [Modèles de Données](#7-modèles-de-données)

---

# 1. VUE D'ENSEMBLE

## 1.1 Objectif
Créer un module web permettant d'importer des fichiers Excel/CSV, d'analyser automatiquement la qualité des données, d'identifier les valeurs manquantes ou aberrantes, et de les imputer intelligemment en utilisant les corrélations entre colonnes.

## 1.2 Workflow Utilisateur
```
Upload fichier → Analyse automatique → Rapport qualité → Configuration imputation → Traitement → Téléchargement fichier corrigé
```

## 1.3 Stack Technique Recommandé
- **Backend**: Python (FastAPI ou Django REST)
- **Traitement données**: Pandas, NumPy, Scikit-learn
- **Frontend**: React/Next.js ou Vue.js
- **Base de données**: PostgreSQL (stockage temporaire des fichiers traités)

---

# 2. ARCHITECTURE DU MODULE

## 2.1 Composants Principaux

```
┌─────────────────────────────────────────────────────────────────┐
│                     MODULE IMPUTATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   UPLOAD    │───▶│  ANALYZER   │───▶│  CORRELATION ENGINE │ │
│  │   SERVICE   │    │   SERVICE   │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                            │                      │             │
│                            ▼                      ▼             │
│                     ┌─────────────┐    ┌─────────────────────┐ │
│                     │   REPORT    │    │  IMPUTATION ENGINE  │ │
│                     │  GENERATOR  │    │                     │ │
│                     └─────────────┘    └─────────────────────┘ │
│                                                   │             │
│                                                   ▼             │
│                                        ┌─────────────────────┐ │
│                                        │   EXPORT SERVICE    │ │
│                                        └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 2.2 Services Détaillés

| Service | Responsabilité |
|---------|----------------|
| Upload Service | Validation fichier, parsing Excel/CSV, stockage temporaire |
| Analyzer Service | Détection types, statistiques, identification anomalies |
| Correlation Engine | Calcul corrélations, sélection variables prédictives |
| Imputation Engine | Application algorithmes selon type de données |
| Report Generator | Génération rapport qualité avant/après |
| Export Service | Export fichier corrigé + rapport |

---

# 3. PROMPTS PAR COMPOSANT

---

## PROMPT 1 : Service d'Upload et Parsing

```
Contexte: Je développe un module d'imputation de données pour une application web.

Objectif: Créer un service d'upload et de parsing de fichiers Excel/CSV.

Spécifications fonctionnelles:
1. Accepter les formats: .xlsx, .xls, .csv, .tsv
2. Taille maximale: 50 Mo
3. Détecter automatiquement:
   - L'encodage du fichier (UTF-8, Latin-1, etc.)
   - Le séparateur pour CSV (;  ,  \t)
   - La ligne d'en-tête
   - Les feuilles disponibles (Excel multi-feuilles)
4. Retourner un aperçu des 100 premières lignes
5. Gérer les erreurs de parsing gracieusement

Spécifications techniques:
- Framework: FastAPI
- Librairies: pandas, openpyxl, chardet
- Stockage temporaire: système de fichiers avec UUID
- Durée de rétention: 24 heures

Output attendu:
- Code Python complet du service
- Endpoints REST documentés
- Schémas Pydantic pour validation
- Tests unitaires

Contraintes:
- Code production-ready avec gestion d'erreurs
- Logging structuré
- Documentation docstrings
```

---

## PROMPT 2 : Service d'Analyse des Colonnes

```
Contexte: Module d'imputation de données - composant d'analyse automatique des colonnes.

Objectif: Créer un service qui analyse chaque colonne d'un DataFrame et produit un rapport détaillé.

Pour chaque colonne, détecter et calculer:

1. TYPE DE DONNÉES:
   - Numérique continu (float)
   - Numérique discret (entier)
   - Catégoriel nominal (texte sans ordre)
   - Catégoriel ordinal (texte avec ordre implicite)
   - Date/Datetime
   - Booléen
   - Texte libre
   - Mixte (problématique)

2. STATISTIQUES DESCRIPTIVES:
   Pour numérique: count, mean, std, min, max, median, Q1, Q3, skewness, kurtosis
   Pour catégoriel: count, unique, top, freq, distribution des modalités
   Pour dates: min, max, plage, fréquence

3. QUALITÉ DES DONNÉES:
   - Nombre et pourcentage de valeurs manquantes
   - Nombre et pourcentage de valeurs aberrantes (IQR, Z-score)
   - Valeurs dupliquées
   - Formats incohérents (ex: dates mal formatées, nombres avec texte)
   - Espaces superflus, caractères spéciaux

4. PATTERNS DÉTECTÉS:
   - Regex pour formats standards (email, téléphone, date, code postal)
   - Valeurs sentinelles (999, -1, N/A, NULL, etc.)

Format de sortie (JSON):
{
  "column_name": {
    "detected_type": "numeric_continuous",
    "confidence": 0.95,
    "statistics": {...},
    "quality": {
      "missing_count": 150,
      "missing_percent": 10.5,
      "outliers_count": 23,
      "outliers_indices": [12, 45, 78, ...],
      "format_issues": [...]
    },
    "recommendations": [
      "Imputation recommandée: moyenne par groupe",
      "23 valeurs aberrantes détectées"
    ]
  }
}

Technologies: Python, Pandas, NumPy, SciPy

Livrer: Code complet avec classe ColumnAnalyzer et méthodes associées.
```

---

## PROMPT 3 : Moteur de Corrélation

```
Contexte: Module d'imputation - composant de calcul des corrélations entre colonnes.

Objectif: Identifier les meilleures variables prédictives pour chaque colonne à imputer.

Algorithmes à implémenter selon les types de variables:

1. NUMÉRIQUE vs NUMÉRIQUE:
   - Corrélation de Pearson (linéaire)
   - Corrélation de Spearman (monotone)
   - Distance de corrélation (non-linéaire)
   - Information mutuelle

2. CATÉGORIEL vs CATÉGORIEL:
   - V de Cramér
   - Coefficient de contingence
   - Information mutuelle

3. NUMÉRIQUE vs CATÉGORIEL:
   - Ratio de corrélation (Eta)
   - ANOVA F-statistic
   - Information mutuelle

4. SÉLECTION DES PRÉDICTEURS:
   - Retenir les variables avec corrélation > seuil configurable (défaut: 0.3)
   - Exclure les variables avec trop de valeurs manquantes (> 50%)
   - Limiter à N meilleurs prédicteurs (défaut: 5)
   - Éviter la multicolinéarité entre prédicteurs

Structure de sortie:
{
  "target_column": "DATE_NAISSANCE",
  "predictors": [
    {"column": "SEXE", "correlation_type": "eta", "score": 0.72, "rank": 1},
    {"column": "DIPLOME", "correlation_type": "eta", "score": 0.65, "rank": 2},
    {"column": "STATUT", "correlation_type": "eta", "score": 0.58, "rank": 3}
  ],
  "recommended_method": "mean_by_group",
  "grouping_columns": ["SEXE", "DIPLOME", "STATUT"]
}

Librairies: scipy.stats, sklearn.feature_selection, sklearn.preprocessing

Livrer:
- Classe CorrelationEngine avec toutes les méthodes
- Matrice de corrélation mixte (tous types)
- Visualisation heatmap (optionnel)
```

---

## PROMPT 4 : Moteur d'Imputation

```
Contexte: Module d'imputation - composant principal d'imputation des valeurs manquantes.

Objectif: Implémenter plusieurs stratégies d'imputation et sélectionner automatiquement la meilleure selon le contexte.

STRATÉGIES D'IMPUTATION À IMPLÉMENTER:

1. MÉTHODES SIMPLES (baseline):
   - Moyenne / Médiane / Mode
   - Valeur constante
   - Forward fill / Backward fill (séries temporelles)

2. MÉTHODES PAR GROUPE:
   - Moyenne/Médiane par groupe (colonnes corrélées)
   - Mode par groupe (catégoriel)
   - Imputation hiérarchique multi-niveaux (fallback progressif)

3. MÉTHODES BASÉES SUR DES MODÈLES:
   - KNN Imputer (k plus proches voisins)
   - Iterative Imputer (MICE - Multiple Imputation by Chained Equations)
   - Random Forest Imputer
   - Régression linéaire/logistique

4. MÉTHODES AVANCÉES:
   - MissForest (Random Forest itératif)
   - Imputation par matrice de faible rang (SVD)

LOGIQUE DE SÉLECTION AUTOMATIQUE:

```python
def select_imputation_method(column_analysis, correlations):
    """
    Règles de sélection:
    
    SI type = numérique continu:
        SI corrélations fortes (>0.5) avec autres colonnes:
            → KNN Imputer ou Iterative Imputer
        SI corrélations moyennes (0.3-0.5):
            → Moyenne par groupe
        SINON:
            → Médiane (robuste aux outliers)
    
    SI type = numérique discret:
        SI corrélations fortes:
            → KNN Imputer avec arrondi
        SINON:
            → Mode ou Médiane arrondie
    
    SI type = catégoriel:
        SI corrélations fortes:
            → Mode par groupe
        SINON:
            → Mode global ou "INCONNU"
    
    SI type = date:
        SI pattern temporel détecté:
            → Interpolation
        SI corrélations avec autres colonnes:
            → Calcul basé sur l'âge moyen du groupe
        SINON:
            → Médiane des dates
    
    SI % manquant > 40%:
        → Privilégier méthodes robustes (KNN, MICE)
        → Avertir l'utilisateur de la fiabilité réduite
    """
```

GESTION DES VALEURS ABERRANTES:
- Détecter avec IQR ou Z-score
- Option: corriger avant imputation ou traiter comme manquantes
- Configurable par l'utilisateur

VALIDATION CROISÉE:
- Masquer aléatoirement 10% des valeurs connues
- Imputer et mesurer l'erreur (RMSE, MAE, accuracy)
- Retourner score de confiance

Format de configuration:
{
  "column": "DATE_NAISSANCE",
  "method": "group_mean",
  "parameters": {
    "grouping_columns": ["SEXE", "DIPLOME", "STATUT"],
    "fallback_levels": [
      ["SEXE", "DIPLOME"],
      ["SEXE"],
      "global_median"
    ],
    "handle_outliers": "replace",
    "outlier_method": "iqr",
    "outlier_threshold": 1.5
  }
}

Livrer:
- Classe ImputationEngine
- Toutes les stratégies implémentées
- Sélecteur automatique
- Métriques de validation
```

---

## PROMPT 5 : Générateur de Rapport

```
Contexte: Module d'imputation - composant de génération de rapports.

Objectif: Générer un rapport complet avant/après imputation.

CONTENU DU RAPPORT:

1. RÉSUMÉ EXÉCUTIF:
   - Nombre total de lignes/colonnes
   - Nombre de valeurs manquantes avant/après
   - Nombre de valeurs corrigées par type
   - Score de qualité global (0-100)

2. ANALYSE PAR COLONNE:
   - Statistiques avant/après
   - Méthode d'imputation utilisée
   - Nombre de valeurs imputées
   - Confiance de l'imputation

3. DÉTAIL DES CORRECTIONS:
   - Liste des lignes modifiées
   - Valeur originale vs valeur imputée
   - Raison de la correction (manquant, aberrant, format)

4. VISUALISATIONS (optionnel):
   - Distribution avant/après (histogrammes)
   - Heatmap des valeurs manquantes
   - Matrice de corrélation

5. RECOMMANDATIONS:
   - Colonnes avec qualité insuffisante
   - Alertes sur imputations à faible confiance
   - Suggestions d'amélioration de la collecte

FORMATS DE SORTIE:
- JSON (pour affichage web)
- PDF (rapport téléchargeable)
- Excel (avec feuilles séparées: données, rapport, détails)

Structure JSON du rapport:
{
  "summary": {
    "total_rows": 14035,
    "total_columns": 8,
    "missing_before": 5860,
    "missing_after": 0,
    "corrections_count": 5860,
    "quality_score_before": 58.2,
    "quality_score_after": 100.0
  },
  "columns": [
    {
      "name": "DATE_NAISSANCE",
      "type": "numeric",
      "missing_before": 5791,
      "missing_after": 0,
      "imputation_method": "hierarchical_group_mean",
      "confidence": 0.87,
      "stats_before": {...},
      "stats_after": {...}
    }
  ],
  "corrections_detail": [
    {
      "row_index": 0,
      "column": "DATE_NAISSANCE",
      "original_value": null,
      "imputed_value": 1980,
      "reason": "missing",
      "method": "group_mean",
      "group_used": {"SEXE": 2, "DIPLOME": 3, "STATUT": 1}
    }
  ],
  "warnings": [
    "Colonne X: 45% de valeurs imputées - fiabilité réduite"
  ]
}

Livrer:
- Classe ReportGenerator
- Templates pour PDF (reportlab ou weasyprint)
- Export Excel multi-feuilles
```

---

## PROMPT 6 : API REST Complète

```
Contexte: Module d'imputation - définition de l'API REST.

Objectif: Créer une API REST complète pour le module d'imputation.

ENDPOINTS:

1. UPLOAD ET ANALYSE
-------------------
POST /api/v1/imputation/upload
- Input: fichier (multipart/form-data)
- Output: {file_id, preview, column_analysis}

GET /api/v1/imputation/{file_id}/analysis
- Output: analyse détaillée de toutes les colonnes

GET /api/v1/imputation/{file_id}/correlations
- Output: matrice de corrélation et prédicteurs recommandés

2. CONFIGURATION
----------------
GET /api/v1/imputation/{file_id}/recommendations
- Output: méthodes d'imputation recommandées par colonne

POST /api/v1/imputation/{file_id}/configure
- Input: configuration personnalisée par colonne
- Output: validation de la configuration

3. EXÉCUTION
------------
POST /api/v1/imputation/{file_id}/execute
- Input: {columns_to_impute, methods_override}
- Output: {job_id, status: "processing"}

GET /api/v1/imputation/{file_id}/status/{job_id}
- Output: {status, progress_percent, current_step}

4. RÉSULTATS
------------
GET /api/v1/imputation/{file_id}/report
- Output: rapport JSON complet

GET /api/v1/imputation/{file_id}/download
- Query params: format (xlsx, csv), include_report (bool)
- Output: fichier téléchargeable

GET /api/v1/imputation/{file_id}/download/report
- Query params: format (pdf, json)
- Output: rapport téléchargeable

5. GESTION
----------
DELETE /api/v1/imputation/{file_id}
- Supprime le fichier et les données associées

GET /api/v1/imputation/history
- Liste des fichiers traités par l'utilisateur

AUTHENTIFICATION:
- JWT Bearer token
- Rate limiting: 10 uploads/heure, 100 requêtes/minute

GESTION D'ERREURS:
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Le fichier doit être au format Excel ou CSV",
    "details": {...}
  }
}

Livrer:
- Code FastAPI complet
- Schémas Pydantic
- Middleware d'authentification
- Documentation OpenAPI/Swagger
```

---

## PROMPT 7 : Interface Utilisateur Frontend

```
Contexte: Module d'imputation - interface utilisateur React/Next.js.

Objectif: Créer une interface intuitive pour le workflow d'imputation.

ÉCRANS ET COMPOSANTS:

1. ÉCRAN UPLOAD (Step 1)
------------------------
- Zone drag & drop pour fichier
- Sélection de la feuille (si Excel multi-feuilles)
- Aperçu des 10 premières lignes
- Bouton "Analyser"

2. ÉCRAN ANALYSE (Step 2)
-------------------------
- Tableau récapitulatif des colonnes:
  | Colonne | Type | Manquants | Aberrants | Qualité | Action |
- Code couleur: vert (OK), orange (attention), rouge (problème)
- Détail expandable par colonne (statistiques, distribution)
- Heatmap des valeurs manquantes
- Matrice de corrélation interactive

3. ÉCRAN CONFIGURATION (Step 3)
-------------------------------
- Pour chaque colonne à imputer:
  - Méthode recommandée (pré-sélectionnée)
  - Options alternatives (dropdown)
  - Paramètres avancés (collapsible)
  - Aperçu de l'impact (estimation)
- Configuration globale:
  - Traitement des outliers (ignorer/corriger/supprimer)
  - Seuils personnalisés

4. ÉCRAN TRAITEMENT (Step 4)
----------------------------
- Barre de progression
- Log en temps réel des opérations
- Possibilité d'annuler

5. ÉCRAN RÉSULTATS (Step 5)
---------------------------
- Résumé des corrections effectuées
- Comparaison avant/après (side by side)
- Graphiques de distribution avant/après
- Score de qualité
- Boutons:
  - Télécharger fichier corrigé (Excel/CSV)
  - Télécharger rapport (PDF)
  - Voir détail des corrections

COMPOSANTS RÉUTILISABLES:
- DataQualityBadge: indicateur visuel de qualité
- ColumnStatsCard: carte de statistiques par colonne
- CorrelationHeatmap: visualisation des corrélations
- DistributionChart: histogramme/bar chart
- MissingValuesMatrix: visualisation des patterns de données manquantes
- ImputationMethodSelector: sélecteur de méthode avec aide contextuelle
- ProgressTracker: stepper de workflow

ÉTAT GLOBAL (Redux/Zustand):
- fileId
- analysisResults
- configuration
- imputationResults
- currentStep

Livrer:
- Composants React complets
- Hooks personnalisés pour l'API
- Styles (Tailwind CSS ou styled-components)
- Tests des composants principaux
```

---

# 4. ALGORITHMES D'IMPUTATION

## 4.1 Matrice de Décision

| Type de Donnée | % Manquant | Corrélation | Méthode Recommandée |
|----------------|------------|-------------|---------------------|
| Numérique | < 5% | Faible | Médiane |
| Numérique | < 5% | Forte | Régression |
| Numérique | 5-20% | Faible | Médiane |
| Numérique | 5-20% | Forte | KNN / MICE |
| Numérique | 20-40% | Toute | MICE / MissForest |
| Numérique | > 40% | Toute | MICE + Avertissement |
| Catégoriel | < 10% | Faible | Mode |
| Catégoriel | < 10% | Forte | Mode par groupe |
| Catégoriel | 10-30% | Forte | KNN catégoriel |
| Catégoriel | > 30% | Toute | Mode + "INCONNU" |
| Date | Toute | Avec âge | Calcul depuis âge moyen |
| Date | Toute | Temporel | Interpolation |

## 4.2 Pseudo-code de l'Imputation Hiérarchique

```python
def impute_hierarchical(df, target_col, group_cols, method='mean'):
    """
    Imputation hiérarchique avec fallback progressif.
    
    Exemple: group_cols = ['SEXE', 'DIPLOME', 'STATUT']
    
    Niveau 1: Moyenne par (SEXE, DIPLOME, STATUT)
    Niveau 2: Moyenne par (SEXE, DIPLOME)
    Niveau 3: Moyenne par (SEXE)
    Niveau 4: Moyenne globale
    """
    
    result = df[target_col].copy()
    missing_mask = result.isna()
    
    # Pré-calculer toutes les moyennes par groupe
    for level in range(len(group_cols), 0, -1):
        current_groups = group_cols[:level]
        group_stats = df.groupby(current_groups)[target_col].agg(method)
        
        # Appliquer aux valeurs encore manquantes
        for idx in result[missing_mask].index:
            group_key = tuple(df.loc[idx, current_groups])
            if group_key in group_stats.index:
                value = group_stats[group_key]
                if pd.notna(value):
                    result[idx] = value
                    missing_mask[idx] = False
    
    # Fallback final: moyenne globale
    global_stat = df[target_col].agg(method)
    result[missing_mask] = global_stat
    
    return result
```

---

# 5. MODÈLES DE DONNÉES

## 5.1 Schéma Base de Données

```sql
-- Table des fichiers uploadés
CREATE TABLE imputation_files (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    row_count INT,
    column_count INT,
    status VARCHAR(50), -- 'uploaded', 'analyzed', 'configured', 'processing', 'completed', 'error'
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table des analyses de colonnes
CREATE TABLE column_analyses (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL,
    column_name VARCHAR(255),
    column_index INT,
    detected_type VARCHAR(50),
    type_confidence FLOAT,
    missing_count INT,
    missing_percent FLOAT,
    outliers_count INT,
    statistics JSONB,
    quality_score FLOAT,
    FOREIGN KEY (file_id) REFERENCES imputation_files(id) ON DELETE CASCADE
);

-- Table des configurations d'imputation
CREATE TABLE imputation_configs (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL,
    column_name VARCHAR(255),
    method VARCHAR(100),
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (file_id) REFERENCES imputation_files(id) ON DELETE CASCADE
);

-- Table des résultats
CREATE TABLE imputation_results (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL,
    output_file_path VARCHAR(500),
    report_json JSONB,
    corrections_count INT,
    quality_score_before FLOAT,
    quality_score_after FLOAT,
    processing_time_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (file_id) REFERENCES imputation_files(id) ON DELETE CASCADE
);
```

## 5.2 Schémas Pydantic (Python)

```python
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from enum import Enum

class DataType(str, Enum):
    NUMERIC_CONTINUOUS = "numeric_continuous"
    NUMERIC_DISCRETE = "numeric_discrete"
    CATEGORICAL_NOMINAL = "categorical_nominal"
    CATEGORICAL_ORDINAL = "categorical_ordinal"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXT = "text"
    MIXED = "mixed"

class ImputationMethod(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    GROUP_MEAN = "group_mean"
    GROUP_MEDIAN = "group_median"
    GROUP_MODE = "group_mode"
    KNN = "knn"
    MICE = "mice"
    RANDOM_FOREST = "random_forest"
    INTERPOLATION = "interpolation"
    CONSTANT = "constant"

class ColumnStatistics(BaseModel):
    count: int
    missing: int
    missing_percent: float
    unique: Optional[int]
    mean: Optional[float]
    std: Optional[float]
    min: Optional[Any]
    max: Optional[Any]
    median: Optional[float]
    mode: Optional[Any]
    q1: Optional[float]
    q3: Optional[float]

class ColumnAnalysis(BaseModel):
    name: str
    index: int
    detected_type: DataType
    type_confidence: float
    statistics: ColumnStatistics
    outliers_count: int
    outliers_indices: List[int]
    format_issues: List[str]
    quality_score: float
    recommended_method: ImputationMethod
    recommended_predictors: List[str]

class ImputationConfig(BaseModel):
    column: str
    method: ImputationMethod
    grouping_columns: Optional[List[str]]
    fallback_levels: Optional[List[Any]]
    handle_outliers: str = "keep"  # keep, replace, remove
    constant_value: Optional[Any]
    knn_neighbors: int = 5

class CorrectionDetail(BaseModel):
    row_index: int
    column: str
    original_value: Optional[Any]
    imputed_value: Any
    reason: str  # missing, outlier, format_error
    method_used: str
    confidence: float

class ImputationReport(BaseModel):
    file_id: str
    summary: Dict[str, Any]
    columns: List[Dict[str, Any]]
    corrections: List[CorrectionDetail]
    warnings: List[str]
    processing_time_seconds: float
```

---

# 6. CHECKLIST DE DÉVELOPPEMENT

## Phase 1 : Backend Core (2-3 semaines)
- [ ] Service d'upload et parsing
- [ ] Service d'analyse des colonnes
- [ ] Moteur de corrélation
- [ ] Tests unitaires

## Phase 2 : Imputation Engine (2-3 semaines)
- [ ] Imputation simple (mean, median, mode)
- [ ] Imputation par groupe hiérarchique
- [ ] Imputation KNN
- [ ] Imputation MICE
- [ ] Sélecteur automatique
- [ ] Validation croisée

## Phase 3 : API et Export (1-2 semaines)
- [ ] Endpoints REST complets
- [ ] Générateur de rapport JSON
- [ ] Export Excel
- [ ] Export PDF
- [ ] Documentation Swagger

## Phase 4 : Frontend (2-3 semaines)
- [ ] Écran d'upload
- [ ] Écran d'analyse
- [ ] Écran de configuration
- [ ] Écran de résultats
- [ ] Composants de visualisation

## Phase 5 : Intégration et Tests (1-2 semaines)
- [ ] Tests d'intégration
- [ ] Tests de performance
- [ ] Documentation utilisateur
- [ ] Déploiement

---

# 7. EXEMPLES DE CODE DE RÉFÉRENCE

## 7.1 Détection Automatique du Type de Colonne

```python
import pandas as pd
import numpy as np
from scipy import stats

def detect_column_type(series: pd.Series) -> tuple[str, float]:
    """
    Détecte automatiquement le type d'une colonne.
    Retourne (type, confidence).
    """
    # Ignorer les valeurs manquantes pour l'analyse
    clean_series = series.dropna()
    
    if len(clean_series) == 0:
        return ("unknown", 0.0)
    
    # Test 1: Booléen
    unique_values = clean_series.unique()
    if len(unique_values) <= 2:
        bool_indicators = {True, False, 0, 1, '0', '1', 'true', 'false', 
                          'yes', 'no', 'oui', 'non', 'Y', 'N', 'O', 'N'}
        if set(str(v).lower() for v in unique_values).issubset(
            {str(b).lower() for b in bool_indicators}):
            return ("boolean", 0.95)
    
    # Test 2: Numérique
    numeric_series = pd.to_numeric(clean_series, errors='coerce')
    numeric_ratio = numeric_series.notna().sum() / len(clean_series)
    
    if numeric_ratio > 0.9:
        # Distinguer continu vs discret
        if numeric_series.dtype in ['int64', 'int32']:
            unique_ratio = len(numeric_series.unique()) / len(numeric_series)
            if unique_ratio < 0.05:  # Peu de valeurs uniques
                return ("numeric_discrete", numeric_ratio)
            return ("numeric_continuous", numeric_ratio)
        else:
            # Float - vérifier si ce sont des entiers déguisés
            is_integer = (numeric_series == numeric_series.astype(int)).all()
            if is_integer:
                return ("numeric_discrete", numeric_ratio * 0.9)
            return ("numeric_continuous", numeric_ratio)
    
    # Test 3: Date
    date_series = pd.to_datetime(clean_series, errors='coerce', infer_datetime_format=True)
    date_ratio = date_series.notna().sum() / len(clean_series)
    if date_ratio > 0.8:
        return ("datetime", date_ratio)
    
    # Test 4: Catégoriel
    unique_ratio = len(unique_values) / len(clean_series)
    if unique_ratio < 0.5:  # Moins de 50% de valeurs uniques
        # Vérifier s'il y a un ordre implicite
        if _has_ordinal_pattern(unique_values):
            return ("categorical_ordinal", 0.8)
        return ("categorical_nominal", 0.85)
    
    # Par défaut: texte libre
    return ("text", 0.7)

def _has_ordinal_pattern(values) -> bool:
    """Détecte si les valeurs ont un pattern ordinal."""
    ordinal_patterns = [
        ['faible', 'moyen', 'fort'],
        ['low', 'medium', 'high'],
        ['petit', 'moyen', 'grand'],
        ['1er', '2e', '3e'],
        ['primaire', 'secondaire', 'supérieur']
    ]
    values_lower = [str(v).lower() for v in values]
    for pattern in ordinal_patterns:
        if any(p in values_lower for p in pattern):
            return True
    return False
```

## 7.2 Calcul de Corrélation Mixte

```python
from scipy.stats import pearsonr, spearmanr, chi2_contingency
import numpy as np

def correlation_ratio(categories, measurements):
    """
    Calcule le ratio de corrélation (Eta) entre une variable 
    catégorielle et une variable numérique.
    """
    categories = np.array(categories)
    measurements = np.array(measurements)
    
    # Supprimer les NaN
    mask = ~(pd.isna(categories) | pd.isna(measurements))
    categories = categories[mask]
    measurements = measurements[mask]
    
    # Calculer les moyennes par catégorie
    cat_unique = np.unique(categories)
    cat_means = {cat: measurements[categories == cat].mean() 
                 for cat in cat_unique}
    
    # Variance inter-groupe
    grand_mean = measurements.mean()
    ss_between = sum(
        len(measurements[categories == cat]) * (cat_means[cat] - grand_mean)**2 
        for cat in cat_unique
    )
    
    # Variance totale
    ss_total = ((measurements - grand_mean)**2).sum()
    
    if ss_total == 0:
        return 0
    
    return np.sqrt(ss_between / ss_total)

def cramers_v(x, y):
    """
    Calcule le V de Cramér entre deux variables catégorielles.
    """
    confusion_matrix = pd.crosstab(x, y)
    chi2 = chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    min_dim = min(confusion_matrix.shape) - 1
    
    if min_dim == 0 or n == 0:
        return 0
    
    return np.sqrt(chi2 / (n * min_dim))

def compute_mixed_correlation_matrix(df: pd.DataFrame, 
                                      column_types: dict) -> pd.DataFrame:
    """
    Calcule une matrice de corrélation pour tous types de variables.
    """
    columns = df.columns
    n = len(columns)
    corr_matrix = pd.DataFrame(index=columns, columns=columns, dtype=float)
    
    for i, col1 in enumerate(columns):
        for j, col2 in enumerate(columns):
            if i == j:
                corr_matrix.loc[col1, col2] = 1.0
            elif j > i:
                type1 = column_types[col1]
                type2 = column_types[col2]
                
                corr = _compute_pairwise_correlation(
                    df[col1], df[col2], type1, type2
                )
                
                corr_matrix.loc[col1, col2] = corr
                corr_matrix.loc[col2, col1] = corr
    
    return corr_matrix

def _compute_pairwise_correlation(series1, series2, type1, type2):
    """Calcule la corrélation appropriée selon les types."""
    
    # Numérique vs Numérique
    if 'numeric' in type1 and 'numeric' in type2:
        return spearmanr(series1, series2, nan_policy='omit')[0]
    
    # Catégoriel vs Catégoriel
    if 'categorical' in type1 and 'categorical' in type2:
        return cramers_v(series1, series2)
    
    # Numérique vs Catégoriel
    if 'numeric' in type1 and 'categorical' in type2:
        return correlation_ratio(series2, series1)
    if 'categorical' in type1 and 'numeric' in type2:
        return correlation_ratio(series1, series2)
    
    # Autres cas: retourner 0 ou utiliser une méthode générique
    return 0
```

---

# 8. RESSOURCES ET RÉFÉRENCES

## Librairies Python Recommandées
- **pandas**: Manipulation de données
- **numpy**: Calculs numériques
- **scikit-learn**: KNNImputer, IterativeImputer
- **scipy**: Tests statistiques, corrélations
- **missingno**: Visualisation des données manquantes
- **fancyimpute**: Algorithmes avancés (MICE, MatrixFactorization)

## Documentation
- [Scikit-learn Imputation](https://scikit-learn.org/stable/modules/impute.html)
- [Pandas Missing Data](https://pandas.pydata.org/docs/user_guide/missing_data.html)
- [MICE Algorithm Paper](https://www.jstatsoft.org/article/view/v045i03)

---

*Document généré pour le développement du Module d'Imputation Automatique - MESRIT Niger*
