"""
Routes pour la configuration et l'upload des métadonnées
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
import os
import logging
import base64
from werkzeug.utils import secure_filename
from pathlib import Path

from app.services.session_manager import ensure_session_dir, cleanup_session_files
from app.services.metadata_manager import MetadataManager
from app.services.dhis2_api import DHIS2ApiService
from app.utils.activity_logger import log_activity

bp = Blueprint('configuration', __name__, url_prefix='/configuration')
logger = logging.getLogger(__name__)

# Extensions autorisées
ALLOWED_EXTENSIONS = {'json'}


@bp.route('/')
def configuration_page():
    """Affiche la page de configuration"""
    # Récupérer les infos de métadonnées si présentes
    metadata_info = None
    if 'metadata' in session:
        try:
            manager = MetadataManager.from_dict(session['metadata'])
            metadata_info = manager.get_stats()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métadonnées: {e}")
            flash('Erreur lors de la récupération des métadonnées', 'error')
    
    return render_template(
        'configuration.html',
        metadata_info=metadata_info
    )





@bp.route('/api/metadata/status', methods=['GET'])
def metadata_status():
    """
    Vérifie le statut des métadonnées chargées
    
    Returns:
        JSON avec le statut
    """
    if 'metadata' not in session:
        return jsonify({
            'loaded': False
        }), 200
    
    try:
        manager = MetadataManager.from_dict(session['metadata'])
        stats = manager.get_stats()
        
        return jsonify({
            'loaded': True,
            'filename': session.get('metadata_file', 'Unknown'),
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({
            'loaded': False,
            'error': str(e)
        }), 500


@bp.route('/api/debug/sections/<dataset_id>', methods=['GET'])
def debug_sections(dataset_id):
    """
    Endpoint de debug pour inspecter les sections d'un dataset
    
    Args:
        dataset_id: ID du dataset
        
    Returns:
        JSON avec la structure des sections
    """
    if 'metadata' not in session:
        return jsonify({
            'error': 'Aucune métadonnée chargée'
        }), 400
    
    try:
        manager = MetadataManager.from_dict(session['metadata'])
        
        # Récupérer les sections pour ce dataset
        sections_indexed = manager.sections_by_dataset.get(dataset_id, [])
        
        # Détails complets des sections
        sections_details = []
        for section in sections_indexed:
            sections_details.append({
                'id': section.get('id'),
                'name': section.get('name'),
                'displayName': section.get('displayName'),
                'sortOrder': section.get('sortOrder'),
                'dataElements_count': len(section.get('dataElements', []))
            })
        
        return jsonify({
            'success': True,
            'dataset_id': dataset_id,
            'sections_count': len(sections_indexed),
            'sections': sections_details
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur debug sections: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@bp.route('/api/datasets', methods=['GET'])
def get_datasets():
    """
    Retourne la liste des datasets disponibles

    Returns:
        JSON avec la liste des datasets
    """
    if 'metadata' not in session:
        return jsonify({
            'success': False,
            'error': 'Aucune métadonnée chargée'
        }), 400

    try:
        manager = MetadataManager.from_dict(session['metadata'])

        # Utiliser la méthode get_datasets() qui gère correctement la structure
        datasets = manager.get_datasets()

        # Trier par nom
        datasets.sort(key=lambda x: x['name'])

        return jsonify({
            'success': True,
            'datasets': datasets
        }), 200

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des datasets: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


@bp.route('/clear', methods=['POST'])
def clear_metadata():
    """Efface les métadonnées de la session"""
    session.pop('metadata', None)
    session.pop('metadata_file', None)
    
    # Nettoyer les fichiers temporaires de la session
    session_id = session.get('_id', session.sid)
    cleanup_session_files(session_id)
    
    flash('Métadonnées effacées avec succès', 'success')
    return redirect(url_for('configuration.configuration_page'))


@bp.route('/api/dhis2/test-connection', methods=['POST'])
def test_dhis2_connection():
    """
    Teste la connexion à une instance DHIS2
    """
    try:
        data = request.json
        url = data.get('url', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not url or not username or not password:
            return jsonify({
                'success': False,
                'error': 'URL, nom d\'utilisateur et mot de passe requis'
            }), 400
        
        # Test de connexion
        api = DHIS2ApiService()
        success, message = api.test_connection(url, username, password)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 401
            
    except Exception as e:
        logger.error(f"Erreur test connexion: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


@bp.route('/api/dhis2/fetch-metadata', methods=['POST'])
def fetch_dhis2_metadata():
    """
    Récupère les métadonnées depuis DHIS2
    """
    try:
        data = request.json
        url = data.get('url', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not url or not username or not password:
            return jsonify({
                'success': False,
                'error': 'URL, nom d\'utilisateur et mot de passe requis'
            }), 400
        
        # Connexion et téléchargement
        api = DHIS2ApiService()
        
        # Tester d'abord
        success, message = api.test_connection(url, username, password)
        if not success:
            return jsonify({
                'success': False,
                'error': f'Connexion échouée: {message}'
            }), 401
        
        # Récupérer les métadonnées
        success, metadata, message = api.fetch_metadata()
        
        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
        # Charger dans MetadataManager
        manager = MetadataManager()
        load_success, errors, warnings = manager.load_from_dict(metadata)
        
        if not load_success:
            return jsonify({
                'success': False,
                'error': 'Erreur lors du chargement des métadonnées',
                'details': errors
            }), 500
        
        # Valider la structure
        valid, validation_errors = manager.validate_structure()
        if not valid:
            return jsonify({
                'success': False,
                'error': 'Structure de métadonnées invalide',
                'details': validation_errors
            }), 500
        
        # Sauvegarder en session
        session['metadata'] = manager.to_dict()
        session['metadata_source'] = 'api'
        session['dhis2_url'] = url
        session['dhis2_username'] = username
        # Encoder les credentials en base64 pour l'authentification
        credentials = f"{username}:{password}"
        session['dhis2_auth'] = base64.b64encode(credentials.encode()).decode()
        
        stats = manager.get_stats()
        
        logger.info(f"Métadonnées DHIS2 chargées: {stats}")
        log_activity(f"Connexion DHIS2 réussie - URL: {url} - Stats: {stats}", 'info')
        
        return jsonify({
            'success': True,
            'message': message,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur récupération métadonnées: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }), 500


@bp.route('/api/dhis2/disconnect', methods=['POST'])
def disconnect_dhis2():
    """Déconnexion DHIS2 et nettoyage session"""
    url = session.get('dhis2_url', 'unknown')
    
    # Logger AVANT de supprimer les infos de session
    logger.info("Déconnexion DHIS2")
    log_activity(f"Déconnexion DHIS2 - URL: {url}", 'info')
    
    # Maintenant supprimer les infos de session
    session.pop('dhis2_url', None)
    session.pop('dhis2_username', None)
    session.pop('dhis2_auth', None)
    session.pop('metadata_source', None)
    session.pop('metadata', None)
    session.pop('metadata_file', None)
    
    # Note: Les fichiers Excel/JSON ne sont pas effacés lors de la déconnexion
    # L'utilisateur peut les effacer manuellement avec le bouton "Tout effacer"
    
    return jsonify({'success': True, 'message': 'Déconnecté avec succès'})


@bp.route('/api/session/clear', methods=['POST'])
def clear_session_files():
    """Clear Excel and JSON files from the session."""
    try:
        # Remove files from session
        session.pop('excel_filename', None)
        session.pop('json_filename', None)
        session.pop('excel_path', None)
        session.pop('json_path', None)
        
        return jsonify({'success': True, 'message': 'Fichiers de session effacés'})
    except Exception as e:
        logger.error(f"Error clearing session files: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
