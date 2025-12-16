"""
Routes pour le calculateur automatique
"""

from flask import Blueprint, render_template, session, flash, redirect, url_for, jsonify, request, send_file, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import logging
import json
import csv
import base64
import os
from datetime import datetime
import pandas as pd

from app.services.metadata_manager import MetadataManager
from app.services.data_calculator import DataCalculator
from app.services.file_handler import save_upload_file
from app.services.auto_processor import AutoProcessor, AutoMappingConfig

bp = Blueprint('calculator', __name__, url_prefix='/calculator')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_metadata_from_session():
    """Helper pour récupérer les métadonnées de la session"""
    try:
        metadata_dict = session['metadata']
        print(f"[DEBUG] Type of metadata in session: {type(metadata_dict)}")
        print(f"[DEBUG] First 200 chars: {str(metadata_dict)[:200]}")
        
        if isinstance(metadata_dict, str):
            print("[DEBUG] Metadata is a string, deserializing...")
            metadata_dict = json.loads(metadata_dict)
        
        return MetadataManager.from_dict(metadata_dict)
    except Exception as e:
        print(f"[ERROR] Error in get_metadata_from_session: {e}")
        print(f"[ERROR] Type: {type(session.get('metadata'))}")
        raise


@bp.route('/')
def calculator_page():
    """Affiche le calculateur automatique"""
    # Vérifier si des métadonnées sont chargées
    if 'metadata' not in session:
        flash('Veuillez d\'abord charger les métadonnées', 'warning')
        return redirect(url_for('configuration.configuration_page'))
    
    return render_template('calculator.html')


