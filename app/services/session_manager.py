"""
Service de gestion des sessions
================================
Gestion du cycle de vie des sessions et nettoyage automatique
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_session_dir(session_id: str) -> Path:
    """Retourne le chemin du dossier de la session"""
    return Path(f"sessions/{session_id}")


def ensure_session_dir(session_id: str) -> Path:
    """Crée le dossier session s'il n'existe pas"""
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def cleanup_session_files(session_id: str) -> bool:
    """
    Nettoie les fichiers d'une session spécifique
    
    Args:
        session_id: Identifiant de la session
        
    Returns:
        True si le nettoyage a réussi, False sinon
    """
    try:
        session_dir = get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.info(f"Session nettoyée: {session_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage de la session {session_id}: {e}")
        return False


def cleanup_old_sessions(max_age_hours: int = 2) -> int:
    """
    Nettoie les sessions expirées
    
    Args:
        max_age_hours: Âge maximum des sessions en heures
        
    Returns:
        Nombre de sessions nettoyées
    """
    sessions_dir = Path("sessions")
    if not sessions_dir.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cleaned_count = 0
    
    try:
        for session_dir in sessions_dir.iterdir():
            if session_dir.is_dir():
                # Vérifier la date de modification
                try:
                    mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
                    if mtime < cutoff:
                        shutil.rmtree(session_dir)
                        cleaned_count += 1
                        logger.info(f"Session expirée nettoyée: {session_dir.name}")
                except Exception as e:
                    logger.error(f"Erreur lors du nettoyage de {session_dir.name}: {e}")
                    
        if cleaned_count > 0:
            logger.info(f"Total de {cleaned_count} session(s) expirée(s) nettoyée(s)")
            
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des sessions: {e}")
    
    return cleaned_count


def get_session_size(session_id: str) -> int:
    """
    Calcule la taille totale d'une session en octets
    
    Args:
        session_id: Identifiant de la session
        
    Returns:
        Taille en octets
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        return 0
    
    total_size = 0
    try:
        for path in session_dir.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
    except Exception as e:
        logger.error(f"Erreur lors du calcul de la taille de la session {session_id}: {e}")
    
    return total_size


def get_session_info(session_id: str) -> dict:
    """
    Retourne les informations sur une session
    
    Args:
        session_id: Identifiant de la session
        
    Returns:
        Dictionnaire avec les informations
    """
    session_dir = get_session_dir(session_id)
    
    if not session_dir.exists():
        return {
            'exists': False,
            'session_id': session_id
        }
    
    try:
        stat = session_dir.stat()
        files = list(session_dir.rglob('*'))
        file_count = sum(1 for f in files if f.is_file())
        
        return {
            'exists': True,
            'session_id': session_id,
            'created_at': datetime.fromtimestamp(stat.st_ctime),
            'modified_at': datetime.fromtimestamp(stat.st_mtime),
            'size': get_session_size(session_id),
            'file_count': file_count
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos de session {session_id}: {e}")
        return {
            'exists': True,
            'session_id': session_id,
            'error': str(e)
        }
