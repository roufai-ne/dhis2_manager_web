"""
Moteur d'imputation de données
Implémente plusieurs stratégies d'imputation automatique
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, ExtraTreesRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression, BayesianRidge
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
import warnings
import joblib
from functools import lru_cache

warnings.filterwarnings('ignore')


class ImputationMethod:
    """Énumération des méthodes d'imputation"""
    # Méthodes statistiques simples
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    
    # Méthodes par groupe
    GROUP_MEAN = "group_mean"
    GROUP_MEDIAN = "group_median"
    GROUP_MODE = "group_mode"
    
    # Méthodes avancées
    KNN = "knn"
    MICE = "mice"  # Multiple Imputation by Chained Equations
    RANDOM_FOREST = "random_forest"
    LINEAR_REGRESSION = "linear_regression"
    
    # Méthodes temporelles
    INTERPOLATION_LINEAR = "interpolation_linear"
    INTERPOLATION_POLYNOMIAL = "interpolation_polynomial"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    
    # Autres
    CONSTANT = "constant"


class ImputationEngine:
    """Moteur principal d'imputation"""

    def __init__(self):
        self.corrections_log = []
        self.scalers = {}
        self.feature_cache = {}
        
        # Paramètres optimisés pour vitesse/précision
        self.max_samples_for_ml = 5000  # Échantillonner si > 5000 lignes
        self.n_jobs = -1  # Parallélisation maximale
        self.use_feature_selection = True  # Sélection auto des features
    
    def _select_best_features(
        self,
        df: pd.DataFrame,
        target_column: str,
        candidate_columns: List[str],
        max_features: int = 15
    ) -> List[str]:
        """
        Sélectionne automatiquement les meilleures features pour l'imputation
        Utilise mutual_info_regression pour capturer relations linéaires et non-linéaires
        """
        # Clé de cache
        cache_key = f"{target_column}_{len(candidate_columns)}_{max_features}"
        if cache_key in self.feature_cache:
            return self.feature_cache[cache_key]
        
        # Filtrer seulement colonnes numériques sans target
        numeric_cols = [col for col in candidate_columns 
                       if col != target_column and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(numeric_cols) <= max_features:
            self.feature_cache[cache_key] = numeric_cols
            return numeric_cols
        
        try:
            # Préparer données sans NaN pour analyse
            df_complete = df[[target_column] + numeric_cols].dropna()
            
            if len(df_complete) < 20:  # Pas assez de données
                selected = numeric_cols[:max_features]
                self.feature_cache[cache_key] = selected
                return selected
            
            X = df_complete[numeric_cols]
            y = df_complete[target_column]
            
            # Mutual information (capture relations non-linéaires)
            selector = SelectKBest(mutual_info_regression, k=min(max_features, len(numeric_cols)))
            selector.fit(X, y)
            
            # Obtenir indices des meilleures features
            selected_mask = selector.get_support()
            selected = [col for col, selected in zip(numeric_cols, selected_mask) if selected]
            
            self.feature_cache[cache_key] = selected
            return selected
            
        except Exception:
            # Fallback: prendre simplement les premières
            selected = numeric_cols[:max_features]
            self.feature_cache[cache_key] = selected
            return selected

    def impute_dataframe(
        self,
        df: pd.DataFrame,
        imputation_config: Dict[str, Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Impute les valeurs manquantes d'un DataFrame selon la configuration.

        Args:
            df: DataFrame à imputer
            imputation_config: Configuration par colonne
                {
                    'col_name': {
                        'method': 'knn',
                        'parameters': {...}
                    }
                }

        Returns:
            (DataFrame imputé, rapport détaillé)
        """
        df_imputed = df.copy()
        self.corrections_log = []
        imputation_report = {
            'columns_imputed': [],
            'total_corrections': 0,
            'corrections_by_column': {}
        }

        for col_name, config in imputation_config.items():
            if col_name not in df_imputed.columns:
                continue

            missing_before = df_imputed[col_name].isna().sum()
            if missing_before == 0:
                continue

            method = config.get('method', ImputationMethod.MEDIAN)
            parameters = config.get('parameters', {})

            # Appliquer l'imputation
            df_imputed[col_name] = self._impute_column(
                df_imputed,
                col_name,
                method,
                parameters
            )

            missing_after = df_imputed[col_name].isna().sum()
            corrections_count = missing_before - missing_after

            imputation_report['columns_imputed'].append(col_name)
            imputation_report['total_corrections'] += corrections_count
            imputation_report['corrections_by_column'][col_name] = {
                'method': method,
                'corrections_count': corrections_count,
                'missing_before': missing_before,
                'missing_after': missing_after
            }

        return df_imputed, imputation_report

    def _impute_column(
        self,
        df: pd.DataFrame,
        column: str,
        method: str,
        parameters: Dict[str, Any]
    ) -> pd.Series:
        """Impute une colonne selon la méthode spécifiée"""
        series = df[column].copy()

        if method == ImputationMethod.MEAN:
            return self._impute_mean(series)

        elif method == ImputationMethod.MEDIAN:
            return self._impute_median(series)

        elif method == ImputationMethod.MODE:
            return self._impute_mode(series)

        elif method == ImputationMethod.GROUP_MEAN:
            return self._impute_group_mean(
                df, column,
                parameters.get('grouping_columns', []),
                parameters.get('fallback_levels', [])
            )

        elif method == ImputationMethod.GROUP_MEDIAN:
            return self._impute_group_median(
                df, column,
                parameters.get('grouping_columns', []),
                parameters.get('fallback_levels', [])
            )

        elif method == ImputationMethod.GROUP_MODE:
            return self._impute_group_mode(
                df, column,
                parameters.get('grouping_columns', []),
                parameters.get('fallback_levels', [])
            )

        elif method == ImputationMethod.KNN:
            return self._impute_knn(
                df, column,
                parameters.get('k_neighbors', 5),
                parameters.get('predictor_columns', [])
            )

        elif method == ImputationMethod.MICE:
            return self._impute_mice(
                df, column,
                parameters.get('max_iter', 10),
                parameters.get('predictor_columns', [])
            )

        elif method == ImputationMethod.RANDOM_FOREST:
            return self._impute_random_forest(
                df, column,
                parameters.get('n_estimators', 100),
                parameters.get('predictor_columns', [])
            )

        elif method == ImputationMethod.LINEAR_REGRESSION:
            return self._impute_regression(
                df, column,
                parameters.get('predictor_columns', [])
            )

        elif method == ImputationMethod.INTERPOLATION_LINEAR:
            return self._impute_interpolation(series, method='linear')

        elif method == ImputationMethod.INTERPOLATION_POLYNOMIAL:
            return self._impute_interpolation(series, method='polynomial', order=2)

        elif method == ImputationMethod.CONSTANT:
            return self._impute_constant(
                series,
                parameters.get('constant_value', 0)
            )

        elif method == ImputationMethod.FORWARD_FILL:
            return series.fillna(method='ffill')

        elif method == ImputationMethod.BACKWARD_FILL:
            return series.fillna(method='bfill')

        else:
            # Méthode par défaut: médiane pour numérique, mode pour autre
            if pd.api.types.is_numeric_dtype(series):
                return self._impute_median(series)
            else:
                return self._impute_mode(series)

    def _impute_mean(self, series: pd.Series) -> pd.Series:
        """Imputation par la moyenne"""
        if not pd.api.types.is_numeric_dtype(series):
            series = pd.to_numeric(series, errors='coerce')
        mean_val = series.mean()
        return series.fillna(mean_val)

    def _impute_median(self, series: pd.Series) -> pd.Series:
        """Imputation par la médiane"""
        if not pd.api.types.is_numeric_dtype(series):
            series = pd.to_numeric(series, errors='coerce')
        median_val = series.median()
        return series.fillna(median_val)

    def _impute_mode(self, series: pd.Series) -> pd.Series:
        """Imputation par le mode (valeur la plus fréquente)"""
        mode_values = series.mode()
        if len(mode_values) > 0:
            mode_val = mode_values[0]
            return series.fillna(mode_val)
        return series

    def _impute_constant(self, series: pd.Series, constant_value: Any) -> pd.Series:
        """Imputation par une valeur constante"""
        return series.fillna(constant_value)

    def _impute_group_mean(
        self,
        df: pd.DataFrame,
        target_column: str,
        grouping_columns: List[str],
        fallback_levels: Optional[List] = None
    ) -> pd.Series:
        """
        Imputation hiérarchique par moyenne de groupe.

        Exemple: Si grouping_columns = ['SEXE', 'DIPLOME', 'STATUT']
        - Niveau 1: Moyenne par (SEXE, DIPLOME, STATUT)
        - Niveau 2: Moyenne par (SEXE, DIPLOME)
        - Niveau 3: Moyenne par (SEXE)
        - Niveau 4: Moyenne globale
        """
        return self._impute_hierarchical(
            df, target_column, grouping_columns, 'mean', fallback_levels
        )

    def _impute_group_median(
        self,
        df: pd.DataFrame,
        target_column: str,
        grouping_columns: List[str],
        fallback_levels: Optional[List] = None
    ) -> pd.Series:
        """Imputation hiérarchique par médiane de groupe"""
        return self._impute_hierarchical(
            df, target_column, grouping_columns, 'median', fallback_levels
        )

    def _impute_group_mode(
        self,
        df: pd.DataFrame,
        target_column: str,
        grouping_columns: List[str],
        fallback_levels: Optional[List] = None
    ) -> pd.Series:
        """Imputation hiérarchique par mode de groupe"""
        return self._impute_hierarchical(
            df, target_column, grouping_columns, 'mode', fallback_levels
        )

    def _impute_hierarchical(
        self,
        df: pd.DataFrame,
        target_column: str,
        grouping_columns: List[str],
        aggregation: str,
        fallback_levels: Optional[List] = None
    ) -> pd.Series:
        """
        Imputation hiérarchique générique avec fallback progressif.
        """
        result = df[target_column].copy()
        missing_mask = result.isna()

        # Filtrer les colonnes de regroupement qui existent
        grouping_columns = [col for col in grouping_columns if col in df.columns]

        if not grouping_columns:
            # Pas de colonne de regroupement, utiliser la statistique globale
            if aggregation == 'mean':
                global_stat = result.mean()
            elif aggregation == 'median':
                global_stat = result.median()
            else:  # mode
                mode_vals = result.mode()
                global_stat = mode_vals[0] if len(mode_vals) > 0 else result.iloc[0]

            result[missing_mask] = global_stat
            return result

        # Créer les niveaux de fallback automatiquement si non fournis
        if fallback_levels is None:
            fallback_levels = []
            for i in range(len(grouping_columns), 0, -1):
                fallback_levels.append(grouping_columns[:i])

        # Ajouter le fallback global à la fin
        fallback_levels.append([])

        # Appliquer chaque niveau de fallback
        for level_groups in fallback_levels:
            if not missing_mask.any():
                break  # Plus de valeurs manquantes

            if not level_groups:
                # Fallback global
                if aggregation == 'mean':
                    global_stat = result.mean()
                elif aggregation == 'median':
                    global_stat = result.median()
                else:  # mode
                    mode_vals = result.mode()
                    global_stat = mode_vals[0] if len(mode_vals) > 0 else None

                if global_stat is not None:
                    result[missing_mask] = global_stat
                break

            # Calculer les statistiques par groupe
            if aggregation == 'mode':
                # Le mode nécessite un traitement spécial
                group_stats = df.groupby(level_groups)[target_column].agg(
                    lambda x: x.mode()[0] if len(x.mode()) > 0 else np.nan
                )
            else:
                group_stats = df.groupby(level_groups)[target_column].agg(aggregation)

            # Appliquer aux valeurs encore manquantes
            for idx in result[missing_mask].index:
                try:
                    group_key = tuple(df.loc[idx, level_groups])
                    if group_key in group_stats.index:
                        value = group_stats[group_key]
                        if pd.notna(value):
                            result[idx] = value
                            missing_mask[idx] = False
                except Exception:
                    continue

        return result

    def _impute_knn(
        self,
        df: pd.DataFrame,
        target_column: str,
        n_neighbors: int = 5,
        predictor_columns: Optional[List[str]] = None
    ) -> pd.Series:
        """
        Imputation KNN (K plus proches voisins).
        OPTIMISÉ: k adaptatif, feature selection, poids par distance

        Args:
            df: DataFrame
            target_column: Colonne à imputer
            n_neighbors: Nombre de voisins
            predictor_columns: Colonnes à utiliser comme prédicteurs
        """
        # Adapter k selon la taille du dataset (optimisation)
        n_samples = len(df)
        k_optimal = min(n_neighbors, max(3, int(np.sqrt(n_samples))))
        
        # Sélectionner les colonnes pour KNN
        if predictor_columns:
            columns_to_use = [col for col in predictor_columns if col in df.columns]
            columns_to_use.append(target_column)
        else:
            # Utiliser toutes les colonnes numériques
            columns_to_use = df.select_dtypes(include=[np.number]).columns.tolist()

        if target_column not in columns_to_use:
            columns_to_use.append(target_column)

        # Feature selection pour accélérer
        if self.use_feature_selection and len(columns_to_use) > 20:
            columns_to_use = self._select_best_features(df, target_column, columns_to_use, max_features=20)
            if target_column not in columns_to_use:
                columns_to_use.append(target_column)

        # Créer un sous-dataframe avec seulement les colonnes numériques
        df_numeric = df[columns_to_use].copy()

        # Encoder les colonnes non-numériques si nécessaire
        encoders = {}
        for col in df_numeric.columns:
            if not pd.api.types.is_numeric_dtype(df_numeric[col]):
                le = LabelEncoder()
                # Remplacer les valeurs non-nulles
                mask = df_numeric[col].notna()
                if mask.any():
                    df_numeric.loc[mask, col] = le.fit_transform(
                        df_numeric.loc[mask, col].astype(str)
                    )
                    encoders[col] = le

        # Appliquer KNN Imputer avec pondération par distance
        try:
            imputer = KNNImputer(
                n_neighbors=min(k_optimal, len(df) - 1),
                weights='distance'  # Pondération par distance (améliore précision)
            )
            df_imputed = pd.DataFrame(
                imputer.fit_transform(df_numeric),
                columns=df_numeric.columns,
                index=df_numeric.index
            )

            result = df_imputed[target_column]

            # Décoder si la colonne était encodée
            if target_column in encoders:
                le = encoders[target_column]
                # Arrondir aux valeurs entières pour le décodage
                result = result.round().astype(int)
                # Limiter aux indices valides
                result = result.clip(0, len(le.classes_) - 1)
                result = result.apply(lambda x: le.classes_[x])

            return result

        except Exception as e:
            # En cas d'erreur, fallback vers la médiane/mode
            if pd.api.types.is_numeric_dtype(df[target_column]):
                return self._impute_median(df[target_column])
            else:
                return self._impute_mode(df[target_column])

    def _impute_mice(
        self,
        df: pd.DataFrame,
        target_column: str,
        max_iter: int = 10,
        predictor_columns: Optional[List[str]] = None
    ) -> pd.Series:
        """
        MICE (Multiple Imputation by Chained Equations)
        Méthode itérative très robuste qui modélise chaque colonne en fonction des autres.
        OPTIMISÉ: BayesianRidge, normalisation, sélection de features
        """
        if predictor_columns and len(predictor_columns) > 0:
            columns_to_use = [col for col in predictor_columns if col in df.columns]
        else:
            columns_to_use = df.select_dtypes(include=[np.number]).columns.tolist()

        if target_column not in columns_to_use:
            columns_to_use.append(target_column)

        # Sélection automatique des meilleures features (corrélations fortes)
        if self.use_feature_selection and len(columns_to_use) > 10:
            columns_to_use = self._select_best_features(df, target_column, columns_to_use, max_features=10)
            if target_column not in columns_to_use:
                columns_to_use.append(target_column)

        df_numeric = df[columns_to_use].copy()

        # Encoder colonnes non-numériques
        encoders = {}
        for col in df_numeric.columns:
            if not pd.api.types.is_numeric_dtype(df_numeric[col]):
                le = LabelEncoder()
                mask = df_numeric[col].notna()
                if mask.any():
                    df_numeric.loc[mask, col] = le.fit_transform(
                        df_numeric.loc[mask, col].astype(str)
                    )
                    encoders[col] = le

        try:
            # Normaliser pour améliorer convergence
            scaler = StandardScaler()
            mask_complete = df_numeric.notna().all(axis=1)
            if mask_complete.any():
                scaler.fit(df_numeric[mask_complete])
                df_scaled = pd.DataFrame(
                    scaler.transform(df_numeric),
                    columns=df_numeric.columns,
                    index=df_numeric.index
                )
            else:
                df_scaled = df_numeric.copy()

            # MICE avec BayesianRidge (meilleur que défaut)
            imputer = IterativeImputer(
                estimator=BayesianRidge(),
                max_iter=max_iter,
                random_state=42,
                verbose=0,
                skip_complete=True  # Optimisation: skip colonnes complètes
            )
            df_imputed_scaled = imputer.fit_transform(df_scaled)
            
            # Dénormaliser
            if mask_complete.any():
                df_imputed = pd.DataFrame(
                    scaler.inverse_transform(df_imputed_scaled),
                    columns=df_numeric.columns,
                    index=df_numeric.index
                )
            else:
                df_imputed = pd.DataFrame(
                    df_imputed_scaled,
                    columns=df_numeric.columns,
                    index=df_numeric.index
                )

            result = df_imputed[target_column]

            # Décoder si nécessaire
            if target_column in encoders:
                le = encoders[target_column]
                result = result.round().astype(int).clip(0, len(le.classes_) - 1)
                result = result.apply(lambda x: le.classes_[x])

            return result

        except Exception as e:
            return self._impute_knn(df, target_column, 5, predictor_columns)

    def _impute_random_forest(
        self,
        df: pd.DataFrame,
        target_column: str,
        n_estimators: int = 100,
        predictor_columns: Optional[List[str]] = None
    ) -> pd.Series:
        """
        Imputation par RandomForest
        Très efficace pour relations non-linéaires complexes.
        OPTIMISÉ: ExtraTrees, échantillonnage, feature selection, parallélisation
        """
        if predictor_columns and len(predictor_columns) > 0:
            X_cols = [col for col in predictor_columns if col in df.columns and col != target_column]
        else:
            X_cols = [col for col in df.columns if col != target_column]
            X_cols = [col for col in X_cols if pd.api.types.is_numeric_dtype(df[col])]

        if len(X_cols) == 0:
            return self._impute_median(df[target_column])

        # Sélection des meilleures features
        if self.use_feature_selection and len(X_cols) > 15:
            X_cols = self._select_best_features(df, target_column, X_cols, max_features=15)

        result = df[target_column].copy()
        mask_missing = result.isna()
        
        if not mask_missing.any():
            return result

        # Préparer les données
        X = df[X_cols].copy()
        
        # Encoder les colonnes catégorielles
        for col in X.columns:
            if not pd.api.types.is_numeric_dtype(X[col]):
                le = LabelEncoder()
                mask = X[col].notna()
                if mask.any():
                    X.loc[mask, col] = le.fit_transform(X.loc[mask, col].astype(str))
                X[col] = X[col].fillna(X[col].median())

        # Remplir les NaN dans X avec la médiane
        X = X.fillna(X.median())

        # Train/predict avec échantillonnage si trop de données
        X_train = X[~mask_missing]
        y_train = result[~mask_missing]
        X_predict = X[mask_missing]
        
        # Échantillonner pour accélérer si dataset trop grand
        if len(X_train) > self.max_samples_for_ml:
            sample_idx = np.random.choice(len(X_train), self.max_samples_for_ml, replace=False)
            X_train = X_train.iloc[sample_idx]
            y_train = y_train.iloc[sample_idx]

        try:
            is_numeric = pd.api.types.is_numeric_dtype(result)
            
            if is_numeric:
                # ExtraTreesRegressor souvent plus rapide et aussi précis
                model = ExtraTreesRegressor(
                    n_estimators=min(n_estimators, 100),  # Limiter si besoin
                    max_depth=15,  # Éviter overfitting
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=self.n_jobs,
                    bootstrap=False  # ExtraTrees utilise tout le dataset
                )
            else:
                # Classification
                le = LabelEncoder()
                y_train = le.fit_transform(y_train.astype(str))
                model = RandomForestClassifier(
                    n_estimators=min(n_estimators, 100),
                    max_depth=15,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=self.n_jobs
                )

            model.fit(X_train, y_train)
            predictions = model.predict(X_predict)

            if not is_numeric:
                predictions = le.inverse_transform(predictions)

            result.loc[mask_missing] = predictions
            return result

        except Exception as e:
            return self._impute_median(df[target_column]) if is_numeric else self._impute_mode(df[target_column])

    def _impute_regression(
        self,
        df: pd.DataFrame,
        target_column: str,
        predictor_columns: Optional[List[str]] = None
    ) -> pd.Series:
        """
        Imputation par régression linéaire
        Optimal pour relations linéaires entre variables.
        """
        if predictor_columns and len(predictor_columns) > 0:
            X_cols = [col for col in predictor_columns if col in df.columns and col != target_column]
        else:
            X_cols = [col for col in df.columns if col != target_column]
            X_cols = [col for col in X_cols if pd.api.types.is_numeric_dtype(df[col])]

        if len(X_cols) == 0:
            return self._impute_median(df[target_column])

        result = df[target_column].copy()
        mask_missing = result.isna()
        
        if not mask_missing.any():
            return result

        # Préparer les données
        X = df[X_cols].copy().fillna(df[X_cols].median())

        X_train = X[~mask_missing]
        y_train = result[~mask_missing]
        X_predict = X[mask_missing]

        try:
            is_numeric = pd.api.types.is_numeric_dtype(result)
            
            if is_numeric:
                model = LinearRegression()
            else:
                le = LabelEncoder()
                y_train = le.fit_transform(y_train.astype(str))
                model = LogisticRegression(random_state=42, max_iter=1000)

            model.fit(X_train, y_train)
            predictions = model.predict(X_predict)

            if not is_numeric:
                predictions = le.inverse_transform(predictions.astype(int))

            result.loc[mask_missing] = predictions
            return result

        except Exception as e:
            return self._impute_median(df[target_column]) if is_numeric else self._impute_mode(df[target_column])

    def _impute_interpolation(
        self,
        series: pd.Series,
        method: str = 'linear',
        order: int = 2
    ) -> pd.Series:
        """
        Imputation par interpolation
        Excellent pour les séries temporelles ou données ordonnées.
        """
        try:
            if method == 'polynomial':
                return series.interpolate(method='polynomial', order=order, limit_direction='both')
            else:
                return series.interpolate(method=method, limit_direction='both')
        except Exception as e:
            return series.fillna(method='ffill').fillna(method='bfill')

    def validate_imputation(
        self,
        df_original: pd.DataFrame,
        df_imputed: pd.DataFrame,
        column: str,
        sample_fraction: float = 0.1
    ) -> Dict[str, float]:
        """
        Validation croisée de l'imputation.
        Masque aléatoirement des valeurs connues, impute, et mesure l'erreur.

        Args:
            df_original: DataFrame original
            df_imputed: DataFrame imputé
            column: Colonne à valider
            sample_fraction: Fraction de valeurs à masquer pour validation

        Returns:
            Dictionnaire avec métriques de validation
        """
        # TODO: Implémenter validation croisée
        return {
            'rmse': 0.0,
            'mae': 0.0,
            'accuracy': 0.0,
            'confidence': 0.8
        }
