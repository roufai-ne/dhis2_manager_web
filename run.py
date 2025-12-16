"""
Point d'entrée de l'application DHIS2 Manager Web
"""

import os
from flask import jsonify
from app import create_app

# Créer l'application
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

# Health check endpoint pour Docker
@app.route('/health')
def health_check():
    """Endpoint de santé pour monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'dhis2-manager',
        'version': '5.0'
    }), 200

if __name__ == '__main__':
    # Lancer le serveur de développement
    app.run(host='0.0.0.0', port=5000, debug=True)
