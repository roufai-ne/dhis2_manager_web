"""
Utilitaire de logging enrichi avec informations utilisateur
"""

import logging
from flask import session, request
from functools import wraps


def get_user_context():
    """Récupère le contexte utilisateur actuel"""
    user = session.get('admin_username') or session.get('dhis2_username') or 'anonymous'
    ip = request.remote_addr if request else 'unknown'
    return user, ip


def log_activity(message, level='info'):
    """
    Log une activité avec contexte utilisateur
    
    Args:
        message: Message à logger
        level: Niveau de log (info, warning, error, debug)
    """
    from flask import current_app
    
    user, ip = get_user_context()
    formatted_message = f"[user:{user}] [ip:{ip}] {message}"
    
    logger = current_app.logger
    
    if level == 'info':
        logger.info(formatted_message)
    elif level == 'warning':
        logger.warning(formatted_message)
    elif level == 'error':
        logger.error(formatted_message)
    elif level == 'debug':
        logger.debug(formatted_message)
    else:
        logger.info(formatted_message)


def log_activity_decorator(activity_name):
    """
    Décorateur pour logger automatiquement les activités
    
    Usage:
        @log_activity_decorator("Upload fichier Excel")
        def upload_file():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user, ip = get_user_context()
            
            # Log début d'activité
            log_activity(f"Début: {activity_name}", 'info')
            
            try:
                result = f(*args, **kwargs)
                
                # Log succès
                log_activity(f"Succès: {activity_name}", 'info')
                
                return result
            except Exception as e:
                # Log erreur
                log_activity(f"Erreur: {activity_name} - {str(e)}", 'error')
                raise
        
        return decorated_function
    return decorator
