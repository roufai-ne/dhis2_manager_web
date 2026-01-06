"""
Moteur de calcul des corrélations entre colonnes
Identifie les meilleures variables prédictives pour l'imputation
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr, chi2_contingency
from typing import Dict, List, Tuple, Any
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_selection import mutual_info_regression, mutual_info_classif


class CorrelationEngine:
    """Calcule les corrélations entre colonnes de différents types"""

    def __init__(self, min_correlation: float = 0.3, max_predictors: int = 5):
        """
        Args:
            min_correlation: Seuil minimum de corrélation pour sélection
            max_predictors: Nombre maximum de prédicteurs à retenir
        """
        self.min_correlation = min_correlation
        self.max_predictors = max_predictors

    def compute_correlation_matrix(
        self,
        df: pd.DataFrame,
        column_types: Dict[str, str]
    ) -> pd.DataFrame:
        """
        Calcule une matrice de corrélation mixte pour tous types de variables.

        Args:
            df: DataFrame à analyser
            column_types: Dictionnaire {colonne: type_détecté}

        Returns:
            DataFrame avec matrice de corrélation
        """
        columns = df.columns
        n = len(columns)
        corr_matrix = pd.DataFrame(
            index=columns,
            columns=columns,
            dtype=float
        )

        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i == j:
                    corr_matrix.loc[col1, col2] = 1.0
                elif j > i:
                    type1 = column_types.get(col1, 'unknown')
                    type2 = column_types.get(col2, 'unknown')

                    corr = self._compute_pairwise_correlation(
                        df[col1], df[col2], type1, type2
                    )

                    corr_matrix.loc[col1, col2] = corr
                    corr_matrix.loc[col2, col1] = corr

        return corr_matrix

    def find_best_predictors(
        self,
        df: pd.DataFrame,
        target_column: str,
        column_types: Dict[str, str],
        exclude_columns: List[str] = None
    ) -> Dict[str, Any]:
        """
        Trouve les meilleures variables prédictives pour une colonne cible.

        Args:
            df: DataFrame
            target_column: Colonne à imputer
            column_types: Types des colonnes
            exclude_columns: Colonnes à exclure de l'analyse

        Returns:
            Dictionnaire avec prédicteurs recommandés et méthode d'imputation
        """
        if exclude_columns is None:
            exclude_columns = []

        target_type = column_types.get(target_column, 'unknown')
        predictors = []

        # Calculer les corrélations avec toutes les autres colonnes
        for col in df.columns:
            if col == target_column or col in exclude_columns:
                continue

            # Exclure les colonnes avec trop de valeurs manquantes
            if df[col].isna().sum() / len(df) > 0.5:
                continue

            col_type = column_types.get(col, 'unknown')
            correlation = self._compute_pairwise_correlation(
                df[target_column], df[col], target_type, col_type
            )

            if abs(correlation) >= self.min_correlation:
                predictors.append({
                    'column': col,
                    'correlation_score': abs(correlation),
                    'correlation_type': self._get_correlation_type(target_type, col_type),
                    'column_type': col_type
                })

        # Trier par score de corrélation décroissant
        predictors.sort(key=lambda x: x['correlation_score'], reverse=True)

        # Limiter au nombre maximum de prédicteurs
        predictors = predictors[:self.max_predictors]

        # Ajouter le rang
        for i, pred in enumerate(predictors, 1):
            pred['rank'] = i

        # Déterminer la méthode d'imputation recommandée
        recommended_method = self._recommend_imputation_method(
            target_type, predictors
        )

        # Colonnes de regroupement pour imputation par groupe
        grouping_columns = [p['column'] for p in predictors if 'categorical' in p['column_type']]

        return {
            'target_column': target_column,
            'target_type': target_type,
            'predictors': predictors,
            'recommended_method': recommended_method,
            'grouping_columns': grouping_columns[:3],  # Max 3 pour éviter trop de groupes
            'has_strong_correlations': len(predictors) > 0 and predictors[0]['correlation_score'] > 0.5
        }

    def _compute_pairwise_correlation(
        self,
        series1: pd.Series,
        series2: pd.Series,
        type1: str,
        type2: str
    ) -> float:
        """Calcule la corrélation appropriée selon les types de variables"""
        # Supprimer les valeurs manquantes
        mask = ~(series1.isna() | series2.isna())
        s1 = series1[mask]
        s2 = series2[mask]

        if len(s1) < 3:
            return 0.0

        try:
            # Numérique vs Numérique
            if 'numeric' in type1 and 'numeric' in type2:
                return self._numeric_numeric_correlation(s1, s2)

            # Catégoriel vs Catégoriel
            if 'categorical' in type1 and 'categorical' in type2:
                return self._categorical_categorical_correlation(s1, s2)

            # Numérique vs Catégoriel
            if 'numeric' in type1 and 'categorical' in type2:
                return self._categorical_numeric_correlation(s2, s1)
            if 'categorical' in type1 and 'numeric' in type2:
                return self._categorical_numeric_correlation(s1, s2)

            # Booléen traité comme catégoriel
            if 'boolean' in type1 or 'boolean' in type2:
                if 'numeric' in type1 or 'numeric' in type2:
                    return self._categorical_numeric_correlation(
                        s1 if 'boolean' in type1 else s2,
                        s2 if 'boolean' in type1 else s1
                    )
                else:
                    return self._categorical_categorical_correlation(s1, s2)

            # Autres cas
            return 0.0

        except Exception as e:
            # En cas d'erreur, retourner 0
            return 0.0

    def _numeric_numeric_correlation(self, s1: pd.Series, s2: pd.Series) -> float:
        """Corrélation de Spearman (robuste aux outliers)"""
        s1_num = pd.to_numeric(s1, errors='coerce')
        s2_num = pd.to_numeric(s2, errors='coerce')

        mask = ~(s1_num.isna() | s2_num.isna())
        s1_clean = s1_num[mask]
        s2_clean = s2_num[mask]

        if len(s1_clean) < 3:
            return 0.0

        corr, _ = spearmanr(s1_clean, s2_clean)
        return corr if not np.isnan(corr) else 0.0

    def _categorical_categorical_correlation(self, s1: pd.Series, s2: pd.Series) -> float:
        """V de Cramér pour variables catégorielles"""
        return self._cramers_v(s1, s2)

    def _categorical_numeric_correlation(
        self,
        categorical: pd.Series,
        numeric: pd.Series
    ) -> float:
        """Ratio de corrélation (Eta) pour catégoriel vs numérique"""
        return self._correlation_ratio(categorical, numeric)

    def _cramers_v(self, x: pd.Series, y: pd.Series) -> float:
        """
        Calcule le V de Cramér entre deux variables catégorielles.
        Valeur entre 0 (pas d'association) et 1 (association parfaite)
        """
        try:
            confusion_matrix = pd.crosstab(x, y)
            chi2, _, _, _ = chi2_contingency(confusion_matrix)
            n = confusion_matrix.sum().sum()
            min_dim = min(confusion_matrix.shape[0], confusion_matrix.shape[1]) - 1

            if min_dim == 0 or n == 0:
                return 0.0

            v = np.sqrt(chi2 / (n * min_dim))
            return min(v, 1.0)  # Limiter à 1.0

        except Exception:
            return 0.0

    def _correlation_ratio(self, categories: pd.Series, measurements: pd.Series) -> float:
        """
        Calcule le ratio de corrélation (Eta) entre une variable
        catégorielle et une variable numérique.
        Valeur entre 0 et 1.
        """
        try:
            # Convertir en numérique
            measurements_num = pd.to_numeric(measurements, errors='coerce')

            # Supprimer les NaN
            mask = ~(pd.isna(categories) | pd.isna(measurements_num))
            cat = categories[mask]
            meas = measurements_num[mask]

            if len(cat) < 3:
                return 0.0

            # Calculer les moyennes par catégorie
            cat_unique = cat.unique()
            cat_means = {}
            for c in cat_unique:
                cat_means[c] = meas[cat == c].mean()

            # Variance inter-groupe
            grand_mean = meas.mean()
            ss_between = sum(
                len(meas[cat == c]) * (cat_means[c] - grand_mean) ** 2
                for c in cat_unique
            )

            # Variance totale
            ss_total = ((meas - grand_mean) ** 2).sum()

            if ss_total == 0:
                return 0.0

            eta = np.sqrt(ss_between / ss_total)
            return min(eta, 1.0)  # Limiter à 1.0

        except Exception:
            return 0.0

    def _get_correlation_type(self, type1: str, type2: str) -> str:
        """Retourne le type de corrélation utilisé"""
        if 'numeric' in type1 and 'numeric' in type2:
            return 'spearman'
        elif 'categorical' in type1 and 'categorical' in type2:
            return 'cramers_v'
        elif ('numeric' in type1 and 'categorical' in type2) or \
             ('categorical' in type1 and 'numeric' in type2):
            return 'eta'
        else:
            return 'other'

    def _recommend_imputation_method(
        self,
        target_type: str,
        predictors: List[Dict]
    ) -> str:
        """Recommande une méthode d'imputation basée sur le type et les corrélations"""
        has_strong_correlation = (
            len(predictors) > 0 and predictors[0]['correlation_score'] > 0.5
        )
        has_medium_correlation = (
            len(predictors) > 0 and predictors[0]['correlation_score'] > 0.3
        )

        if 'numeric' in target_type:
            if has_strong_correlation:
                return 'knn' if len(predictors) >= 2 else 'group_mean'
            elif has_medium_correlation:
                return 'group_mean'
            else:
                return 'median'

        elif 'categorical' in target_type:
            if has_medium_correlation:
                return 'group_mode'
            else:
                return 'mode'

        elif target_type == 'datetime':
            if has_medium_correlation:
                return 'group_median_date'
            else:
                return 'median_date'

        else:
            return 'constant'
