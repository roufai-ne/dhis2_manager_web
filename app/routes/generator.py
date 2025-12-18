"""
Routes pour le générateur de modèles Excel
"""

from flask import Blueprint, render_template, session, flash, redirect, url_for, jsonify, request, send_file
from pathlib import Path
import logging
from datetime import datetime

from app.services.metadata_manager import MetadataManager
from app.services.template_generator import TemplateGenerator, TemplateConfig
from app.services.excel_service import ExcelService
from app.utils.activity_logger import log_activity

bp = Blueprint('generator', __name__, url_prefix='/generator')
logger = logging.getLogger(__name__)


@bp.route('/')
def generator_page():
    """Affiche le générateur de modèles"""
    # Vérifier si des métadonnées sont chargées
    if 'metadata' not in session:
        flash('Veuillez d\'abord charger les métadonnées', 'warning')
        return redirect(url_for('configuration.configuration_page'))
    
    try:
        # Récupérer le metadata manager
        metadata = MetadataManager.from_dict(session['metadata'])
        
        # Obtenir la liste des datasets
        datasets = [
            {
                'id': ds.get('id'),
                'name': ds.get('name'),
                'code': ds.get('code', ''),
                'shortName': ds.get('shortName'),
                'periodType': ds.get('periodType', 'Monthly')
            }
            for ds in metadata.datasets
        ]
        
        return render_template(
            'generator.html',
            datasets=datasets
        )
        
    except Exception as e:
        logger.error(f"Erreur affichage générateur: {e}")
        flash('Erreur lors du chargement du générateur', 'error')
        return redirect(url_for('main.index'))


