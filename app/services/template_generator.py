"""
Service de génération de templates Excel pour DHIS2
====================================================
Génère des fichiers Excel de saisie de données
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

from app.services.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


@dataclass
class TemplateConfig:
    """Configuration pour la génération de template"""
    org_unit_ids: List[str]
    dataset_id: str
    period: str
    period_type: str  # 'Monthly', 'Quarterly', 'Yearly'
    include_all_disaggregations: bool = True
    add_formulas: bool = False


class TemplateGenerator:
    """
    Générateur de templates Excel pour la saisie de données DHIS2
    """
    
    def __init__(self, metadata_manager: MetadataManager):
        """
        Initialise le générateur avec les métadonnées
        
        Args:
            metadata_manager: Instance de MetadataManager
        """
        self.metadata = metadata_manager
        
    def generate_template(self, config: TemplateConfig) -> Tuple[pd.DataFrame, Dict]:
        """
        Génère un template Excel basé sur la configuration
        Organise les données par section du dataset
        
        Args:
            config: Configuration du template
            
        Returns:
            Tuple (DataFrame, statistiques)
        """
        logger.info(f"Génération template pour dataset {config.dataset_id}, période {config.period}")
        
        # Récupérer le dataset
        dataset = self._get_dataset(config.dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {config.dataset_id} introuvable")
        
        # Récupérer l'attributeOptionCombo par défaut
        default_aoc = self.metadata.coc_lookup.get("default", "")
        
        rows = []
        stats = {
            'org_units': len(config.org_unit_ids),
            'data_elements': 0,
            'total_rows': 0,
            'dataset_name': dataset.get('name', 'Unknown'),
            'sections': 0
        }
        
        # Récupérer les sections du dataset depuis sections_by_dataset
        sections = self.metadata.sections_by_dataset.get(config.dataset_id, [])
        stats['sections'] = len(sections)
        
        # Trier par sortOrder
        if sections:
            sections = sorted(sections, key=lambda x: x.get('sortOrder', 999))
        
        # Si pas de sections, créer une section par défaut
        if not sections:
            logger.info(f"Pas de sections pour dataset {config.dataset_id}, utilisation de la section par défaut")
            sections = [{'id': 'default', 'name': 'Défaut', 'dataElements': []}]
        
        # Pour chaque organisation
        for org_id in config.org_unit_ids:
            org_unit = self.metadata.org_units_map.get(org_id)
            if not org_unit:
                logger.warning(f"Organisation {org_id} introuvable")
                continue
            
            # Log pour debug
            logger.debug(f"Organisation: {org_unit.get('name')} - Code: {org_unit.get('code', 'ABSENT')}")
            
            # Pour chaque section
            for section in sections:
                section_id = section.get('id')
                
                # Récupérer le nom de la section (name est le champ standard dans DHIS2)
                section_name = section.get('name') or section.get('displayName') or 'Défaut'
                
                # Éléments de la section
                if section_id == 'default':
                    # Section par défaut: tous les éléments du dataset
                    section_elements = [
                        ds_element.get('dataElement', {}).get('id')
                        for ds_element in dataset.get('dataSetElements', [])
                    ]
                else:
                    # Éléments spécifiques de la section
                    section_elements = [
                        de_ref.get('id') if isinstance(de_ref, dict) else de_ref
                        for de_ref in section.get('dataElements', [])
                    ]
                
                # Pour chaque élément de la section
                for de_id in section_elements:
                    if not de_id:
                        continue
                    
                    data_element = self.metadata.data_elements_map.get(de_id)
                    if not data_element:
                        logger.warning(f"DataElement {de_id} introuvable")
                        continue
                    
                    stats['data_elements'] += 1
                    
                    # Récupérer les combinaisons de catégories pour le dataElement
                    cc_id = data_element.get('categoryCombo', {}).get('id')
                    valid_cocs = self._get_valid_cocs(cc_id)

                    # Récupérer les attribute option combos du dataset (attribute category combo)
                    dataset_attr_cc_id = dataset.get('categoryCombo', {}).get('id') or dataset.get('attributeCategoryCombo', {}).get('id')
                    valid_aocs = self._get_valid_cocs(dataset_attr_cc_id) if dataset_attr_cc_id else [{'id': default_aoc, 'name': 'default'}]

                    # Créer une ligne pour chaque combinaison COC × AOC
                    for coc in valid_cocs:
                        for aoc in valid_aocs:
                            row = {
                                'section': section_name,
                                'dataElementName': data_element.get('name', ''),
                                'dataElement': de_id,
                                'orgUnitName': org_unit.get('name', ''),
                                'orgUnitCode': org_unit.get('code', ''),
                                'orgUnit': org_id,
                                'categoryOptionComboName': self.metadata.get_coc_display_name(coc.get('id', '')),
                                'categoryOptionCombo': coc.get('id', ''),
                                'attributeOptionComboName': self.metadata.get_coc_display_name(aoc.get('id', '')) if aoc.get('id') else 'default',
                                'attributeOptionCombo': aoc.get('id', default_aoc),
                                'period': config.period,
                                'value': ''
                            }

                            rows.append(row)
                            stats['total_rows'] += 1
        
        if not rows:
            raise ValueError("Aucune donnée générée. Vérifiez la configuration.")
        
        # Créer le DataFrame
        df = pd.DataFrame(rows)
        
        logger.info(f"Template généré : {stats['total_rows']} lignes pour {stats['org_units']} organisations et {stats['sections']} sections")
        
        return df, stats

    def generate_names_template(self, config: TemplateConfig) -> Tuple[pd.DataFrame, Dict]:
        """
        Génère un template sous forme de DataFrame avec colonnes basées sur les noms
        Inclut les sections du dataset
        
        Args:
            config: Configuration du template

        Returns:
            Tuple (DataFrame, statistiques)
        """
        logger.info(f"Génération template (noms) pour dataset {config.dataset_id}, période {config.period}")

        dataset = self._get_dataset(config.dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {config.dataset_id} introuvable")

        rows = []
        stats = {
            'org_units': len(config.org_unit_ids),
            'data_elements': 0,
            'total_rows': 0,
            'dataset_name': dataset.get('name', 'Unknown'),
            'sections': 0
        }

        # Récupérer les sections du dataset depuis sections_by_dataset
        sections = self.metadata.sections_by_dataset.get(config.dataset_id, [])
        stats['sections'] = len(sections)
        
        # Trier par sortOrder
        if sections:
            sections = sorted(sections, key=lambda x: x.get('sortOrder', 999))
        
        if not sections:
            logger.info(f"Pas de sections pour dataset {config.dataset_id}, utilisation de la section par défaut")
            sections = [{'id': 'default', 'name': 'Défaut', 'dataElements': []}]

        for org_id in config.org_unit_ids:
            org_unit = self.metadata.org_units_map.get(org_id)
            if not org_unit:
                logger.warning(f"Organisation {org_id} introuvable")
                continue

            for section in sections:
                section_id = section.get('id')
                
                # Récupérer le nom de la section (name est le champ standard dans DHIS2)
                section_name = section.get('name') or section.get('displayName') or 'Défaut'
                
                # Éléments de la section
                if section_id == 'default':
                    section_elements = [
                        ds_element.get('dataElement', {}).get('id')
                        for ds_element in dataset.get('dataSetElements', [])
                    ]
                else:
                    section_elements = [
                        de_ref.get('id') if isinstance(de_ref, dict) else de_ref
                        for de_ref in section.get('dataElements', [])
                    ]
                
                for de_id in section_elements:
                    if not de_id:
                        continue
                    
                    data_element = self.metadata.data_elements_map.get(de_id)
                    if not data_element:
                        logger.warning(f"DataElement {de_id} introuvable")
                        continue
                    stats['data_elements'] += 1

                    cc_id = data_element.get('categoryCombo', {}).get('id')
                    valid_cocs = self._get_valid_cocs(cc_id)

                    dataset_attr_cc_id = dataset.get('categoryCombo', {}).get('id') or dataset.get('attributeCategoryCombo', {}).get('id')
                    valid_aocs = self._get_valid_cocs(dataset_attr_cc_id) if dataset_attr_cc_id else [{'id': self.metadata.coc_lookup.get('default', ''), 'name': 'default'}]

                    for coc in valid_cocs:
                        for aoc in valid_aocs:
                            row = {
                                'section': section_name,
                                'dataElementName': data_element.get('name', ''),
                                'dataElement': de_id,
                                'orgUnitName': org_unit.get('name', ''),
                                'orgUnitCode': org_unit.get('code', ''),
                                'orgUnit': org_id,
                                'categoryOptionComboName': self.metadata.get_coc_display_name(coc.get('id', '')),
                                'categoryOptionCombo': coc.get('id', ''),
                                'attributeOptionComboName': self.metadata.get_coc_display_name(aoc.get('id', '')) if aoc.get('id') else 'default',
                                'attributeOptionCombo': aoc.get('id', self.metadata.coc_lookup.get('default', '')),
                                'period': config.period,
                                'value': ''
                            }
                            rows.append(row)
                            stats['total_rows'] += 1

        if not rows:
            raise ValueError("Aucune donnée générée. Vérifiez la configuration.")

        df = pd.DataFrame(rows)
        logger.info(f"Template (noms) généré : {stats['total_rows']} lignes pour {stats['org_units']} organisations et {stats['sections']} sections")
        return df, stats
    
    def _get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Récupère un dataset par son ID"""
        return next(
            (ds for ds in self.metadata.datasets if ds.get('id') == dataset_id),
            None
        )
    
    def _get_valid_cocs(self, category_combo_id: str) -> List[Dict]:
        """
        Récupère les COCs valides pour un category combo
        
        Args:
            category_combo_id: ID du category combo
            
        Returns:
            Liste des COCs valides
        """
        if not category_combo_id:
            # Retourner le COC par défaut
            default_coc = {
                'id': self.metadata.coc_lookup.get('default', ''),
                'name': 'default'
            }
            return [default_coc]
        
        # Récupérer tous les COCs qui correspondent à ce combo
        valid_cocs = []
        for coc in self.metadata.raw_data.get('categoryOptionCombos', []):
            coc_combo_id = coc.get('categoryCombo', {}).get('id')
            if coc_combo_id == category_combo_id:
                valid_cocs.append(coc)
        
        # Si aucun COC trouvé, utiliser le défaut
        if not valid_cocs:
            logger.warning(f"Aucun COC trouvé pour combo {category_combo_id}, utilisation du défaut")
            default_coc = {
                'id': self.metadata.coc_lookup.get('default', ''),
                'name': 'default'
            }
            return [default_coc]
        
        return valid_cocs
    
    def get_dataset_info(self, dataset_id: str) -> Dict:
        """
        Récupère les informations d'un dataset
        
        Args:
            dataset_id: ID du dataset
            
        Returns:
            Dictionnaire avec les infos
        """
        dataset = self._get_dataset(dataset_id)
        if not dataset:
            return {}
        
        # Compter les éléments
        num_elements = len(dataset.get('dataSetElements', []))
        
        # Identifier les catégories utilisées
        categories_used = set()
        for ds_element in dataset.get('dataSetElements', []):
            de_id = ds_element.get('dataElement', {}).get('id')
            data_element = self.metadata.data_elements_map.get(de_id)
            if data_element:
                cc_id = data_element.get('categoryCombo', {}).get('id')
                if cc_id:
                    cat_combo = self.metadata.cat_combos.get(cc_id)
                    if cat_combo and cat_combo.get('name') != 'default':
                        for cat in cat_combo.get('categories', []):
                            categories_used.add(cat.get('name', ''))
        
        return {
            'id': dataset.get('id'),
            'name': dataset.get('name'),
            'shortName': dataset.get('shortName'),
            'periodType': dataset.get('periodType', 'Unknown'),
            'num_elements': num_elements,
            'categories': list(categories_used),
            'has_disaggregation': len(categories_used) > 0
        }
    
    def validate_config(self, config: TemplateConfig) -> Tuple[bool, List[str]]:
        """
        Valide la configuration avant génération
        
        Args:
            config: Configuration à valider
            
        Returns:
            Tuple (valide, liste d'erreurs)
        """
        errors = []
        
        # Vérifier les organisations
        if not config.org_unit_ids:
            errors.append("Aucune organisation sélectionnée")
        else:
            for org_id in config.org_unit_ids:
                if org_id not in self.metadata.org_units_map:
                    errors.append(f"Organisation {org_id} introuvable")
        
        # Vérifier le dataset
        dataset = self._get_dataset(config.dataset_id)
        if not dataset:
            errors.append(f"Dataset {config.dataset_id} introuvable")
        
        # Vérifier la période
        if not config.period:
            errors.append("Période manquante")
        else:
            # Valider le format de période selon le type
            if not self._validate_period_format(config.period, config.period_type):
                errors.append(f"Format de période invalide pour le type {config.period_type}")
        
        return len(errors) == 0, errors
    
    def _validate_period_format(self, period: str, period_type: str) -> bool:
        """
        Valide le format de période
        
        Args:
            period: Période (ex: "2024", "202401", "2024Q1")
            period_type: Type de période
            
        Returns:
            True si valide
        """
        try:
            if period_type == 'Yearly':
                # Format: YYYY
                return len(period) == 4 and period.isdigit()
            
            elif period_type == 'Monthly':
                # Format: YYYYMM
                if len(period) != 6 or not period.isdigit():
                    return False
                year = int(period[:4])
                month = int(period[4:6])
                return 1 <= month <= 12 and year > 1900
            
            elif period_type == 'Quarterly':
                # Format: YYYYQ# (ex: 2024Q1)
                if len(period) != 6 or period[4] != 'Q':
                    return False
                year = period[:4]
                quarter = period[5]
                return year.isdigit() and quarter in ['1', '2', '3', '4']
            
            elif period_type == 'Weekly':
                # Format: YYYYW# ou YYYYWnn
                if 'W' not in period:
                    return False
                parts = period.split('W')
                if len(parts) != 2:
                    return False
                year, week = parts
                return year.isdigit() and week.isdigit() and 1 <= int(week) <= 53
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation période: {e}")
            return False
    
    def get_period_examples(self, period_type: str) -> List[str]:
        """
        Retourne des exemples de format de période
        
        Args:
            period_type: Type de période
            
        Returns:
            Liste d'exemples
        """
        current_year = datetime.now().year
        
        if period_type == 'Yearly':
            return [str(current_year), str(current_year - 1)]
        
        elif period_type == 'Monthly':
            return [f"{current_year}01", f"{current_year}12"]
        
        elif period_type == 'Quarterly':
            return [f"{current_year}Q1", f"{current_year}Q4"]
        
        elif period_type == 'Weekly':
            return [f"{current_year}W01", f"{current_year}W52"]
        
        return [str(current_year)]
