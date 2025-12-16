"""
Service de traitement pour le mode mapping avec data elements
==============================================================
Traite les fichiers Excel bruts avec mapping explicite des data elements

Supporte deux modes:
1. Mode Valeurs: Fichiers avec valeurs agrégées (colonnes de valeurs numériques)
2. Mode Comptage: Fichiers avec enregistrements individuels (compte automatiquement)
"""

import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd

logger = logging.getLogger(__name__)


def process_mapped_excel(
    metadata_manager,
    filepath: str,
    org_column: str,
    category_mapping: Dict[str, str],
    data_element_mapping: Dict[str, str],
    dataset_id: str,
    period: str,
    processing_mode: str = 'values',
    data_element_column: Optional[str] = None,
    value_to_de_mapping: Optional[Dict[str, str]] = None,
    fixed_org_unit: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> Tuple[List[Dict], Dict]:
    """
    Traite un fichier Excel avec mapping explicite des data elements

    Args:
        metadata_manager: Instance de MetadataManager
        filepath: Chemin du fichier Excel
        org_column: Nom de la colonne contenant les codes organisation (si mode colonne)
        category_mapping: Dict {category_id: column_name}
        data_element_mapping: Dict {data_element_id: column_name}
        dataset_id: ID du dataset
        period: Période (ex: "202401")
        processing_mode: 'values' (défaut) ou 'count' (comptage automatique)
        data_element_column: (Mode count) Colonne pour déterminer le DE
        value_to_de_mapping: (Mode count) Mapping valeur -> DE ID
        fixed_org_unit: (Optionnel) ID DHIS2 de l'org unit fixe si mode valeur fixe
        sheet_name: (Optionnel) Nom de l'onglet à lire

    Returns:
        Tuple (liste de dataValues, statistiques)
    """
    logger.info(f"Traitement mapping Excel: {filepath} - Mode: {processing_mode} - Sheet: {sheet_name}")

    # Lire le fichier
    try:
        if sheet_name:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
            logger.info(f"Fichier lu avec sheet '{sheet_name}': {len(df)} lignes, colonnes: {list(df.columns)}")
        else:
            df = pd.read_excel(filepath)
            logger.info(f"Fichier lu (premier sheet): {len(df)} lignes, colonnes: {list(df.columns)}")
    except Exception as e:
        logger.error(f"ERREUR lecture fichier: {str(e)}")
        raise ValueError(f"Erreur lecture fichier: {str(e)}")
    
    # Appliquer le fill down pour les cellules fusionnées (format TCD)
    logger.info(f"Application fill-down sur org_column={org_column}, categories={list(category_mapping.keys())}")
    df = _apply_fill_down(df, org_column, category_mapping)
    logger.info(f"Après fill-down: {len(df)} lignes")

    # Récupérer le dataset
    dataset = next((ds for ds in metadata_manager.datasets if ds['id'] == dataset_id), None)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} introuvable")

    # Router vers la fonction appropriée selon le mode
    if processing_mode == 'count':
        return _process_count_mode(
            metadata_manager, df, org_column, category_mapping,
            data_element_mapping, dataset_id, period,
            data_element_column, value_to_de_mapping, fixed_org_unit
        )
    else:
        return _process_values_mode(
            metadata_manager, df, org_column, category_mapping,
            data_element_mapping, dataset_id, period, fixed_org_unit
        )


