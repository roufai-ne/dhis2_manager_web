"""
Routes API pour les opérations asynchrones
"""

from flask import Blueprint, request, jsonify, session

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/session/info', methods=['GET'])
def session_info():
    """Retourne les informations de la session"""
    return jsonify({
        'has_metadata': 'metadata' in session,
        'has_source': 'source_file' in session,
        'metadata_stats': session.get('metadata_stats', {})
    })


@bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})
