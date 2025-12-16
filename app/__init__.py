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
    
    # Configuration du logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/dhis2_manager.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('DHIS2 Manager Web startup')
    
    # Enregistrer les blueprints (routes)
    from app.routes import main, configuration, generator, calculator, api
    app.register_blueprint(main.bp)
    app.register_blueprint(configuration.bp)
    app.register_blueprint(generator.bp)
    app.register_blueprint(calculator.bp)
    app.register_blueprint(api.bp)
    
    # Service de nettoyage des sessions au démarrage
    from app.services.session_manager import cleanup_old_sessions
    cleanup_old_sessions(app.config['SESSION_CLEANUP_HOURS'])
    
    # Enregistrer le nettoyage à l'arrêt
    import atexit
    atexit.register(lambda: cleanup_old_sessions(app.config['SESSION_CLEANUP_HOURS']))
    
    return app