def _process_values_mode(
    metadata_manager,
    df: pd.DataFrame,
    org_column: str,
    category_mapping: Dict[str, str],
    data_element_mapping: Dict[str, str],
    dataset_id: str,
    period: str,
    fixed_org_unit: Optional[str] = None
) -> Tuple[List[Dict], Dict]:
    """
    Mode Valeurs: Traite un fichier avec valeurs numériques pré-agrégées
    Support de la détection automatique des colonnes de valeurs (TCD)
    """
    logger.info("Mode Valeurs: Traitement des valeurs agrégées")
    logger.info(f"Input: df shape={df.shape}, org_column={org_column}, fixed_org={fixed_org_unit}")
    logger.info(f"Mapping reçu: categories={category_mapping}, DEs={data_element_mapping}")

    # Détection automatique des colonnes de valeurs si mapping vide ou incomplet
    if not data_element_mapping:
        logger.info("Aucun mapping DE fourni, tentative de détection automatique...")
        detected_cols = _detect_value_columns(df, org_column, category_mapping, data_element_mapping)
        
        if detected_cols:
            logger.info(f"✓ Colonnes de valeurs détectées: {detected_cols}")
            # Récupérer le premier DE du dataset comme fallback
            dataset = next((ds for ds in metadata_manager.datasets if ds['id'] == dataset_id), None)
            if dataset and dataset.get('dataSetElements'):
                first_de_id = dataset['dataSetElements'][0]['dataElement']['id']
                # Créer un mapping automatique pour chaque colonne détectée
                data_element_mapping = {first_de_id: detected_cols[0]}
                logger.info(f"Mapping automatique créé: {first_de_id} -> {detected_cols[0]}")
            else:
                raise ValueError("Impossible de détecter les colonnes de valeurs et aucun DE dans le dataset")
        else:
            raise ValueError("Aucune colonne de valeur détectée. Vérifiez le format du fichier.")

    # Vérifier que toutes les colonnes mappées existent
    if fixed_org_unit:
        # Mode valeur fixe : pas besoin de colonne org
        required_cols = list(category_mapping.values()) + list(data_element_mapping.values())
    else:
        required_cols = [org_column] + list(category_mapping.values()) + list(data_element_mapping.values())
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le fichier: {', '.join(missing_cols)}")

    # Préparer les données
    df = df.fillna("")

    # Générer les dataValues
    data_values = []
    errors = {
        'org_not_found': 0,
        'de_not_found': 0,
        'coc_not_found': 0,
        'invalid_value': 0,
        'empty_value': 0
    }

    default_aoc = metadata_manager.coc_lookup.get("default", "")
    
    logger.info(f"Début de la boucle: {len(df)} lignes à traiter avec {len(data_element_mapping)} DEs")

    for idx, row in df.iterrows():
        # Résoudre l'organisation
        if fixed_org_unit:
            # Mode valeur fixe
            org_id = fixed_org_unit
        else:
            # Mode colonne
            org_value = str(row[org_column]).strip()
            org_key = org_value.lower()

            # Essayer d'abord par code (plus fiable)
            org_id = metadata_manager.org_code_to_id.get(org_key)

            # Fallback sur le nom si code non trouvé
            if not org_id:
                org_id = metadata_manager.org_name_to_id.get(org_key)

            if not org_id:
                errors['org_not_found'] += 1
                logger.warning(f"Ligne {idx+2}: Organisation non trouvée: {org_value}")
                continue

        # Résoudre les category options
        category_options = {}
        for cat_id, col_name in category_mapping.items():
            cat_value = str(row[col_name]).strip()
            if cat_value:
                # Normaliser la valeur
                cat_value_normalized = _normalize_category_value(cat_value)
                category_options[cat_id] = cat_value_normalized

        # Pour chaque data element mappé
        for de_id, col_name in data_element_mapping.items():
            # Récupérer la valeur
            value = row[col_name]

            # Ignorer les valeurs vides
            if pd.isna(value) or value == '' or value == 0:
                errors['empty_value'] += 1
                continue

            # Valider la valeur
            parsed_value = _parse_value(value)
            if parsed_value is None:
                errors['invalid_value'] += 1
                logger.warning(f"Ligne {idx+2}, DE {de_id}: Valeur invalide: {value}")
                continue

            # Récupérer le data element
            de = metadata_manager.data_elements_map.get(de_id)
            if not de:
                errors['de_not_found'] += 1
                continue

            # Résoudre le COC
            cc_id = de.get('categoryCombo', {}).get('id')
            coc_id = _resolve_coc(metadata_manager, cc_id, category_options)

            if not coc_id:
                errors['coc_not_found'] += 1
                logger.warning(f"Ligne {idx+2}, DE {de_id}: COC non trouvé pour {category_options}")
                continue

            # Créer le dataValue
            data_value = {
                'dataElement': de_id,
                'period': period,
                'orgUnit': org_id,
                'categoryOptionCombo': coc_id,
                'attributeOptionCombo': default_aoc,
                'value': str(parsed_value)
            }

            data_values.append(data_value)

    # Statistiques
    stats = {
        'total_rows': len(df),
        'valid_rows': len(data_values),
        'errors': errors,
        'error_rate': round((sum(errors.values()) / (len(df) * len(data_element_mapping))) * 100, 2) if len(df) > 0 else 0
    }

    logger.info(f"Traitement terminé: {len(data_values)} valeurs valides sur {len(df)} lignes x {len(data_element_mapping)} DEs")

    return data_values, stats