@bp.route('/api/org-tree', methods=['GET'])
def get_org_tree():
    """
    Retourne l'arborescence des organisations pour jsTree
    
    Returns:
        JSON avec l'arbre des organisations
    """
    if 'metadata' not in session:
        logger.warning("Tentative d'accès à l'arbre sans métadonnées")
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        tree = metadata.get_org_tree()
        
        logger.info(f"Arbre des organisations récupéré: {len(tree)} nœuds")
        return jsonify(tree), 200
        
    except Exception as e:
        logger.error(f"Erreur récupération arbre: {e}", exc_info=True)
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@bp.route('/api/dataset/<dataset_id>/info', methods=['GET'])
def get_dataset_info(dataset_id: str):
    """
    Retourne les informations d'un dataset
    
    Args:
        dataset_id: ID du dataset
        
    Returns:
        JSON avec les infos
    """
    if 'metadata' not in session:
        logger.warning(f"Tentative d'accès aux infos du dataset {dataset_id} sans métadonnées")
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        generator = TemplateGenerator(metadata)
        
        info = generator.get_dataset_info(dataset_id)
        
        if not info:
            logger.warning(f"Dataset introuvable: {dataset_id}")
            return jsonify({'error': f'Dataset introuvable: {dataset_id}'}), 404
        
        logger.info(f"Infos du dataset {dataset_id} récupérées")
        return jsonify(info), 200
        
    except Exception as e:
        logger.error(f"Erreur récupération info dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/generate', methods=['POST'])
def generate_template():
    """
    Génère et télécharge un template Excel
    
    Body JSON:
        {
            "org_unit_ids": ["id1", "id2"],
            "dataset_id": "ds_id",
            "period": "2024",
            "period_type": "Yearly"
        }
        
    Returns:
        Fichier Excel ou erreur JSON
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        # Récupérer les paramètres
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        org_unit_ids = data.get('org_unit_ids', [])
        dataset_id = data.get('dataset_id')
        period = data.get('period')
        period_type = data.get('period_type', 'Yearly')
        
        # Validation basique
        if not org_unit_ids:
            logger.warning("Tentative de génération sans organisations")
            return jsonify({'error': 'Sélectionnez au moins une organisation'}), 400
        
        if not dataset_id:
            logger.warning("Tentative de génération sans dataset")
            return jsonify({'error': 'Sélectionnez un dataset'}), 400
        
        if not period:
            logger.warning("Tentative de génération sans période")
            return jsonify({'error': 'Entrez une période'}), 400
        
        logger.info(f"Génération template - Dataset: {dataset_id}, Période: {period}, Orgs: {len(org_unit_ids)}")
        
        # Créer la configuration
        config = TemplateConfig(
            org_unit_ids=org_unit_ids,
            dataset_id=dataset_id,
            period=period,
            period_type=period_type
        )
        
        # Récupérer les services
        metadata = MetadataManager.from_dict(session['metadata'])
        generator = TemplateGenerator(metadata)
        excel_service = ExcelService()
        
        # Valider la configuration
        valid, errors = generator.validate_config(config)
        if not valid:
            logger.warning(f"Configuration invalide: {errors}")
            return jsonify({
                'error': 'Configuration invalide',
                'details': errors
            }), 400
        
        # Générer le template
        df, stats = generator.generate_template(config)
        
        logger.info(f"Template généré avec succès: {stats}")
        
        # Créer le répertoire de session avec chemin absolu
        import os
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom du fichier
        dataset_name = stats.get('dataset_name', 'dataset').replace(' ', '_')
        filename = f"Template_{dataset_name}_{period}.xlsx"
        filepath = session_dir / filename
        
        # Créer le fichier Excel
        excel_metadata = {
            'dataset_name': stats.get('dataset_name'),
            'period': period,
            'org_units': stats.get('org_units'),
            'total_rows': stats.get('total_rows')
        }
        
        excel_service.create_template_excel(
            df=df,
            filepath=str(filepath),
            metadata=excel_metadata,
            protect_technical=True
        )
        
        logger.info(f"Template généré: {filename} ({stats.get('total_rows')} lignes)")
        log_activity(f"Génération template Excel - Dataset: {dataset_name}, Période: {period}, Organisations: {len(org_unit_ids)}, Lignes: {stats.get('total_rows')}", 'info')
        
        # Retourner le fichier
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except ValueError as e:
        logger.error(f"Erreur validation génération: {e}")
        return jsonify({'error': f'Validation échouée: {str(e)}'}), 400
    except KeyError as e:
        logger.error(f"Données manquantes: {e}")
        return jsonify({'error': f'Élément introuvable: {str(e)}'}), 404
    except Exception as e:
        logger.error(f"Erreur génération template: {e}", exc_info=True)
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@bp.route('/api/generate-csv-names', methods=['POST'])
def generate_csv_names():
    """
    Génère et télécharge un CSV avec colonnes basées sur les noms

    Body JSON:
        {
            "org_unit_ids": ["id1", "id2"],
            "dataset_id": "ds_id",
            "period": "2024",
            "period_type": "Yearly"
        }

    Returns:
        Fichier CSV ou erreur JSON
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400

        org_unit_ids = data.get('org_unit_ids', [])
        dataset_id = data.get('dataset_id')
        period = data.get('period')
        period_type = data.get('period_type', 'Yearly')

        if not org_unit_ids:
            return jsonify({'error': 'Sélectionnez au moins une organisation'}), 400
        if not dataset_id:
            return jsonify({'error': 'Sélectionnez un dataset'}), 400
        if not period:
            return jsonify({'error': 'Entrez une période'}), 400

        config = TemplateConfig(
            org_unit_ids=org_unit_ids,
            dataset_id=dataset_id,
            period=period,
            period_type=period_type
        )

        metadata = MetadataManager.from_dict(session['metadata'])
        generator = TemplateGenerator(metadata)

        valid, errors = generator.validate_config(config)
        if not valid:
            return jsonify({'error': 'Configuration invalide', 'details': errors}), 400

        # Générer DataFrame avec colonnes noms
        df, stats = generator.generate_names_template(config)

        # Créer le répertoire de session
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        session_dir.mkdir(parents=True, exist_ok=True)

        dataset_name = stats.get('dataset_name', 'dataset').replace(' ', '_')
        filename = f"dataValueSets_{dataset_name}_{period}_names.csv"
        filepath = session_dir / filename

        # Sauvegarder en CSV (UTF-8 avec BOM pour Excel)
        df.to_csv(str(filepath), index=False, encoding='utf-8-sig')

        logger.info(f"CSV (noms) généré: {filename} ({stats.get('total_rows')} lignes)")
        log_activity(f"Génération CSV noms - Dataset: {dataset_name}, Période: {period}, Organisations: {len(org_unit_ids)}, Lignes: {stats.get('total_rows')}", 'info')

        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )

    except ValueError as e:
        logger.error(f"Erreur validation génération CSV: {e}")
        return jsonify({'error': f'Validation échouée: {str(e)}'}), 400
    except KeyError as e:
        logger.error(f"Données manquantes: {e}")
        return jsonify({'error': f'Élément introuvable: {str(e)}'}), 404
    except Exception as e:
        logger.error(f"Erreur génération CSV: {e}", exc_info=True)
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@bp.route('/api/period-examples/<period_type>', methods=['GET'])
def get_period_examples(period_type: str):
    """
    Retourne des exemples de format de période
    
    Args:
        period_type: Type de période
        
    Returns:
        JSON avec exemples
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        generator = TemplateGenerator(metadata)
        
        examples = generator.get_period_examples(period_type)
        
        return jsonify({'examples': examples}), 200
        
    except Exception as e:
        logger.error(f"Erreur récupération exemples: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/org-unit-groups', methods=['GET'])
def get_org_unit_groups():
    """Retourne la liste des groupes d'unités d'organisation"""
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        groups = [
            {'id': g['id'], 'name': g['name']}
            for g in metadata.org_unit_groups.values()
        ]
        # Trier par nom
        groups.sort(key=lambda x: x['name'])
        return jsonify(groups), 200
    except Exception as e:
        logger.error(f"Erreur récupération groupes UO: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/org-unit-levels', methods=['GET'])
def get_org_unit_levels():
    """Retourne la liste des niveaux d'unités d'organisation"""
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        levels = [
            {'level': l['level'], 'name': l['name']}
            for l in metadata.org_unit_levels
        ]
        return jsonify(levels), 200
    except Exception as e:
        logger.error(f"Erreur récupération niveaux UO: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/org-units/by-group/<group_id>', methods=['GET'])
def get_org_units_by_group(group_id):
    """Retourne les IDs des UO appartenant à un groupe"""
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        org_units = metadata.get_org_units_by_group(group_id)
        ids = [ou['id'] for ou in org_units]
        return jsonify({'ids': ids}), 200
    except Exception as e:
        logger.error(f"Erreur récupération UO par groupe {group_id}: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/org-units/by-level/<int:level>', methods=['GET'])
def get_org_units_by_level(level):
    """Retourne les IDs des UO à un niveau spécifique"""
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = MetadataManager.from_dict(session['metadata'])
        org_units = metadata.get_org_units_by_level(level)
        ids = [ou['id'] for ou in org_units]
        return jsonify({'ids': ids}), 200
    except Exception as e:
        logger.error(f"Erreur récupération UO par niveau {level}: {e}")
        return jsonify({'error': str(e)}), 500
