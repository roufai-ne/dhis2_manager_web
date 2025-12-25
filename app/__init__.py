"""
DHIS2 Data Manager Web - Application Factory
============================================
Application Flask avec gestion des sessions sans base de données

Auteur: Amadou Roufai
Version: 5.0 Web Edition
"""

from flask import Flask
from flask_session import Session
from flask_cors import CORS
import os
import logging
from logging.handlers import RotatingFileHandler

# Instance de session (sera initialisée dans create_app)
sess = Session()


def create_app(config_name='default'):
    """Factory pour créer l'application Flask"""
    
    app = Flask(__name__)
    
    # Charger la configuration
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Initialiser Flask-Session
    sess.init_app(app)
    
    # CORS (si nécessaire pour API)
    CORS(app)
    
    # S'assurer que les dossiers nécessaires existent
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Configuration du logging (actif en développement et production)
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Handler pour fichier avec format enrichi
    file_handler = RotatingFileHandler(
        app.config.get('LOG_FILE', 'logs/app.log'),
        maxBytes=app.config.get('LOG_MAX_BYTES', 10485760),
        backupCount=app.config.get('LOG_BACKUP_COUNT', 10)
    )
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('DHIS2 Manager Web startup')
    
    # Desactiver le cache en mode DEBUG
    if app.config['DEBUG']:
        @app.after_request
        def add_header(response):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

    # Injecter la version pour le cache busting
    @app.context_processor
    def inject_version():
        import time
        # En dev: timestamp actuel (cache buster aggressif)
        # En prod: version fixe ou timestamp de démarrage
        version = int(time.time()) if app.config['DEBUG'] else '5.1'
        return dict(version=version)

    # Enregistrer les blueprints (routes)
    from app.routes import main, configuration, generator, calculator, api, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(configuration.bp)
    app.register_blueprint(generator.bp)
    app.register_blueprint(calculator.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)
    
    # Service de nettoyage des sessions au démarrage
    from app.services.session_manager import cleanup_old_sessions
    cleanup_old_sessions(app.config['SESSION_CLEANUP_HOURS'])
    
    # Enregistrer le nettoyage à l'arrêt
    import atexit
    atexit.register(lambda: cleanup_old_sessions(app.config['SESSION_CLEANUP_HOURS']))
    
    return app