def _process_count_mode(
    metadata_manager,
    df: pd.DataFrame,
    org_column: str,
    category_mapping: Dict[str, str],
    data_element_mapping: Dict[str, str],
    dataset_id: str,
    period: str,
    data_element_column: Optional[str] = None,
    value_to_de_mapping: Optional[Dict[str, str]] = None,
    fixed_org_unit: Optional[str] = None
) -> Tuple[List[Dict], Dict]:
    """
    Mode Comptage: Traite un fichier avec enregistrements individuels
    Compte automatiquement les enregistrements par combinaison de catégories
    Supporte le mapping dynamique des Data Elements via une colonne
    """
    logger.info("Mode Comptage: Agrégation automatique des enregistrements")

    # Vérifier que les colonnes requises existent
    if fixed_org_unit:
        required_cols = list(category_mapping.values())
    else:
        required_cols = [org_column] + list(category_mapping.values())
    
    if data_element_column:
        required_cols.append(data_element_column)
        
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le fichier: {', '.join(missing_cols)}")

    # Logique de détermination du Data Element
    if not data_element_column:
        # Mode classique: un seul DE fixe
        if not data_element_mapping:
            logger.warning("Aucun data element mappé, tentative d'utilisation du premier DE du dataset")
            dataset = next((ds for ds in metadata_manager.datasets if ds['id'] == dataset_id), None)
            if dataset and dataset.get('dataSetElements') and len(dataset['dataSetElements']) > 0:
                first_de_id = dataset['dataSetElements'][0]['dataElement']['id']
                logger.info(f"✓ Utilisation du premier DE du dataset: {first_de_id}")
                data_element_mapping = {first_de_id: 'COUNT'}
            else:
                logger.error(f"Dataset {dataset_id} n'a pas de dataSetElements!")
                raise ValueError(f"Le dataset {dataset_id} ne contient aucun data element")

        if not data_element_mapping:
            raise ValueError("Aucun data element disponible pour le comptage")
        
        logger.info(f"Mode count avec DE fixe: {list(data_element_mapping.keys())[0]}")
    else:
        # Mode dynamique
        if not value_to_de_mapping:
            raise ValueError("Mapping des valeurs vers Data Elements manquant")

    # Préparer les colonnes de groupement
    if fixed_org_unit:
        group_columns = list(category_mapping.values())
    else:
        group_columns = [org_column] + list(category_mapping.values())
    
    if data_element_column:
        group_columns.append(data_element_column)

    # Nettoyer les données
    df = df.copy()
    for col in group_columns:
        df[col] = df[col].fillna('Non spécifié').astype(str).str.strip()

    # Grouper et compter
    aggregated = df.groupby(group_columns).size().reset_index(name='COUNT')

    logger.info(f"Agrégation: {len(df)} enregistrements → {len(aggregated)} combinaisons")

    # Générer les dataValues
    data_values = []
    errors = {
        'org_not_found': 0,
        'de_not_found': 0,
        'coc_not_found': 0,
        'invalid_value': 0,
        'empty_value': 0,
        'mapping_not_found': 0
    }

    default_aoc = metadata_manager.coc_lookup.get("default", "")

    # Si mode fixe, on récupère le DE unique
    fixed_de_id = None
    if not data_element_column:
        fixed_de_id = list(data_element_mapping.keys())[0]
        de_obj = metadata_manager.data_elements_map.get(fixed_de_id)
        if not de_obj:
             raise ValueError(f"Data element {fixed_de_id} introuvable dans metadata")
        logger.info(f"Utilisation DE fixe: {fixed_de_id} ({de_obj.get('name', 'sans nom')})")

    logger.info(f"Début génération des dataValues pour {len(aggregated)} combinaisons...")
    
    for idx, row in aggregated.iterrows():
        # Résoudre le Data Element
        de_id = fixed_de_id
        
        if data_element_column:
            val = row[data_element_column]
            # Essayer de trouver le DE correspondant à la valeur
            # On normalise la clé (minuscule, strip) pour être plus tolérant
            # Mais le mapping doit être fourni correctement
            de_id = value_to_de_mapping.get(val)
            
            # Si pas trouvé, essayer avec des variantes simples ? 
            # Pour l'instant on reste strict ou on log
            if not de_id:
                errors['mapping_not_found'] += 1
                logger.warning(f"Combinaison {idx+1}: Pas de mapping pour la valeur '{val}'")
                continue
        
        de = metadata_manager.data_elements_map.get(de_id)
        if not de:
            errors['de_not_found'] += 1
            logger.warning(f"Combinaison {idx+1}: DE {de_id} introuvable dans metadata")
            continue

        # Résoudre l'organisation
        if fixed_org_unit:
            org_id = fixed_org_unit
        else:
            org_value = str(row[org_column]).strip()
            org_key = org_value.lower()

            # Essayer par code puis par nom
            org_id = metadata_manager.org_code_to_id.get(org_key)
            if not org_id:
                org_id = metadata_manager.org_name_to_id.get(org_key)

            if not org_id:
                errors['org_not_found'] += 1
                logger.warning(f"Combinaison {idx+1}: Organisation non trouvée: {org_value}")
                continue

        # Résoudre les category options
        category_options = {}
        for cat_id, col_name in category_mapping.items():
            cat_value = str(row[col_name]).strip()
            if cat_value and cat_value != 'Non spécifié':
                cat_value_normalized = _normalize_category_value(cat_value)
                category_options[cat_id] = cat_value_normalized

        # Résoudre le COC
        cc_id = de.get('categoryCombo', {}).get('id')
        coc_id = _resolve_coc(metadata_manager, cc_id, category_options)

        if not coc_id:
            errors['coc_not_found'] += 1
            logger.warning(f"Combinaison {idx+1}: COC non trouvé pour CC={cc_id}, options={category_options}")
            continue

        # Récupérer le compte
        count_value = int(row['COUNT'])

        if count_value == 0:
            errors['empty_value'] += 1
            logger.debug(f"Combinaison {idx+1}: Valeur = 0, ignorée")
            continue
        
        logger.debug(f"✓ Combinaison {idx+1}: DE={de_id}, Org={org_id}, COC={coc_id}, Value={count_value}")

        # Créer le dataValue
        data_value = {
            'dataElement': de_id,
            'period': period,
            'orgUnit': org_id,
            'categoryOptionCombo': coc_id,
            'attributeOptionCombo': default_aoc,
            'value': str(count_value)
        }

        data_values.append(data_value)

    # Statistiques
    stats = {
        'total_rows': len(aggregated),
        'valid_rows': len(data_values),
        'errors': errors,
        'error_rate': round((sum(errors.values()) / len(aggregated)) * 100, 2) if len(aggregated) > 0 else 0,
        'original_records': len(df),
        'aggregated_combinations': len(aggregated)
    }

    logger.info(f"Traitement terminé: {len(data_values)} valeurs valides sur {len(aggregated)} combinaisons")
    if len(data_values) == 0:
        logger.error(f"AUCUNE VALEUR GÉNÉRÉE! Erreurs: {errors}")
        logger.error(f"Vérifiez: 1) Les org units, 2) Les category combos, 3) Les mappings")

    return data_values, stats


