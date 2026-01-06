"""
Service d'analyse automatique des colonnes
Détecte les types de données, calcule les statistiques et identifie les problèmes de qualité
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Any, Optional
import re
from datetime import datetime


class DataType:
    """Énumération des types de données détectés"""
    NUMERIC_CONTINUOUS = "numeric_continuous"
    NUMERIC_DISCRETE = "numeric_discrete"
    CATEGORICAL_NOMINAL = "categorical_nominal"
    CATEGORICAL_ORDINAL = "categorical_ordinal"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXT = "text"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ColumnAnalyzer:
    """Service d'analyse de colonnes pour l'imputation"""

    def __init__(self):
        self.ordinal_patterns = [
            ['faible', 'moyen', 'fort', 'très fort'],
            ['low', 'medium', 'high', 'very high'],
            ['petit', 'moyen', 'grand'],
            ['1er', '2e', '3e', '4e', '5e'],
            ['primaire', 'secondaire', 'supérieur'],
            ['mauvais', 'passable', 'bon', 'excellent'],
        ]

    def _clean_for_json(self, obj):
        """
        Nettoie récursivement un objet pour la sérialisation JSON.
        Remplace NaN, inf, -inf par None et convertit les types numpy.
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
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif pd.isna(obj):
            return None
        return obj

    def analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse complète d'un DataFrame.

        Args:
            df: DataFrame à analyser

        Returns:
            Dictionnaire contenant l'analyse de toutes les colonnes
        """
        results = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': {},
            'global_quality_score': 0.0,
            'total_missing': 0,
            'analysis_timestamp': datetime.now().isoformat()
        }

        total_cells = len(df) * len(df.columns)
        total_missing = 0
        quality_scores = []

        for col in df.columns:
            analysis = self.analyze_column(df[col], col)
            results['columns'][col] = analysis
            total_missing += analysis['quality']['missing_count']
            quality_scores.append(analysis['quality_score'])

        results['total_missing'] = total_missing
        results['missing_percentage'] = (total_missing / total_cells * 100) if total_cells > 0 else 0
        results['global_quality_score'] = np.mean(quality_scores) if quality_scores else 0

        # Nettoyer les NaN pour la sérialisation JSON
        return self._clean_for_json(results)

    def analyze_column(self, series: pd.Series, column_name: str) -> Dict[str, Any]:
        """
        Analyse détaillée d'une colonne.

        Args:
            series: Série pandas à analyser
            column_name: Nom de la colonne

        Returns:
            Dictionnaire avec les résultats d'analyse
        """
        detected_type, confidence = self.detect_column_type(series)
        statistics = self.compute_statistics(series, detected_type)
        quality = self.assess_quality(series, detected_type)
        outliers = self.detect_outliers(series, detected_type)

        # Calculer le score de qualité global (0-100)
        quality_score = self._calculate_quality_score(quality, outliers)

        # Générer des recommandations
        recommendations = self._generate_recommendations(
            series, detected_type, quality, outliers
        )

        return {
            'name': column_name,
            'detected_type': detected_type,
            'type_confidence': confidence,
            'statistics': statistics,
            'quality': quality,
            'outliers': outliers,
            'quality_score': quality_score,
            'recommendations': recommendations
        }

    def detect_column_type(self, series: pd.Series) -> Tuple[str, float]:
        """
        Détecte automatiquement le type d'une colonne.

        Returns:
            (type_détecté, niveau_de_confiance)
        """
        clean_series = series.dropna()

        if len(clean_series) == 0:
            return (DataType.UNKNOWN, 0.0)

        # Test 1: Booléen
        unique_values = clean_series.unique()
        if len(unique_values) <= 2:
            bool_indicators = {
                True, False, 0, 1, '0', '1', 'true', 'false',
                'yes', 'no', 'oui', 'non', 'Y', 'N', 'O', 'N'
            }
            if set(str(v).lower() for v in unique_values).issubset(
                {str(b).lower() for b in bool_indicators}
            ):
                return (DataType.BOOLEAN, 0.95)

        # Test 2: Numérique
        numeric_series = pd.to_numeric(clean_series, errors='coerce')
        numeric_ratio = numeric_series.notna().sum() / len(clean_series)

        if numeric_ratio > 0.9:
            # Distinguer continu vs discret
            if numeric_series.dtype in ['int64', 'int32']:
                unique_ratio = len(numeric_series.unique()) / len(numeric_series)
                if unique_ratio < 0.05:
                    return (DataType.NUMERIC_DISCRETE, numeric_ratio)
                return (DataType.NUMERIC_CONTINUOUS, numeric_ratio)
            else:
                # Float - vérifier si ce sont des entiers déguisés
                is_integer = (numeric_series == numeric_series.astype(int)).all()
                if is_integer:
                    return (DataType.NUMERIC_DISCRETE, numeric_ratio * 0.9)
                return (DataType.NUMERIC_CONTINUOUS, numeric_ratio)

        # Test 3: Date
        date_series = pd.to_datetime(clean_series, errors='coerce', infer_datetime_format=True)
        date_ratio = date_series.notna().sum() / len(clean_series)
        if date_ratio > 0.8:
            return (DataType.DATETIME, date_ratio)

        # Test 4: Catégoriel
        unique_ratio = len(unique_values) / len(clean_series)
        if unique_ratio < 0.5:
            # Vérifier s'il y a un ordre implicite
            if self._has_ordinal_pattern(unique_values):
                return (DataType.CATEGORICAL_ORDINAL, 0.8)
            return (DataType.CATEGORICAL_NOMINAL, 0.85)

        # Par défaut: texte libre
        return (DataType.TEXT, 0.7)

    def compute_statistics(self, series: pd.Series, data_type: str) -> Dict[str, Any]:
        """Calcule les statistiques descriptives selon le type de données"""
        stats_dict = {
            'count': len(series),
            'missing': series.isna().sum(),
            'missing_percent': (series.isna().sum() / len(series) * 100) if len(series) > 0 else 0
        }

        clean_series = series.dropna()

        if data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
            numeric_series = pd.to_numeric(clean_series, errors='coerce')
            # Convertir en numpy pour supporter toutes les opérations statistiques
            # (PyArrow ne supporte pas kurt/skew)
            if hasattr(numeric_series, 'to_numpy'):
                numeric_series = pd.Series(numeric_series.to_numpy())
            
            stats_dict.update({
                'mean': float(numeric_series.mean()) if len(numeric_series) > 0 else None,
                'std': float(numeric_series.std()) if len(numeric_series) > 0 else None,
                'min': float(numeric_series.min()) if len(numeric_series) > 0 else None,
                'max': float(numeric_series.max()) if len(numeric_series) > 0 else None,
                'median': float(numeric_series.median()) if len(numeric_series) > 0 else None,
                'q1': float(numeric_series.quantile(0.25)) if len(numeric_series) > 0 else None,
                'q3': float(numeric_series.quantile(0.75)) if len(numeric_series) > 0 else None,
                'skewness': float(numeric_series.skew()) if len(numeric_series) > 0 else None,
                'kurtosis': float(numeric_series.kurtosis()) if len(numeric_series) > 0 else None
            })

        elif data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL, DataType.BOOLEAN]:
            value_counts = clean_series.value_counts()
            stats_dict.update({
                'unique': len(clean_series.unique()),
                'top': str(value_counts.index[0]) if len(value_counts) > 0 else None,
                'freq': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                'distribution': {str(k): int(v) for k, v in value_counts.head(10).items()}
            })

        elif data_type == DataType.DATETIME:
            date_series = pd.to_datetime(clean_series, errors='coerce')
            stats_dict.update({
                'min': date_series.min().isoformat() if len(date_series) > 0 else None,
                'max': date_series.max().isoformat() if len(date_series) > 0 else None,
                'range_days': (date_series.max() - date_series.min()).days if len(date_series) > 0 else None
            })

        return stats_dict

    def assess_quality(self, series: pd.Series, data_type: str) -> Dict[str, Any]:
        """Évalue la qualité des données de la colonne"""
        quality = {
            'missing_count': int(series.isna().sum()),
            'missing_percent': float((series.isna().sum() / len(series) * 100) if len(series) > 0 else 0),
            'duplicates_count': int(series.duplicated().sum()),
            'format_issues': []
        }

        clean_series = series.dropna()

        # Détection de valeurs sentinelles
        sentinel_values = ['999', '9999', '-1', 'N/A', 'NULL', 'null', 'None', '#N/A']
        sentinel_count = clean_series.isin(sentinel_values).sum()
        if sentinel_count > 0:
            quality['format_issues'].append(f"{sentinel_count} valeurs sentinelles détectées")

        # Détection d'espaces superflus pour les chaînes
        if data_type in [DataType.TEXT, DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
            has_leading_trailing = clean_series.astype(str).apply(lambda x: x != x.strip()).sum()
            if has_leading_trailing > 0:
                quality['format_issues'].append(f"{has_leading_trailing} valeurs avec espaces superflus")

        return quality

    def detect_outliers(self, series: pd.Series, data_type: str) -> Dict[str, Any]:
        """Détecte les valeurs aberrantes"""
        outliers_info = {
            'count': 0,
            'indices': [],
            'method': None
        }

        if data_type not in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
            return outliers_info

        numeric_series = pd.to_numeric(series, errors='coerce')
        clean_series = numeric_series.dropna()

        if len(clean_series) < 4:
            return outliers_info

        # Méthode IQR
        Q1 = clean_series.quantile(0.25)
        Q3 = clean_series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers_mask = (numeric_series < lower_bound) | (numeric_series > upper_bound)
        outliers_indices = numeric_series[outliers_mask].index.tolist()

        outliers_info['count'] = len(outliers_indices)
        outliers_info['indices'] = outliers_indices[:100]  # Limiter à 100 pour la performance
        outliers_info['method'] = 'IQR'
        outliers_info['bounds'] = {
            'lower': float(lower_bound),
            'upper': float(upper_bound)
        }

        return outliers_info

    def _has_ordinal_pattern(self, values) -> bool:
        """Détecte si les valeurs ont un pattern ordinal"""
        values_lower = [str(v).lower() for v in values]
        for pattern in self.ordinal_patterns:
            if any(p in values_lower for p in pattern):
                return True
        return False

    def _calculate_quality_score(self, quality: Dict, outliers: Dict) -> float:
        """Calcule un score de qualité de 0 à 100"""
        score = 100.0

        # Pénalité pour valeurs manquantes
        missing_penalty = quality['missing_percent'] * 0.5
        score -= missing_penalty

        # Pénalité pour problèmes de format
        format_penalty = len(quality['format_issues']) * 5
        score -= format_penalty

        # Pénalité pour valeurs aberrantes (légère)
        outlier_penalty = min(outliers['count'] * 0.1, 10)
        score -= outlier_penalty

        return max(0.0, min(100.0, score))

    def _generate_recommendations(
        self,
        series: pd.Series,
        data_type: str,
        quality: Dict,
        outliers: Dict
    ) -> List[str]:
        """Génère des recommandations pour l'imputation"""
        recommendations = []

        missing_percent = quality['missing_percent']

        if missing_percent == 0:
            recommendations.append("Aucune imputation nécessaire - données complètes")
            return recommendations

        if missing_percent > 40:
            recommendations.append(
                f"ATTENTION: {missing_percent:.1f}% de valeurs manquantes - "
                "fiabilité de l'imputation réduite"
            )

        # Recommandations selon le type
        if data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
            if missing_percent < 5:
                recommendations.append("Imputation recommandée: Médiane (robuste)")
            elif missing_percent < 20:
                recommendations.append("Imputation recommandée: KNN ou Moyenne par groupe")
            else:
                recommendations.append("Imputation recommandée: MICE (Multiple Imputation)")

        elif data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
            if missing_percent < 10:
                recommendations.append("Imputation recommandée: Mode global")
            else:
                recommendations.append("Imputation recommandée: Mode par groupe ou KNN catégoriel")

        elif data_type == DataType.DATETIME:
            recommendations.append("Imputation recommandée: Médiane des dates ou interpolation")

        # Avertissement pour valeurs aberrantes
        if outliers['count'] > 0:
            recommendations.append(
                f"{outliers['count']} valeurs aberrantes détectées - "
                "considérer le traitement avant imputation"
            )

        # Avertissement pour problèmes de format
        if quality['format_issues']:
            recommendations.append(
                "Problèmes de format détectés - nettoyage recommandé"
            )

        return recommendations
