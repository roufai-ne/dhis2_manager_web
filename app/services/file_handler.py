"""
Service de gestion des fichiers uploadés
=========================================
Gestion des uploads, validation et sauvegarde temporaire
"""

import os
import json
import logging
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from typing import Tuple, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Vérifie si l'extension du fichier est autorisée
    
    Args:
        filename: Nom du fichier
        allowed_extensions: Set des extensions autorisées
        
    Returns:
        True si autorisé, False sinon
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def validate_json_structure(data: Dict) -> Tuple[bool, list]:
    """
    Valide la structure d'un fichier JSON DHIS2
    
    Args:
        data: Dictionnaire contenant les données JSON
        
    Returns:
        Tuple (valide, liste d'erreurs)
    """
    errors = []
    
    # Vérifier que c'est un dictionnaire
    if not isinstance(data, dict):
        errors.append("Le fichier JSON doit contenir un objet (dictionnaire)")
        return False, errors
    
    # Vérifier les champs DHIS2 attendus
    expected_fields = [
        'organisationUnits',
        'dataSets',
        'dataElements'
    ]
    
    missing_fields = []
    for field in expected_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        errors.append(f"Champs manquants : {', '.join(missing_fields)}")
    
    # Vérifier que les champs sont des listes
    for field in expected_fields:
        if field in data and not isinstance(data[field], list):
            errors.append(f"Le champ '{field}' doit être une liste")
    
    # Vérifier qu'il y a au moins des données
    if 'organisationUnits' in data and len(data['organisationUnits']) == 0:
        errors.append("Aucune organisation trouvée")
    
    if 'dataSets' in data and len(data['dataSets']) == 0:
        errors.append("Aucun dataset trouvé")
    
    return len(errors) == 0, errors


def save_upload_file(
    file: FileStorage,
    session_dir: Path,
    allowed_extensions: set,
    max_size: int = 50 * 1024 * 1024  # 50 MB
) -> Tuple[bool, str, Optional[str]]:
    """
    Sauvegarde un fichier uploadé
    
    Args:
        file: Fichier uploadé (Werkzeug FileStorage)
        session_dir: Répertoire de la session
        allowed_extensions: Extensions autorisées
        max_size: Taille maximale en octets
        
    Returns:
        Tuple (succès, chemin_ou_erreur, nom_fichier)
    """
    if not file:
        return False, "Aucun fichier fourni", None
    
    if file.filename == '':
        return False, "Nom de fichier vide", None
    
    # Vérifier l'extension
    if not allowed_file(file.filename, allowed_extensions):
        return False, f"Extension non autorisée. Extensions valides: {', '.join(allowed_extensions)}", None
    
    # Sécuriser le nom de fichier
    filename = secure_filename(file.filename)
    
    # Créer le chemin complet
    filepath = session_dir / filename
    
    try:
        # Sauvegarder le fichier
        file.save(str(filepath))
        
        # Vérifier la taille
        file_size = filepath.stat().st_size
        if file_size > max_size:
            filepath.unlink()  # Supprimer le fichier
            return False, f"Fichier trop volumineux ({file_size / 1024 / 1024:.1f} MB). Maximum: {max_size / 1024 / 1024} MB", None
        
        logger.info(f"Fichier sauvegardé: {filename} ({file_size / 1024:.1f} KB)")
        return True, str(filepath), filename
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")
        return False, f"Erreur lors de la sauvegarde: {str(e)}", None


def load_json_file(filepath: str) -> Tuple[bool, Dict, list]:
    """
    Charge et valide un fichier JSON
    
    Args:
        filepath: Chemin du fichier
        
    Returns:
        Tuple (succès, données, erreurs)
    """
    errors = []
    
    if not os.path.exists(filepath):
        return False, {}, ["Fichier introuvable"]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Valider la structure
        valid, validation_errors = validate_json_structure(data)
        if not valid:
            return False, {}, validation_errors
        
        return True, data, []
        
    except json.JSONDecodeError as e:
        errors.append(f"Erreur JSON à la ligne {e.lineno}: {e.msg}")
        return False, {}, errors
    except UnicodeDecodeError:
        errors.append("Erreur d'encodage. Le fichier doit être en UTF-8")
        return False, {}, errors
    except Exception as e:
        errors.append(f"Erreur lors de la lecture: {str(e)}")
        return False, {}, errors


def get_file_info(filepath: str) -> Dict:
    """
    Retourne les informations sur un fichier
    
    Args:
        filepath: Chemin du fichier
        
    Returns:
        Dictionnaire avec les infos
    """
    if not os.path.exists(filepath):
        return {'exists': False}
    
    try:
        stat = os.stat(filepath)
        return {
            'exists': True,
            'filename': os.path.basename(filepath),
            'size': stat.st_size,
            'size_mb': round(stat.st_size / 1024 / 1024, 2),
            'modified': stat.st_mtime
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos: {e}")
        return {'exists': True, 'error': str(e)}


def get_json_preview(filepath: str, max_items: int = 5) -> Dict:
    """
    Génère un aperçu d'un fichier JSON
    
    Args:
        filepath: Chemin du fichier
        max_items: Nombre maximum d'éléments à afficher par catégorie
        
    Returns:
        Dictionnaire avec l'aperçu
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        preview = {
            'structure': {}
        }
        
        # Compter les éléments principaux
        for key in ['organisationUnits', 'dataSets', 'dataElements', 
                    'categories', 'categoryOptions', 'categoryOptionCombos']:
            if key in data and isinstance(data[key], list):
                preview['structure'][key] = {
                    'count': len(data[key]),
                    'sample': [item.get('name', item.get('id', 'N/A')) 
                              for item in data[key][:max_items]]
                }
        
        return preview
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'aperçu: {e}")
        return {'error': str(e)}