def _resolve_coc(
    metadata_manager,
    cc_id: Optional[str],
    category_options: Dict[str, str]
) -> Optional[str]:
    """
    Résout le categoryOptionCombo à partir des category options
    Utilise le fuzzy matching pour gérer les variantes d'ordre

    Args:
        metadata_manager: MetadataManager
        cc_id: ID du category combo
        category_options: Dict {category_id: option_value}

    Returns:
        ID du COC ou None
    """
    # Si pas de combo ou combo par défaut
    if not cc_id:
        return metadata_manager.coc_lookup.get("default")

    cat_combo = metadata_manager.cat_combos.get(cc_id)
    if not cat_combo or cat_combo.get('name') == 'default':
        return metadata_manager.coc_lookup.get("default")

    # Construire la clé de lookup
    options = []
    for cat in cat_combo.get('categories', []):
        cat_id = cat['id']
        if cat_id in category_options:
            options.append(category_options[cat_id])

    if options:
        # Construire le nom du COC avec différents séparateurs
        # Tenter d'abord avec " | " (standard)
        coc_name = " | ".join(sorted(options))
        
        # Utiliser le fuzzy matching
        coc_id = metadata_manager.get_coc_uid_fuzzy(coc_name)
        if coc_id:
            return coc_id
        
        # Tenter avec "," comme séparateur alternatif
        coc_name_alt = ", ".join(sorted(options))
        coc_id = metadata_manager.get_coc_uid_fuzzy(coc_name_alt)
        if coc_id:
            return coc_id

        # Debug: log la clé recherchée
        logger.debug(f"COC non trouvé pour: '{coc_name}' ou '{coc_name_alt}'")

    return metadata_manager.coc_lookup.get("default")


