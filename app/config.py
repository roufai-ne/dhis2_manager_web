"""
Configuration de l'application DHIS2 Manager
==========================================
Configuration sécurisée avec validation des variables critiques
"""

import os
import secrets
from dotenv import load_dotenv

load_dotenv()


def generate_secret_key() -> str:
    """Génère une clé secrète sécurisée"""
    return secrets.token_hex(32)


def validate_production_config():
    """Valide que la configuration production est sécurisée"""
    if os.environ.get('FLASK_ENV') == 'production':
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key or secret_key == 'dev-secret-key-please-change-in-production':
            raise ValueError(
                "❌ ERREUR CRITIQUE: SECRET_KEY doit être définie en production!\n"
                "Générez une clé avec: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                "Puis ajoutez SECRET_KEY=<votre_clé> dans .env"
            )

        if len(secret_key) < 32:
            raise ValueError("❌ SECRET_KEY trop courte (minimum 32 caractères)")


class Config:
    """Configuration de base"""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or generate_secret_key()

    # Session Configuration
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')
    SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', './sessions')
    SESSION_PERMANENT = os.environ.get('SESSION_PERMANENT', 'False').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '3600'))
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '52428800'))  # 50 MB
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'json,xlsx,xls,csv').split(','))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './sessions')

    # Session Cleanup
    SESSION_CLEANUP_HOURS = int(os.environ.get('SESSION_CLEANUP_HOURS', '2'))

    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = int(os.environ.get('SEND_FILE_MAX_AGE_DEFAULT', '0'))

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Pas d'expiration (géré par session)
    WTF_CSRF_SSL_STRICT = os.environ.get('WTF_CSRF_SSL_STRICT', 'False').lower() == 'true'

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10 MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '10'))
    
    # Admin Configuration
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme123')

    # Allowed Hosts (pour production)
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')


class DevelopmentConfig(Config):
    """Configuration développement"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True  # Activé même en dev pour tester


class ProductionConfig(Config):
    """Configuration production"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Forcer HTTPS
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SSL_STRICT = True

    def __init__(self):
        validate_production_config()


class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Désactivé pour faciliter les tests
    SESSION_TYPE = 'filesystem'
    RATELIMIT_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """
    Retourne la configuration appropriée

    Args:
        env: Environnement (development, production, testing)

    Returns:
        Instance de configuration
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')

    config_class = config.get(env, config['default'])

    # Validation production
    if env == 'production':
        validate_production_config()

    return config_class()
