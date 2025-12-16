"""
Routes principales de l'application
"""

from flask import Blueprint, render_template, session
from app.services.metadata_manager import MetadataManager
import logging

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


@bp.route('/')
def index():
    """Page d'accueil / Dashboard"""
    # Vérifier si des métadonnées sont chargées
    has_metadata = 'metadata' in session
    
    metadata_info = None
    if has_metadata:
        try:
            metadata = MetadataManager.from_dict(session['metadata'])
            metadata_info = metadata.get_stats()
            metadata_info['filename'] = session.get('metadata_file', 'Unknown')
        except Exception as e:
            logger.error(f"Erreur récupération métadonnées dashboard: {e}")
    
    # Informations de session
    session_info = {
        'has_excel': 'excel_filename' in session,
        'excel_filename': session.get('excel_filename'),
        'has_json': 'json_filename' in session,
        'json_filename': session.get('json_filename')
    }
    
    return render_template(
        'index.html',
        has_metadata=has_metadata,
        metadata_info=metadata_info,
        session_info=session_info
    )


@bp.route('/about')
def about():
    """Page À propos"""
    return render_template('about.html')


@bp.route('/help')
def help_page():
    """Page d'aide et documentation"""
    return render_template('help.html')
