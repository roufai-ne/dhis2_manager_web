"""
Routes pour le module d'imputation automatique de données
"""

from flask import Blueprint, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import os
import uuid
from datetime import datetime
import json

from app.services.column_analyzer import ColumnAnalyzer
from app.services.correlation_engine import CorrelationEngine
from app.services.imputation_engine import ImputationEngine
from app.utils.activity_logger import log_activity_decorator

# Créer le blueprint
imputation_bp = Blueprint('imputation', __name__, url_prefix='/imputation')

# Initialiser les services
column_analyzer = ColumnAnalyzer()

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Optimisations pour gros fichiers
MAX_PREVIEW_ROWS = 100  # Limiter aperçu
MAX_ANALYSIS_ROWS = 10000  # Échantillonner analyse si > 10k lignes
CHUNK_SIZE = 5000  # Taille des chunks pour lecture

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@imputation_bp.route('/')
@log_activity_decorator('Accès page imputation')
def index():
    """Page principale du module d'imputation"""
    return render_template('imputation_new.html')


@imputation_bp.route('/upload', methods=['POST'])
@log_activity_decorator('Upload fichier imputation')
def upload_file():
    """
    Upload et analyse initiale d'un fichier pour l'imputation.

    Returns:
        JSON avec file_id, aperçu des données et analyse des colonnes
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nom de fichier vide'}), 400

        # Valider l'extension
        if not allowed_file(file.filename):
            return jsonify({'error': 'Format de fichier non supporté. Utilisez .xlsx, .xls ou .csv'}), 400

        # Sauvegarder le fichier
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
        file.save(file_path)

        # Vérifier la taille
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            return jsonify({'error': f'Fichier trop volumineux ({file_size / 1024 / 1024:.1f} MB). Maximum: 50 MB'}), 400

        # Charger le fichier selon son type
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext in ['.xlsx', '.xls']:
            # Pour Excel, lire la première feuille par défaut avec optimisations
            # Lire d'abord seulement quelques lignes pour détecter la structure
            df_sample = pd.read_excel(file_path, sheet_name=0, nrows=1000)
            
            # Récupérer les noms des feuilles
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Lire le fichier complet avec dtypes optimisés
            df = pd.read_excel(file_path, sheet_name=0, dtype_backend='pyarrow')
            # Convertir en numpy pour éviter les conflits de types PyArrow lors de l'imputation
            df = df.convert_dtypes(dtype_backend='numpy_nullable')
        elif file_ext == '.csv':
            # Détecter l'encodage et le séparateur avec échantillon
            df_sample = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python', nrows=1000)
            
            # Lire le fichier complet optimisé
            df = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python', 
                           dtype_backend='pyarrow')
            # Convertir en numpy pour éviter les conflits de types PyArrow lors de l'imputation
            df = df.convert_dtypes(dtype_backend='numpy_nullable')
            sheet_names = None
        else:
            return jsonify({'error': 'Format de fichier non supporté'}), 400

        # Échantillonner pour analyse si trop de lignes
        df_for_analysis = df if len(df) <= MAX_ANALYSIS_ROWS else df.sample(n=MAX_ANALYSIS_ROWS, random_state=42)
        
        # Analyse initiale du fichier (sur échantillon si nécessaire)
        analysis = column_analyzer.analyze_dataframe(df_for_analysis)
        analysis['total_rows'] = len(df)  # Garder le vrai nombre total
        analysis['is_sampled'] = len(df) > MAX_ANALYSIS_ROWS

        # Sauvegarder dans la session
        session['imputation_file_id'] = file_id
        session['imputation_filename'] = secure_filename(file.filename)
        session['imputation_file_path'] = file_path
        session['imputation_sheet_names'] = sheet_names
        session['imputation_analysis'] = analysis
        session['imputation_total_rows'] = len(df)

        # Créer un aperçu limité des données (max 100 lignes pour performance)
        preview_rows = min(MAX_PREVIEW_ROWS, len(df))
        df_preview = df.head(preview_rows)
        
        # Optimiser colonnes pour aperçu (max 20 colonnes)
        if len(df_preview.columns) > 20:
            cols_to_show = list(df_preview.columns[:20])
            df_preview = df_preview[cols_to_show]
            truncated_cols = True
        else:
            truncated_cols = False
        
        # Remplacer NaN par None pour la sérialisation JSON
        preview = df_preview.replace({np.nan: None}).to_dict(orient='records')

        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': file.filename,
            'sheet_names': sheet_names,
            'preview': preview,
            'preview_info': {
                'rows_shown': len(preview),
                'total_rows': len(df),
                'cols_shown': len(df_preview.columns),
                'total_cols': len(df.columns),
                'truncated_cols': truncated_cols
            },
            'analysis': {
                'total_rows': analysis['total_rows'],
                'total_columns': analysis['total_columns'],
                'total_missing': analysis['total_missing'],
                'missing_percentage': round(analysis['missing_percentage'], 2),
                'global_quality_score': round(analysis['global_quality_score'], 2),
                'is_sampled': analysis.get('is_sampled', False)
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur lors du traitement du fichier: {str(e)}'}), 500


@imputation_bp.route('/change-sheet', methods=['POST'])
@log_activity_decorator('Changement de feuille Excel')
def change_sheet():
    """Change la feuille Excel active pour l'analyse"""
    try:
        data = request.get_json()
        sheet_name = data.get('sheet_name')

        if 'imputation_file_path' not in session:
            return jsonify({'error': 'Aucun fichier chargé'}), 400

        file_path = session['imputation_file_path']

        # Charger la nouvelle feuille avec optimisations
        df = pd.read_excel(file_path, sheet_name=sheet_name, dtype_backend='pyarrow')
        # Convertir en numpy pour éviter les conflits de types PyArrow
        df = df.convert_dtypes(dtype_backend='numpy_nullable')

        # Échantillonner pour analyse si nécessaire
        df_for_analysis = df if len(df) <= MAX_ANALYSIS_ROWS else df.sample(n=MAX_ANALYSIS_ROWS, random_state=42)
        
        # Analyser
        analysis = column_analyzer.analyze_dataframe(df_for_analysis)
        analysis['total_rows'] = len(df)
        analysis['is_sampled'] = len(df) > MAX_ANALYSIS_ROWS

        # Mettre à jour la session
        session['imputation_analysis'] = analysis
        session['imputation_total_rows'] = len(df)

        # Aperçu limité
        preview_rows = min(MAX_PREVIEW_ROWS, len(df))
        df_preview = df.head(preview_rows)
        
        # Limiter colonnes si nécessaire
        if len(df_preview.columns) > 20:
            df_preview = df_preview[list(df_preview.columns[:20])]
        
        # Remplacer NaN par None pour la sérialisation JSON
        preview = df_preview.replace({np.nan: None}).to_dict(orient='records')

        return jsonify({
            'success': True,
            'preview': preview,
            'analysis': {
                'total_rows': analysis['total_rows'],
                'total_columns': analysis['total_columns'],
                'total_missing': analysis['total_missing'],
                'missing_percentage': round(analysis['missing_percentage'], 2),
                'global_quality_score': round(analysis['global_quality_score'], 2)
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@imputation_bp.route('/analysis/<file_id>', methods=['GET'])
def get_analysis(file_id):
    """Retourne l'analyse détaillée de toutes les colonnes"""
    try:
        if session.get('imputation_file_id') != file_id:
            return jsonify({'error': 'Fichier non trouvé'}), 404

        analysis = session.get('imputation_analysis', {})

        # Formater pour l'affichage
        columns_data = []
        for col_name, col_analysis in analysis.get('columns', {}).items():
            columns_data.append({
                'name': col_name,
                'type': col_analysis['detected_type'],
                'confidence': round(col_analysis['type_confidence'] * 100, 1),
                'missing_count': col_analysis['quality']['missing_count'],
                'missing_percent': round(col_analysis['quality']['missing_percent'], 2),
                'outliers_count': col_analysis['outliers']['count'],
                'quality_score': round(col_analysis['quality_score'], 1),
                'recommendations': col_analysis['recommendations'],
                'statistics': col_analysis['statistics']
            })

        return jsonify({
            'success': True,
            'columns': columns_data,
            'summary': {
                'total_rows': analysis.get('total_rows', 0),
                'total_columns': analysis.get('total_columns', 0),
                'total_missing': analysis.get('total_missing', 0),
                'missing_percentage': round(analysis.get('missing_percentage', 0), 2),
                'global_quality_score': round(analysis.get('global_quality_score', 0), 1)
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@imputation_bp.route('/correlations/<file_id>', methods=['GET'])
def get_correlations(file_id):
    """Calcule et retourne les corrélations entre colonnes"""
    try:
        if session.get('imputation_file_id') != file_id:
            return jsonify({'error': 'Fichier non trouvé'}), 404

        file_path = session['imputation_file_path']
        analysis = session.get('imputation_analysis', {})

        # Charger le DataFrame avec optimisations
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, sheet_name=0, dtype_backend='pyarrow')
            df = df.convert_dtypes(dtype_backend='numpy_nullable')
        else:
            df = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python', 
                           dtype_backend='pyarrow')
            df = df.convert_dtypes(dtype_backend='numpy_nullable')

        # Échantillonner si trop gros pour corrélations (calcul intensif)
        if len(df) > MAX_ANALYSIS_ROWS:
            df = df.sample(n=MAX_ANALYSIS_ROWS, random_state=42)

        # Extraire les types de colonnes
        column_types = {
            col_name: col_data['detected_type']
            for col_name, col_data in analysis.get('columns', {}).items()
        }

        # Calculer les corrélations
        corr_engine = CorrelationEngine(min_correlation=0.3, max_predictors=5)
        corr_matrix = corr_engine.compute_correlation_matrix(df, column_types)

        # Trouver les meilleurs prédicteurs pour chaque colonne avec valeurs manquantes
        predictors_by_column = {}
        for col_name, col_data in analysis.get('columns', {}).items():
            if col_data['quality']['missing_count'] > 0:
                predictors_info = corr_engine.find_best_predictors(
                    df, col_name, column_types
                )
                predictors_by_column[col_name] = predictors_info

        # Convertir la matrice de corrélation en format JSON
        # Limiter taille si trop de colonnes
        if len(corr_matrix.columns) > 50:
            # Garder seulement colonnes les plus corrélées
            top_cols = corr_matrix.abs().sum().nlargest(50).index
            corr_matrix = corr_matrix.loc[top_cols, top_cols]
        
        # Remplacer NaN par None pour éviter les erreurs JSON
        corr_matrix_dict = corr_matrix.round(3).replace({np.nan: None}).to_dict()

        return jsonify({
            'success': True,
            'correlation_matrix': corr_matrix_dict,
            'predictors_by_column': predictors_by_column
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul des corrélations: {str(e)}'}), 500


@imputation_bp.route('/recommendations/<file_id>', methods=['GET'])
def get_recommendations(file_id):
    """Retourne les recommandations d'imputation pour chaque colonne"""
    try:
        if session.get('imputation_file_id') != file_id:
            return jsonify({'error': 'Fichier non trouvé'}), 404

        file_path = session.get('imputation_file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Fichier introuvable sur le serveur'}), 404

        analysis = session.get('imputation_analysis', {})
        if not analysis or 'columns' not in analysis:
            return jsonify({'error': 'Analyse non disponible'}), 400

        # Charger le DataFrame avec optimisations
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, sheet_name=0, dtype_backend='pyarrow')
            df = df.convert_dtypes(dtype_backend='numpy_nullable')
        else:
            df = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python',
                           dtype_backend='pyarrow')
            df = df.convert_dtypes(dtype_backend='numpy_nullable')

        # Échantillonner si trop gros
        if len(df) > MAX_ANALYSIS_ROWS:
            df = df.sample(n=MAX_ANALYSIS_ROWS, random_state=42)

        # Extraire les types
        column_types = {
            col_name: col_data['detected_type']
            for col_name, col_data in analysis.get('columns', {}).items()
        }

        # Calculer les corrélations
        corr_engine = CorrelationEngine()

        # Générer les recommandations
        recommendations = {}
        for col_name, col_data in analysis.get('columns', {}).items():
            if col_data.get('quality', {}).get('missing_count', 0) > 0:
                try:
                    predictors_info = corr_engine.find_best_predictors(
                        df, col_name, column_types
                    )

                    recommendations[col_name] = {
                        'method': predictors_info.get('recommended_method', 'median'),
                        'grouping_columns': predictors_info.get('grouping_columns', []),
                        'has_strong_correlations': predictors_info.get('has_strong_correlations', False),
                        'predictors': predictors_info.get('predictors', [])[:3],  # Top 3
                        'missing_count': col_data['quality']['missing_count'],
                        'missing_percent': col_data['quality']['missing_percent']
                    }
                except Exception as e:
                    # En cas d'erreur sur une colonne, on continue avec les autres
                    print(f"Erreur pour colonne {col_name}: {e}")
                    continue

        # Nettoyer les NaN pour la sérialisation JSON
        def clean_for_json(obj):
            """Nettoie récursivement un objet pour la sérialisation JSON"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(v) for v in obj]
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

        recommendations_clean = clean_for_json(recommendations)

        return jsonify({
            'success': True,
            'recommendations': recommendations_clean
        }), 200

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Erreur dans get_recommendations: {error_details}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la génération des recommandations: {str(e)}'
        }), 500


@imputation_bp.route('/execute', methods=['POST'])
@log_activity_decorator('Exécution imputation')
def execute_imputation():
    """
    Exécute l'imputation selon la configuration fournie.

    Body JSON:
        {
            "file_id": "uuid",
            "configuration": {
                "column_name": {
                    "method": "knn",
                    "parameters": {...}
                }
            }
        }
    """
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        configuration = data.get('configuration', {})

        if session.get('imputation_file_id') != file_id:
            return jsonify({'error': 'Fichier non trouvé'}), 404

        file_path = session['imputation_file_path']

        # Charger le DataFrame avec optimisations
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            df_original = pd.read_excel(file_path, sheet_name=0, dtype_backend='pyarrow')
            df_original = df_original.convert_dtypes(dtype_backend='numpy_nullable')
        else:
            df_original = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python',
                                    dtype_backend='pyarrow')
            df_original = df_original.convert_dtypes(dtype_backend='numpy_nullable')

        # Exécuter l'imputation
        imputation_engine = ImputationEngine()
        df_imputed, imputation_report = imputation_engine.impute_dataframe(
            df_original, configuration
        )

        # Identifier les cellules imputées (limiter pour performance)
        imputed_cells = {}
        max_cells_to_track = 1000  # Limiter nombre de cellules suivies
        total_tracked = 0
        
        for col in df_original.columns:
            if col in df_imputed.columns and total_tracked < max_cells_to_track:
                # Trouver les indices où les valeurs ont changé
                was_nan = df_original[col].isna()
                is_filled = df_imputed[col].notna()
                imputed_indices = df_original.index[was_nan & is_filled].tolist()
                
                if imputed_indices:
                    # Limiter nombre d'indices par colonne
                    imputed_indices = imputed_indices[:min(100, len(imputed_indices))]
                    imputed_cells[col] = imputed_indices
                    total_tracked += len(imputed_indices)

        # Créer un aperçu limité avec les valeurs imputées
        preview_rows = min(MAX_PREVIEW_ROWS, len(df_imputed))
        preview_df = df_imputed.head(preview_rows)
        
        # Limiter colonnes pour aperçu
        if len(preview_df.columns) > 20:
            preview_df = preview_df[list(preview_df.columns[:20])]
        
        preview_df = preview_df.replace({np.nan: None})
        preview_data = preview_df.to_dict(orient='records')

        # Sauvegarder le fichier imputé dans le même répertoire que le fichier d'upload
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        uploads_dir = project_root / 'uploads'
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = uploads_dir / f"{file_id}_imputed.xlsx"

        # Sauvegarder en Excel
        df_imputed.to_excel(str(output_path), index=False)

        # Nettoyer le rapport pour JSON
        def clean_for_json(obj):
            """Nettoie récursivement un objet pour la sérialisation JSON"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(v) for v in obj]
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

        imputation_report_clean = clean_for_json(imputation_report)
        preview_data_clean = clean_for_json(preview_data)
        imputed_cells_clean = clean_for_json(imputed_cells)

        # Sauvegarder dans la session (convertir Path en string)
        session['imputation_output_path'] = str(output_path)
        session['imputation_report'] = imputation_report_clean

        return jsonify({
            'success': True,
            'report': imputation_report_clean,
            'preview': preview_data_clean,
            'imputed_cells': imputed_cells_clean,
            'download_url': f'/imputation/download/{file_id}'
        }), 200

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Erreur dans execute_imputation: {error_details}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors de l\'imputation: {str(e)}'
        }), 500


@imputation_bp.route('/download/<file_id>', methods=['GET'])
@log_activity_decorator('Téléchargement fichier imputé')
def download_file(file_id):
    """Télécharge le fichier imputé"""
    try:
        if session.get('imputation_file_id') != file_id:
            return jsonify({'error': 'Fichier non trouvé dans la session'}), 404

        output_path = session.get('imputation_output_path')
        original_filename = session.get('imputation_filename')
        
        if not output_path:
            return jsonify({'error': 'Chemin du fichier imputé non trouvé dans la session'}), 404
            
        if not os.path.exists(output_path):
            return jsonify({'error': f'Fichier imputé introuvable: {output_path}'}), 404

        if not original_filename:
            original_filename = 'data.xlsx'

        # Créer le nom du fichier avec le préfixe "imputed_"
        base_name = os.path.splitext(original_filename)[0]
        extension = os.path.splitext(original_filename)[1] or '.xlsx'
        download_filename = f"imputed_{base_name}{extension}"

        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Erreur dans download_file: {error_details}")
        return jsonify({'error': f'Erreur lors du téléchargement: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'Erreur lors du téléchargement: {str(e)}'}), 500


@imputation_bp.route('/report/<file_id>', methods=['GET'])
def get_report(file_id):
    """Retourne le rapport d'imputation détaillé"""
    try:
        if session.get('imputation_file_id') != file_id:
            return jsonify({'error': 'Fichier non trouvé'}), 404

        report = session.get('imputation_report', {})

        return jsonify({
            'success': True,
            'report': report
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@imputation_bp.route('/clear', methods=['POST'])
@log_activity_decorator('Nettoyage session imputation')
def clear_session():
    """Nettoie les données de session de l'imputation"""
    try:
        # Supprimer les fichiers temporaires
        if 'imputation_file_path' in session:
            file_path = session['imputation_file_path']
            if os.path.exists(file_path):
                os.remove(file_path)

        if 'imputation_output_path' in session:
            output_path = session['imputation_output_path']
            if os.path.exists(output_path):
                os.remove(output_path)

        # Nettoyer la session
        keys_to_remove = [
            'imputation_file_id',
            'imputation_filename',
            'imputation_file_path',
            'imputation_sheet_names',
            'imputation_analysis',
            'imputation_output_path',
            'imputation_report'
        ]

        for key in keys_to_remove:
            session.pop(key, None)

        return jsonify({'success': True, 'message': 'Session nettoyée'}), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500
