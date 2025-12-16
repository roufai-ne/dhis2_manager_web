"""
Gestionnaire de métadonnées DHIS2
==================================
Adapté de l'application Tkinter pour le web avec support de sérialisation
pour stockage en session.

Auteur: Amadou Roufai
"""

import json
import os
import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MetadataManager:
    """
    Gestionnaire des métadonnées DHIS2
    Peut être sérialisé/désérialisé pour stockage en session
    """
    raw_data: Dict = field(default_factory=dict)
    org_units_map: Dict[str, Dict] = field(default_factory=dict)
    org_name_to_id: Dict[str, str] = field(default_factory=dict)
    org_code_to_id: Dict[str, str] = field(default_factory=dict)
    org_children_map: Dict[str, List[str]] = field(default_factory=dict)
    datasets: List[Dict] = field(default_factory=list)
    data_elements_map: Dict[str, Dict] = field(default_factory=dict)
    de_name_to_id: Dict[str, str] = field(default_factory=dict)
    coc_map: Dict[str, Dict] = field(default_factory=dict)
    cat_opt_map: Dict[str, str] = field(default_factory=dict)
    cat_combos: Dict[str, Dict] = field(default_factory=dict)
    categories: Dict[str, Dict] = field(default_factory=dict)
    coc_lookup: Dict[str, str] = field(default_factory=dict)
    coc_variants: Dict[str, str] = field(default_factory=dict)  # Fuzzy matching: ordre-indépendant
    
    # New fields for expanded metadata
    org_unit_levels: List[Dict] = field(default_factory=list)
    org_unit_groups: Dict[str, Dict] = field(default_factory=dict)
    org_unit_group_sets: List[Dict] = field(default_factory=list)
    data_element_groups: Dict[str, Dict] = field(default_factory=dict)
    data_element_group_sets: List[Dict] = field(default_factory=list)
    sections: Dict[str, Dict] = field(default_factory=dict)
    sections_by_dataset: Dict[str, List[Dict]] = field(default_factory=dict)
    de_to_section: Dict[str, str] = field(default_factory=dict)
    
    def load_from_file(self, filepath: str) -> Tuple[bool, List[str], List[str]]:
        """
        Charge les métadonnées depuis un fichier JSON
        
        Args:
            filepath: Chemin du fichier JSON
            
        Returns:
            Tuple (succès, liste d'erreurs, liste d'avertissements)
        """
        errors, warnings = [], []
        
        if not os.path.exists(filepath):
            return False, [f"Fichier '{filepath}' introuvable."], []
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Erreur JSON: {e}"], []
        except Exception as e:
            return False, [f"Erreur: {e}"], []
        
        # Parser les données
        success, parse_errors = self._parse_metadata()
        if not success:
            return False, parse_errors, warnings
            
        logger.info(f"Métadonnées chargées: {len(self.org_units_map)} organisations, "
                   f"{len(self.datasets)} datasets, {len(self.data_elements_map)} éléments")
        
        return True, errors, warnings
    
    def load_from_dict(self, data: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Charge les métadonnées depuis un dictionnaire (ex: upload web)
        
        Args:
            data: Dictionnaire contenant les métadonnées
            
        Returns:
            Tuple (succès, liste d'erreurs, liste d'avertissements)
        """
        errors, warnings = [], []
        
        try:
            self.raw_data = data
            success, parse_errors = self._parse_metadata()
            if not success:
                return False, parse_errors, warnings
            
            logger.info(f"Métadonnées chargées depuis dict: {len(self.org_units_map)} organisations")
            return True, errors, warnings
            
        except Exception as e:
            return False, [f"Erreur lors du chargement: {e}"], []
    
    def _parse_metadata(self) -> Tuple[bool, List[str]]:
        """Parse les métadonnées brutes"""
        errors = []
        
        try:
            # Organisations
            for ou in self.raw_data.get('organisationUnits', []):
                self.org_units_map[ou['id']] = ou
                self.org_name_to_id[ou['name'].strip().lower()] = ou['id']

                # Ajouter aussi le mapping par code si présent
                if ou.get('code'):
                    self.org_code_to_id[ou['code'].strip().lower()] = ou['id']

                parent_id = ou.get('parent', {}).get('id')
                if parent_id:
                    self.org_children_map.setdefault(parent_id, []).append(ou['id'])
            
            # Datasets
            self.datasets = self.raw_data.get('dataSets', [])
            
            # Data Elements
            for de in self.raw_data.get('dataElements', []):
                self.data_elements_map[de['id']] = de
                self.de_name_to_id[de['name'].strip().lower()] = de['id']
            
            # Category Option Combos
            for coc in self.raw_data.get('categoryOptionCombos', []):
                self.coc_map[coc['id']] = coc
            
            # Category Options
            for co in self.raw_data.get('categoryOptions', []):
                self.cat_opt_map[co['id']] = co['name']
            
            # Category Combos
            for cc in self.raw_data.get('categoryCombos', []):
                self.cat_combos[cc['id']] = cc
            
            # Categories
            for cat in self.raw_data.get('categories', []):
                self.categories[cat['id']] = cat
            
            # COC Lookup avec fuzzy matching
            for coc in self.raw_data.get('categoryOptionCombos', []):
                coc_id = coc['id']
                coc_name = coc.get('name', '')
                
                # Gérer le cas par défaut
                if coc_name == 'default':
                    self.coc_lookup['default'] = coc_id
                    self.coc_variants['default'] = coc_id
                    continue
                
                # Récupérer les noms des options
                opt_ids = [o['id'] if isinstance(o, dict) else o for o in coc.get('categoryOptions', [])]
                names = sorted([self.cat_opt_map.get(oid, "") for oid in opt_ids])
                
                # Clé standard (pour compatibilité)
                key = " | ".join(names).lower()
                if key:
                    self.coc_lookup[key] = coc_id
                
                # Clé de variante (ordre-indépendant) - Logique du MD
                # Tokenize par séparateurs courants: | , \t \n
                tokens = re.split(r'[|,\t\n]+', coc_name)
                clean_tokens = sorted([t.strip().lower() for t in tokens if t.strip()])
                variant_key = "_".join(clean_tokens)
                if variant_key:
                    self.coc_variants[variant_key] = coc_id
                    logger.debug(f"COC variant: '{variant_key}' -> {coc_id}")
            
            # Org Unit Levels
            self.org_unit_levels = self.raw_data.get('organisationUnitLevels', [])
            self.org_unit_levels.sort(key=lambda x: x['level'])
            
            # Org Unit Groups
            for oug in self.raw_data.get('organisationUnitGroups', []):
                self.org_unit_groups[oug['id']] = oug
                
            # Org Unit Group Sets
            self.org_unit_group_sets = self.raw_data.get('organisationUnitGroupSets', [])
            
            # Data Element Groups
            for deg in self.raw_data.get('dataElementGroups', []):
                self.data_element_groups[deg['id']] = deg
                
            # Data Element Group Sets
            self.data_element_group_sets = self.raw_data.get('dataElementGroupSets', [])
            
            # Sections (organizational structure within datasets)
            for section in self.raw_data.get('sections', []):
                self.sections[section['id']] = section
                
                # Index sections by dataset
                # dataSet peut être un dict {'id': '...'} ou directement un string (l'ID)
                dataset_ref = section.get('dataSet')
                dataset_id = None
                if isinstance(dataset_ref, dict):
                    dataset_id = dataset_ref.get('id')
                elif isinstance(dataset_ref, str):
                    dataset_id = dataset_ref
                
                if dataset_id:
                    if dataset_id not in self.sections_by_dataset:
                        self.sections_by_dataset[dataset_id] = []
                    self.sections_by_dataset[dataset_id].append(section)
                    
                    # Map data elements to sections
                    for de_ref in section.get('dataElements', []):
                        de_id = de_ref.get('id') if isinstance(de_ref, dict) else de_ref
                        if de_id:
                            self.de_to_section[de_id] = section['id']
            
            # Sort sections by sortOrder if present
            for ds_id, secs in self.sections_by_dataset.items():
                secs.sort(key=lambda x: x.get('sortOrder', 999))
            
            return True, errors
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing: {e}")
            return False, [f"Erreur de parsing: {e}"]
    
    def get_root_org_units(self) -> List[str]:
        """Retourne les IDs des organisations racines (sans parent)"""
        all_ids = set(self.org_units_map.keys())
        children = set()
        for kids in self.org_children_map.values():
            children.update(kids)
        return list(all_ids - children)
    
    def get_coc_display_name(self, coc_id: str) -> str:
        """Retourne le nom d'affichage d'un Category Option Combo"""
        coc = self.coc_map.get(coc_id)
        if not coc:
            return "Inconnu"
        if coc.get('name') == 'default':
            return "Total"
        names = sorted([
            self.cat_opt_map.get(o['id'] if isinstance(o, dict) else o, "")
            for o in coc.get('categoryOptions', [])
        ])
        return " | ".join(names) if names else "Inconnu"
    
    def get_coc_uid_fuzzy(self, name: str) -> Optional[str]:
        """
        Recherche un COC avec fuzzy matching (ordre-indépendant)
        Inspiré de la logique du MD remaniement.md
        
        Args:
            name: Nom du COC (ex: "F | 18ans" ou "18ans, F")
            
        Returns:
            UID du COC ou None
        """
        if not name:
            return None
        
        # 1. Tentative exacte via coc_lookup standard
        normalized = self._normalize_text(name)
        uid = self.coc_lookup.get(normalized)
        if uid:
            logger.debug(f"COC trouvé (exact): '{name}' -> {uid}")
            return uid
        
        # 2. Tentative fuzzy (ordre-indépendant)
        # Tokenize et trier les tokens
        tokens = re.split(r'[|,\t\n]+', str(name))
        clean_tokens = sorted([t.strip().lower() for t in tokens if t.strip()])
        variant_key = "_".join(clean_tokens)
        
        uid = self.coc_variants.get(variant_key)
        if uid:
            logger.debug(f"COC trouvé (fuzzy): '{name}' -> '{variant_key}' -> {uid}")
            return uid
        
        logger.debug(f"COC non trouvé: '{name}' (variant: '{variant_key}')")
        return None
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalise un texte pour le matching
        
        Args:
            text: Texte à normaliser
            
        Returns:
            Texte normalisé
        """
        if not isinstance(text, str):
            return ""
        # Enlève les caractères invisibles bizarres
        text = text.replace('\t', ' ').replace('\xa0', ' ')
        return " ".join(text.lower().split())
    
    def get_org_tree(self) -> List[Dict]:
        """
        Construit l'arborescence des organisations pour affichage
        
        Returns:
            Liste de dictionnaires représentant l'arbre
        """
        def build_node(org_id: str) -> Dict:
            org = self.org_units_map.get(org_id)
            if not org:
                return None
            
            node = {
                'id': org_id,
                'text': org['name'],
                'children': []
            }
            
            # Ajouter les enfants
            children_ids = self.org_children_map.get(org_id, [])
            for child_id in sorted(children_ids, key=lambda x: self.org_units_map[x]['name']):
                child_node = build_node(child_id)
                if child_node:
                    node['children'].append(child_node)
            
            return node
        
        # Construire l'arbre depuis les racines
        roots = self.get_root_org_units()
        tree = []
        for root_id in sorted(roots, key=lambda x: self.org_units_map[x]['name']):
            node = build_node(root_id)
            if node:
                tree.append(node)
        
        return tree
    
    def get_datasets(self) -> List[Dict]:
        """Retourne la liste des datasets avec infos basiques"""
        return [
            {
                'id': ds['id'],
                'name': ds['name'],
                'periodType': ds.get('periodType', 'Monthly')
            }
            for ds in self.datasets
        ]
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques sur les métadonnées chargées"""
        return {
            'org_units': len(self.org_units_map),
            'data_sets': len(self.datasets),
            'data_elements': len(self.data_elements_map),
            'category_option_combos': len(self.coc_map),
            'filename': getattr(self, 'filename', 'unknown'),
            'loaded_at': datetime.now().isoformat(),
            'org_unit_groups': len(self.org_unit_groups),
            'data_element_groups': len(self.data_element_groups)
        }
    
    def get_org_units_by_group(self, group_id: str) -> List[Dict]:
        """Retourne les UO appartenant à un groupe"""
        group = self.org_unit_groups.get(group_id)
        if not group:
            return []
        ou_ids = {ou['id'] for ou in group.get('organisationUnits', [])}
        return [self.org_units_map[ou_id] for ou_id in ou_ids if ou_id in self.org_units_map]

    def get_org_units_by_level(self, level: int) -> List[Dict]:
        """Retourne les UO d'un niveau spécifique"""
        return [ou for ou in self.org_units_map.values() if ou.get('level') == level]

    def get_data_elements_by_group(self, group_id: str) -> List[Dict]:
        """Retourne les éléments de données d'un groupe"""
        group = self.data_element_groups.get(group_id)
        if not group:
            return []
        de_ids = {de['id'] for de in group.get('dataElements', [])}
        return [self.data_elements_map[de_id] for de_id in de_ids if de_id in self.data_elements_map]
    
    def to_dict(self) -> Dict:
        """
        Convertit l'instance en dictionnaire pour stockage en session

        Returns:
            Dictionnaire sérialisable
        """
        return {
            'raw_data': self.raw_data,
            'org_units_map': self.org_units_map,
            'org_name_to_id': self.org_name_to_id,
            'org_code_to_id': self.org_code_to_id,
            'org_children_map': self.org_children_map,
            'datasets': self.datasets,
            'data_elements_map': self.data_elements_map,
            'de_name_to_id': self.de_name_to_id,
            'coc_map': self.coc_map,
            'cat_opt_map': self.cat_opt_map,
            'cat_combos': self.cat_combos,
            'categories': self.categories,
            'coc_lookup': self.coc_lookup,
            'coc_variants': self.coc_variants,
            'org_unit_levels': self.org_unit_levels,
            'org_unit_groups': self.org_unit_groups,
            'org_unit_group_sets': self.org_unit_group_sets,
            'data_element_groups': self.data_element_groups,
            'data_element_group_sets': self.data_element_group_sets,
            'sections': self.sections,
            'sections_by_dataset': self.sections_by_dataset,
            'de_to_section': self.de_to_section
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MetadataManager':
        """
        Recrée une instance depuis un dictionnaire (session)
        
        Args:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance de MetadataManager
        """
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    def validate_structure(self) -> Tuple[bool, List[str]]:
        """
        Valide la structure des métadonnées
        
        Returns:
            Tuple (valide, liste d'erreurs)
        """
        errors = []
        
        # Vérifier les champs obligatoires
        if not self.raw_data.get('organisationUnits'):
            errors.append("Aucune organisation trouvée")
        
        if not self.raw_data.get('dataSets'):
            errors.append("Aucun dataset trouvé")
        
        if not self.raw_data.get('dataElements'):
            errors.append("Aucun élément de données trouvé")
        
        # Vérifier l'intégrité des relations
        for org_id, children in self.org_children_map.items():
            if org_id not in self.org_units_map:
                errors.append(f"Organisation parente {org_id} introuvable")
        
        return len(errors) == 0, errors