@bp.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    """
    Upload un fichier Excel pour traitement
    
    Returns:
        JSON avec succès/erreur
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    try:
        # Vérifier le fichier
        if 'file' not in request.files:
            logger.warning("Tentative d'upload Excel sans fichier")
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            logger.warning("Tentative d'upload Excel avec nom vide")
            return jsonify({'error': 'Nom de fichier vide'}), 400
        
        # Vérifier l'extension
        if not any(file.filename.lower().endswith(ext) for ext in ['.xlsx', '.xls']):
            logger.warning(f"Type de fichier Excel invalide: {file.filename}")
            return jsonify({'error': 'Type de fichier invalide. Seuls les fichiers Excel (.xlsx, .xls) sont acceptés.'}), 400
        
        # Créer le répertoire de session avec chemin absolu
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder le fichier
        success, result, filename = save_upload_file(
            file,
            session_dir,
            ALLOWED_EXTENSIONS
        )
        
        if not success:
            logger.error(f"Échec sauvegarde Excel: {result}")
            return jsonify({'error': result}), 400
        
        filepath = result
        
        # Sauvegarder le chemin dans la session
        session['excel_file'] = str(filepath)
        session['excel_filename'] = filename
        
        logger.info(f"Fichier Excel uploadé avec succès: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'Fichier chargé avec succès',
            'filename': filename
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur upload Excel: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@bp.route('/api/get-sheets', methods=['GET'])
def get_excel_sheets():
    """
    Récupère la liste des onglets du fichier Excel uploadé

    Returns:
        JSON avec liste des onglets
    """
    if 'excel_file' not in session:
        return jsonify({'error': 'Aucun fichier uploadé'}), 400

    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400

    try:
        metadata = get_metadata_from_session()
        calculator = DataCalculator(metadata)

        filepath = session['excel_file']
        sheets = calculator.get_excel_sheets(filepath)

        logger.info(f"Onglets détectés: {sheets}")

        return jsonify({
            'success': True,
            'sheets': sheets,
            'count': len(sheets)
        }), 200

    except Exception as e:
        logger.error(f"Erreur récupération onglets: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/process-template', methods=['POST'])
def process_template():
    """
    Traite un fichier Excel

    Body JSON:
        {
            "sheet_name": "Premier Cycle",    # Onglet à traiter
            "mode": "normal",                 # "normal" ou "pivot" (TCD)
            "data_element_id": "xyz123",      # (Optionnel) Si mode pivot mono-DE
            "period": "2024"                  # (Optionnel) Période pour mode pivot
        }

    Returns:
        JSON avec statistiques et preview
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400

    if 'excel_file' not in session:
        return jsonify({'error': 'Aucun fichier uploadé'}), 400

    try:
        # Récupérer paramètres
        data = request.get_json() or {}
        sheet_name = data.get('sheet_name', 'Données')
        mode = data.get('mode', 'normal')
        data_element_id = data.get('data_element_id')  # Optionnel pour TCD multi-DE
        period = data.get('period', '2024')  # Période pour TCD

        # Mode pivot/TCD : data_element_id est maintenant optionnel
        # Si non fourni, les DE seront auto-détectés depuis la première colonne

        # Récupérer les services
        metadata = get_metadata_from_session()
        calculator = DataCalculator(metadata)

        filepath = session['excel_file']
        filename = session.get('excel_filename', 'unknown')

        logger.info(f"========================================")
        logger.info(f"MODE TEMPLATE - Traitement de {filename}")
        logger.info(f"Onglet: {sheet_name}, Mode: {mode}")
        logger.info(f"Period: {period}, DE ID: {data_element_id}")
        logger.info(f"========================================")

        # Traiter le fichier
        data_values, stats = calculator.process_template_excel(
            filepath,
            sheet_name=sheet_name,
            mode=mode,
            data_element_id=data_element_id,
            period=period
        )
        
        logger.info(f"Extraction terminée: {len(data_values)} valeurs générées")
        logger.info(f"Stats: {stats}")
        
        # Générer le payload
        payload = calculator.generate_dhis2_payload(data_values)
        
        # Valider
        valid, errors = calculator.validate_payload(payload)
        
        if not valid:
            logger.warning(f"Payload invalide: {errors}")
            return jsonify({
                'error': 'Payload invalide',
                'details': errors
            }), 400
        
        # Sauvegarder le payload dans la session avec chemin absolu
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        json_filename = f"DHIS2_Import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_filepath = session_dir / json_filename
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        session['json_file'] = str(json_filepath)
        session['json_filename'] = json_filename
        
        logger.info(f"Payload JSON généré: {json_filename} - {len(data_values)} valeurs")
        
        # Preview des premières lignes
        preview = data_values[:10]
        
        return jsonify({
            'success': True,
            'stats': stats,
            'preview': preview,
            'total_values': len(data_values),
            'json_filename': json_filename
        }), 200
        
    except ValueError as e:
        logger.error(f"Erreur validation traitement: {e}")
        return jsonify({'error': f'Validation échouée: {str(e)}'}), 400
    except KeyError as e:
        logger.error(f"Données manquantes dans Excel: {e}")
        return jsonify({'error': f'Élément introuvable dans les métadonnées: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Erreur traitement Excel: {e}", exc_info=True)
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@bp.route('/api/download-json', methods=['GET'])
def download_json():
    """
    Télécharge le fichier JSON généré
    
    Returns:
        Fichier JSON
    """
    if 'json_file' not in session:
        return jsonify({'error': 'Aucun fichier JSON disponible'}), 400
    
    try:
        filepath = session['json_file']
        filename = session.get('json_filename', 'dhis2_import.json')
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Erreur téléchargement JSON: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/download-csv-names', methods=['GET'])
def download_csv_names():
    """
    Télécharge un CSV au format dataValueSets avec les NOMS des métadonnées
    Colonnes: dataElementName, period, orgUnitName, categoryOptionComboName, value

    Utilise le payload JSON déjà généré, et résout les IDs → noms via les métadonnées en session.
    """
    if 'json_file' not in session:
        return jsonify({'error': 'Aucun fichier JSON disponible'}), 400

    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400

    try:
        # Charger payload
        json_filepath = session['json_file']
        with open(json_filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)

        data_values = content.get('dataValues', [])
        if not isinstance(data_values, list) or len(data_values) == 0:
            return jsonify({'error': 'Payload vide ou invalide'}), 400

        # Métadonnées
        metadata = get_metadata_from_session()

        # Dossier session
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        session_dir.mkdir(parents=True, exist_ok=True)

        # Nom de fichier CSV
        # Essayer de détecter la période dominante
        periods = [dv.get('period') for dv in data_values if dv.get('period')]
        period_hint = periods[0] if periods else datetime.now().strftime('%Y%m')
        csv_filename = f"dataValueSets_{period_hint}.csv"
        csv_filepath = session_dir / csv_filename

        # Écrire CSV avec noms
        headers = ['dataElementName', 'period', 'orgUnitName', 'categoryOptionComboName', 'value']
        with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for dv in data_values:
                de_id = dv.get('dataElement')
                ou_id = dv.get('orgUnit')
                coc_id = dv.get('categoryOptionCombo')
                value = dv.get('value')
                period = dv.get('period')

                de_name = metadata.data_elements_map.get(de_id, {}).get('name', de_id)
                ou_name = metadata.org_units_map.get(ou_id, {}).get('name', ou_id)
                coc_name = metadata.get_coc_display_name(coc_id) if coc_id else ''

                writer.writerow({
                    'dataElementName': de_name,
                    'period': period,
                    'orgUnitName': ou_name,
                    'categoryOptionComboName': coc_name,
                    'value': value,
                })

        return send_file(
            str(csv_filepath),
            as_attachment=True,
            download_name=csv_filename,
            mimetype='text/csv'
        )

    except Exception as e:
        logger.error(f"Erreur téléchargement CSV (noms): {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/preview-json', methods=['GET'])
def preview_json():
    """
    Retourne un aperçu du JSON généré
    
    Returns:
        JSON avec le contenu
    """
    if 'json_file' not in session:
        return jsonify({'error': 'Aucun fichier JSON disponible'}), 400
    
    try:
        filepath = session['json_file']
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Limiter à 20 dataValues pour le preview
        if 'dataValues' in content and len(content['dataValues']) > 20:
            preview_content = {
                'dataValues': content['dataValues'][:20],
                'total': len(content['dataValues']),
                'preview': True
            }
        else:
            preview_content = content
            preview_content['preview'] = False
        
        return jsonify(preview_content), 200
        
    except Exception as e:
        logger.error(f"Erreur preview JSON: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/clear', methods=['POST'])
def clear_data():
    """
    Efface les données du calculateur de la session

    Returns:
        JSON avec succès
    """
    session.pop('excel_file', None)
    session.pop('excel_filename', None)
    session.pop('json_file', None)
    session.pop('json_filename', None)
    session.pop('selected_dataset', None)
    session.pop('excel_columns', None)

    logger.info("Données du calculateur effacées")

    return jsonify({'success': True, 'message': 'Données effacées avec succès'}), 200


@bp.route('/api/get-dataset-info', methods=['POST'])
def get_dataset_info():
    """
    Retourne les informations complètes d'un dataset:
    - Catégories
    - Data elements
    - Period type

    Returns:
        JSON avec toutes les informations
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400

    try:
        data = request.get_json()
        dataset_id = data.get('dataset_id')

        if not dataset_id:
            return jsonify({'error': 'Dataset ID requis'}), 400

        metadata = get_metadata_from_session()

        # Récupérer le dataset
        dataset = next((ds for ds in metadata.datasets if ds['id'] == dataset_id), None)
        if not dataset:
            return jsonify({'error': 'Dataset introuvable'}), 404

        # Identifier les catégories requises
        required_cats = {}
        data_elements = []

        # Build DE to Groups map for efficiency
        de_groups_map = {}
        # data_element_groups est un Dict, pas une List
        for group_id, group in metadata.data_element_groups.items():
            group_name = group.get('name', '')
            for de_ref in group.get('dataElements', []):
                de_ref_id = de_ref.get('id') if isinstance(de_ref, dict) else de_ref
                if de_ref_id not in de_groups_map:
                    de_groups_map[de_ref_id] = []
                de_groups_map[de_ref_id].append({'id': group_id, 'name': group_name})

        for elem in dataset.get('dataSetElements', []):
            de_id = elem['dataElement']['id']
            de = metadata.data_elements_map.get(de_id)
            if not de:
                continue

            # Ajouter le data element
            data_elements.append({
                'id': de_id,
                'name': de.get('name', 'N/A'),
                'groups': de_groups_map.get(de_id, [])
            })

            # Récupérer les catégories de ce data element
            cc_id = de.get('categoryCombo', {}).get('id')
            if not cc_id:
                continue

            cc = metadata.cat_combos.get(cc_id)
            if not cc or cc.get('name') == 'default':
                continue

            for cat in cc.get('categories', []):
                cat_id = cat['id']
                if cat_id not in required_cats:
                    cat_obj = metadata.categories.get(cat_id)
                    if cat_obj:
                        required_cats[cat_id] = {
                            'id': cat_id,
                            'name': cat_obj['name']
                        }

        # Trier les data elements par nom
        data_elements.sort(key=lambda x: x['name'])

        # Sauvegarder le dataset sélectionné
        session['selected_dataset'] = dataset_id

        return jsonify({
            'success': True,
            'categories': list(required_cats.values()),
            'has_categories': len(required_cats) > 0,
            'data_elements': data_elements,
            'period_type': dataset.get('periodType', 'Monthly')
        }), 200

    except Exception as e:
        logger.error(f"Erreur récupération infos dataset: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/send-to-dhis2', methods=['POST'])
def send_to_dhis2():
    """
    Sends the generated JSON payload to DHIS2.
    Uses credentials stored in session.
    """
    if 'json_file' not in session:
        return jsonify({'error': 'Aucun fichier JSON généré'}), 400
        
    if 'dhis2_auth' not in session or 'dhis2_url' not in session:
        return jsonify({'error': 'Non connecté à DHIS2 via API'}), 400
        
    try:
        # Load JSON payload
        filepath = session['json_file']
        with open(filepath, 'r', encoding='utf-8') as f:
            payload = json.load(f)
            
        # Get credentials
        auth_b64 = session['dhis2_auth']
        url = session['dhis2_url']
        username = session['dhis2_username']
        
        # Décoder les credentials depuis base64
        credentials = base64.b64decode(auth_b64).decode('utf-8')
        _, password = credentials.split(':', 1)
        
        from app.services.dhis2_client import DHIS2Client
        
        # Initialize client
        client = DHIS2Client(
            url=url,
            username=username,
            password=password
        )
        
        # Push data
        success, response, error = client.push_data_values(payload)
        
        if success:
            logger.info(f"Data pushed to DHIS2 successfully: {response}")
            return jsonify({
                'success': True,
                'message': 'Données envoyées avec succès à DHIS2',
                'details': response
            })
        else:
            logger.error(f"Failed to push data to DHIS2: {error}")
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'envoi à DHIS2',
                'details': response or error
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending to DHIS2: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/get-metadata-filters', methods=['GET'])
def get_metadata_filters():
    """
    Returns metadata filters:
    - Organisation Unit Groups
    - Organisation Unit Levels
    - Data Element Groups
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
        
    try:
        metadata = get_metadata_from_session()
        
        # Convertir les dicts en listes triées
        # S'assurer que ce sont bien des dicts
        org_groups = metadata.org_unit_groups if isinstance(metadata.org_unit_groups, dict) else {}
        de_groups = metadata.data_element_groups if isinstance(metadata.data_element_groups, dict) else {}
        
        org_groups_list = [{'id': k, 'name': v.get('name', '')} for k, v in org_groups.items()]
        de_groups_list = [{'id': k, 'name': v.get('name', '')} for k, v in de_groups.items()]
        
        return jsonify({
            'success': True,
            'org_unit_groups': sorted(org_groups_list, key=lambda x: x['name']),
            'org_unit_levels': sorted(metadata.org_unit_levels, key=lambda x: x.get('level', 0)),
            'data_element_groups': sorted(de_groups_list, key=lambda x: x['name'])
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching metadata filters: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/analyze-file', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier fourni'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            from app.services.ai_analyzer import AIAnalysisService
            analyzer = AIAnalysisService()
            result = analyzer.analyze_excel(filepath)
            
            # Add success flag if not present
            if 'success' not in result:
                result['success'] = True
                
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'})

@bp.route('/api/extract-pivoted-data-elements', methods=['POST'])
def extract_pivoted_data_elements():
    """
    Analyse un fichier Excel au format pivoté et extrait les data elements
    avec leurs sections
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Récupérer les métadonnées si disponibles
            metadata = None
            if 'metadata' in session:
                try:
                    metadata = get_metadata_from_session().to_dict()
                except:
                    pass
            
            from app.services.ai_analyzer import AIAnalysisService
            analyzer = AIAnalysisService()
            result = analyzer.extract_pivoted_data_elements(filepath, metadata)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Erreur extraction pivoted DE: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'}), 400

@bp.route('/pivoted')
def pivoted_mapping_page():
    """Page de mapping pour format pivoté"""
    if 'metadata' not in session:
        flash('Veuillez charger les métadonnées DHIS2 avant de continuer', 'warning')
        return redirect(url_for('dashboard.dashboard_page'))
    return render_template('calculator_pivoted.html')

@bp.route('/api/get-dhis2-data-elements')
def get_dhis2_data_elements():
    """Retourne la liste de tous les Data Elements DHIS2"""
    if 'metadata' not in session:
        return jsonify({'success': False, 'error': 'Métadonnées non chargées'}), 400
    
    try:
        metadata = get_metadata_from_session()
        data_elements = []
        
        for de_id, de in metadata.data_elements_map.items():
            data_elements.append({
                'id': de_id,
                'name': de.get('name') or de.get('displayName', ''),
                'code': de.get('code', ''),
                'shortName': de.get('shortName', '')
            })
        
        # Sort by name
        data_elements.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            'success': True,
            'data_elements': data_elements,
            'count': len(data_elements)
        })
    except Exception as e:
        logger.error(f"Erreur récupération DE: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/get-filtered-org-units', methods=['POST'])
def get_filtered_org_units():
    """
    Returns Organisation Units filtered by Group and/or Level.
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
        
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        level = data.get('level')
        
        metadata = get_metadata_from_session()
        
        # Start with all org units (convert map to list)
        filtered_ous = list(metadata.org_units_map.values())
        
        # Filter by Group
        if group_id:
            group_ous = metadata.get_org_units_by_group(group_id)
            group_ou_ids = set(ou['id'] for ou in group_ous)
            filtered_ous = [ou for ou in filtered_ous if ou['id'] in group_ou_ids]
            
        # Filter by Level
        if level:
            level = int(level)
            filtered_ous = [ou for ou in filtered_ous if ou.get('level') == level]
            
        # Sort by name
        filtered_ous.sort(key=lambda x: x['name'])
        
        # Limit results if too many (e.g. > 1000) to avoid browser crash
        if len(filtered_ous) > 1000:
            filtered_ous = filtered_ous[:1000]
            
        return jsonify({
            'success': True,
            'org_units': [{'id': ou['id'], 'name': ou['name']} for ou in filtered_ous],
            'count': len(filtered_ous)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching filtered org units: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# ROUTES MODE AUTOMATIQUE (TCD vers Template DHIS2)
# =============================================================================

@bp.route('/api/upload-template', methods=['POST'])
def upload_template():
    """
    Upload un template DHIS2 pour le mode automatique.
    
    Returns:
        JSON avec filepath et infos du template
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Format non supporté (xlsx/xls requis)'}), 400
    
    try:
        # Créer le répertoire de session
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder le fichier
        filename = secure_filename(file.filename)
        filepath = session_dir / f"template_{filename}"
        file.save(str(filepath))
        
        # Sauvegarder le chemin en session
        session['template_file'] = str(filepath)
        session['template_filename'] = filename
        
        # Lire le fichier pour avoir des infos basiques et extraire les orgs
        df_full = pd.read_excel(filepath, sheet_name=0, header=5)
        
        # Extraire les organisations uniques depuis la colonne orgUnitName avec leurs codes
        organisations_uniques = []
        organisations_avec_codes = {}  # {nom: code}
        
        if 'orgUnitName' in df_full.columns:
            organisations_uniques = sorted([str(v) for v in df_full['orgUnitName'].dropna().unique() if str(v) not in ['nan', '', 'None']])
            
            # Extraire aussi les codes si la colonne existe
            if 'orgUnitCode' in df_full.columns:
                for _, row in df_full.iterrows():
                    nom = str(row.get('orgUnitName', '')).strip()
                    code = str(row.get('orgUnitCode', '')).strip()
                    if nom and code and nom != 'nan' and code != 'nan':
                        organisations_avec_codes[nom] = code
        
        # Alternative: si orgUnitName n'existe pas, chercher d'autres colonnes possibles
        if not organisations_uniques:
            for col in ['orgUnitName', 'Organisation', 'Établissement', 'Etablissement']:
                if col in df_full.columns:
                    organisations_uniques = sorted([str(v) for v in df_full[col].dropna().unique() if str(v) not in ['nan', '', 'None']])
                    if organisations_uniques:
                        break
        
        # Construire un dictionnaire {section: [data_elements]}
        sections_de = {}
        if 'dataElementName' in df_full.columns:
            # Trouver la colonne de section (généralement première colonne)
            section_col = df_full.columns[0] if len(df_full.columns) > 0 else None
            
            for idx, row in df_full.iterrows():
                section = str(row.get(section_col, '')).strip()
                de_name = str(row.get('dataElementName', '')).strip()
                
                if section and de_name and section != 'nan' and de_name != 'nan':
                    if section not in sections_de:
                        sections_de[section] = []
                    if de_name not in sections_de[section]:
                        sections_de[section].append(de_name)
        
        # Sauvegarder en session
        session['template_orgs'] = organisations_uniques
        session['template_orgs_codes'] = organisations_avec_codes
        session['template_sections_de'] = sections_de
        
        logger.info(f"Template uploadé: {filename}, {len(organisations_uniques)} organisations, {len(sections_de)} sections trouvées")
        
        return jsonify({
            'success': True,
            'filepath': str(filepath),
            'filename': filename,
            'rows': len(df_full),
            'orgs': len(organisations_uniques),
            'organisations_uniques': organisations_uniques,
            'organisations_avec_codes': organisations_avec_codes,
            'sections_de': sections_de
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur upload template: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/auto/analyze-tcd', methods=['POST'])
def analyze_tcd_auto():
    """
    Analyse un fichier TCD pour le mode automatique.
    
    Returns:
        JSON avec structure du fichier (onglets, colonnes, etc.)
    """
    if 'excel_file' not in session:
        return jsonify({'error': 'Aucun fichier TCD uploadé'}), 400
    
    try:
        processor = AutoProcessor(None)  # Pas besoin de metadata pour l'analyse
        filepath = session['excel_file']
        
        result = processor.analyze_tcd_file(filepath)
        
        if result['success']:
            session['tcd_analysis'] = result
            logger.info(f"TCD analysé: {result['sheet_count']} onglets")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erreur analyse TCD auto: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/auto/extract-tcd-values', methods=['POST'])
def extract_tcd_values():
    """
    Extrait les valeurs uniques d'une colonne spécifique du TCD.
    
    Body JSON:
        {
            "sheet_name": "Feuille1",
            "column_name": "CYCLE"
        }
    
    Returns:
        JSON avec valeurs uniques
    """
    if 'excel_file' not in session:
        return jsonify({'error': 'Aucun fichier TCD uploadé'}), 400
    
    try:
        data = request.get_json() or {}
        sheet_name = data.get('sheet_name')
        column_name = data.get('column_name')
        
        if not sheet_name or not column_name:
            return jsonify({'error': 'Paramètres manquants'}), 400
        
        filepath = session['excel_file']
        
        # Lire le TCD avec header à la ligne 0 (tout le fichier)
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)
        
        # Extraire les valeurs uniques de la colonne
        if column_name not in df.columns:
            return jsonify({'error': f'Colonne {column_name} introuvable'}), 400
        
        valeurs_uniques = sorted([str(v) for v in df[column_name].dropna().unique() if str(v) not in ['nan', '', 'None']])
        
        # Extraire aussi les établissements avec leurs codes
        etablissements_uniques = []
        etablissements_avec_codes = {}
        col_etab = 'NOM_ETAB'
        col_code = data.get('column_code', 'CODE_ETAB')  # Utiliser la colonne sélectionnée par l'utilisateur
        
        if col_etab in df.columns:
            etablissements_uniques = sorted([str(v) for v in df[col_etab].dropna().unique() if str(v) not in ['nan', '', 'None']])
            
            if col_code in df.columns:
                for _, row in df.iterrows():
                    nom = str(row.get(col_etab, '')).strip()
                    code = str(row.get(col_code, '')).strip()
                    if nom and code and nom != 'nan' and code != 'nan':
                        etablissements_avec_codes[nom] = code
        
        logger.info(f"Valeurs extraites de {column_name}: {len(valeurs_uniques)} valeurs, {len(etablissements_uniques)} établissements, {len(etablissements_avec_codes)} avec code")
        
        return jsonify({
            'success': True,
            'valeurs': valeurs_uniques,
            'etablissements_uniques': etablissements_uniques,
            'etablissements_avec_codes': etablissements_avec_codes
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur extraction valeurs TCD: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/api/auto/process', methods=['POST'])
def process_auto():
    """
    Traite un TCD avec un template DHIS2 de manière automatique.
    
    Body JSON:
        {
            "template_file": "path_to_template.xlsx",
            "tcd_sheet": "cycle",
            "col_data_element": "CYCLE",
            "period": "2024",
            "config": {
                "etablissements_patterns": {
                    "CPSP": "Centre Privé de Santé Publique",
                    "ESEG": "Economie et de Gestion"
                },
                "data_elements_manuels": {
                    "1er cycle": ["Cycle", "1er cycle"],
                    "2ème cycle": ["Cycle", "2e cycle"]
                }
            }
        }
    
    Returns:
        JSON avec dataValues et statistiques
    """
    if 'metadata' not in session:
        return jsonify({'error': 'Métadonnées non chargées'}), 400
    
    if 'template_file' not in session:
        return jsonify({'error': 'Template non uploadé'}), 400
    
    if 'excel_file' not in session:
        return jsonify({'error': 'Aucun fichier TCD uploadé'}), 400
    
    try:
        data = request.get_json() or {}
        
        # Récupérer le template depuis la session
        template_file = session['template_file']
        
        # Paramètres obligatoires
        tcd_sheet = data.get('tcd_sheet')
        col_data_element = data.get('col_data_element')
        period = data.get('period')
        config_data = data.get('config', {})
        
        if not all([tcd_sheet, col_data_element, period]):
            return jsonify({'error': 'Paramètres manquants'}), 400
        
        # Récupérer metadata
        metadata = get_metadata_from_session()
        
        # Construire la configuration
        config = AutoMappingConfig()
        config.etablissements_patterns = config_data.get('etablissements_patterns', {})
        
        # Convertir data_elements_manuels (list → tuple)
        de_manuels_data = config_data.get('data_elements_manuels', {})
        config.data_elements_manuels = {
            k: tuple(v) if isinstance(v, list) else v
            for k, v in de_manuels_data.items()
        }
        
        # Créer le processeur
        processor = AutoProcessor(metadata, config)
        
        # Charger template
        logger.info(f"Chargement template: {template_file}")
        processor.load_template(template_file)
        
        # Construire mappings
        processor.build_etablissements_mapping()
        processor.build_index_recherche()
        
        # Charger TCD
        tcd_filepath = session['excel_file']
        logger.info(f"Chargement TCD: {tcd_filepath}, sheet: {tcd_sheet}")
        processor.load_tcd(tcd_filepath, tcd_sheet)
        
        # Traiter
        data_values, stats = processor.process_tcd_sheet(col_data_element, period)
        
        if len(data_values) == 0:
            return jsonify({
                'error': 'Aucune valeur générée',
                'stats': stats.to_dict()
            }), 400
        
        # Générer le payload DHIS2
        calculator = DataCalculator(metadata)
        payload = calculator.generate_dhis2_payload(data_values)
        
        # Valider
        valid, errors = calculator.validate_payload(payload)
        
        if not valid:
            logger.warning(f"Payload invalide: {errors}")
            return jsonify({
                'error': 'Payload invalide',
                'details': errors
            }), 400
        
        # Sauvegarder
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / 'sessions' / session.sid
        json_filename = f"DHIS2_Import_Auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_filepath = session_dir / json_filename
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        session['json_file'] = str(json_filepath)
        session['json_filename'] = json_filename
        
        logger.info(f"Payload JSON auto généré: {json_filename} - {len(data_values)} valeurs")
        
        # Preview
        preview = data_values[:10]
        
        return jsonify({
            'success': True,
            'stats': stats.to_dict(),
            'preview': preview,
            'total_values': len(data_values),
            'json_filename': json_filename
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur traitement auto: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