def _normalize_category_value(value: str) -> str:
    """
    Normalise une valeur de catégorie

    Args:
        value: Valeur brute

    Returns:
        Valeur normalisée
    """
    v = value.lower().strip()

    # Normalisation pour le sexe
    if v in ['masculin', 'homme', 'male', 'm', 'h']:
        return 'M'
    if v in ['feminin', 'féminin', 'femme', 'female', 'f']:
        return 'F'

    # Retourner la valeur avec première lettre en majuscule
    return value.strip().title()


def _parse_value(value) -> Optional[float]:
    """
    Parse et valide une valeur numérique

    Args:
        value: Valeur à parser

    Returns:
        Valeur numérique ou None si invalide
    """
    try:
        # Convertir en float
        val = float(value)

        # Vérifier que ce n'est pas NaN
        if pd.isna(val):
            return None

        # Vérifier que c'est positif ou zéro
        if val < 0:
            logger.warning(f"Valeur négative ignorée: {val}")
            return None

        return val

    except (ValueError, TypeError):
        return None


def _apply_fill_down(
    df: pd.DataFrame,
    org_column: str,
    category_mapping: Dict[str, str]
) -> pd.DataFrame:
    """
    Applique le fill down (forward fill) aux colonnes structurelles
    Gère les cellules fusionnées typiques des TCD Excel
    
    Args:
        df: DataFrame à traiter
        org_column: Nom de la colonne organisation
        category_mapping: Mapping des catégories
        
    Returns:
        DataFrame avec fill down appliqué
    """
    # Identifier les colonnes structurelles qui nécessitent un fill down
    structural_cols = []
    
    # Ajouter la colonne organisation si elle existe
    if org_column and org_column in df.columns:
        structural_cols.append(org_column)
    
    # Ajouter les colonnes de catégories
    for col_name in category_mapping.values():
        if col_name in df.columns and col_name not in structural_cols:
            structural_cols.append(col_name)
    
    # Appliquer le fill down (forward fill) sur les colonnes structurelles
    for col in structural_cols:
        df[col] = df[col].ffill()
        logger.debug(f"Fill down appliqué sur la colonne: {col}")
    
    logger.info(f"Fill down appliqué sur {len(structural_cols)} colonnes structurelles: {structural_cols}")
    
    return df


def _detect_value_columns(
    df: pd.DataFrame,
    org_column: str,
    category_mapping: Dict[str, str],
    data_element_mapping: Dict[str, str]
) -> List[str]:
    """
    Détecte automatiquement les colonnes de valeurs (non-structurelles)
    Utile pour les TCD où on ne connaît pas toujours le nom exact de la colonne
    
    Args:
        df: DataFrame
        org_column: Colonne organisation
        category_mapping: Mapping catégories
        data_element_mapping: Mapping data elements existant
        
    Returns:
        Liste des noms de colonnes de valeurs détectées
    """
    # Colonnes à ignorer (structurelles)
    ignore_cols = set()
    
    if org_column:
        ignore_cols.add(org_column)
    
    ignore_cols.update(category_mapping.values())
    ignore_cols.update(data_element_mapping.values())
    
    # Mots-clés indiquant une colonne de comptage/valeur
    value_keywords = ['nombre', 'effectif', 'total', 'count', 'somme', 'valeur']
    
    # Détecter les colonnes candidates
    value_cols = []
    for col in df.columns:
        if col in ignore_cols:
            continue
        
        # Vérifier si c'est une colonne numérique OU contient un mot-clé
        col_lower = str(col).lower()
        is_value_col = (
            any(keyword in col_lower for keyword in value_keywords) or
            pd.api.types.is_numeric_dtype(df[col])
        )
        
        if is_value_col:
            value_cols.append(col)
    
    logger.info(f"Colonnes de valeurs détectées: {value_cols}")
    
    return value_cols
