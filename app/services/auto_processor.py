"""
Service de traitement automatique TCD vers Template DHIS2
Basé sur INTEGRATION_XLS.MD

Architecture:
- Normalizer: Normalisation des chaînes (âge, COC, etc.)
- AutoMappingConfig: Configuration des mappings
- ProcessingStats: Statistiques de traitement
- AutoProcessor: Processeur principal
"""

import pandas as pd
import re
import logging
import difflib
import unicodedata
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from app.services.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


# =============================================================================
# CLASSES DE CONFIGURATION
# =============================================================================

@dataclass
class AutoMappingConfig:
    """Configuration des mappings pour le traitement automatique"""
    
    # Mapping établissements: {ACRONYME_TCD: 'partie_du_nom_template'}
    etablissements_patterns: Dict[str, str] = field(default_factory=dict)
    
    # Mapping data elements: {valeur_tcd: (section, data_element_name)}
    data_elements_manuels: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    
    # Positions des headers
    template_header_row: int = 5  # Header template DHIS2 à la ligne 5 (index 5)
    tcd_header_row: int = 0       # Header TCD à la ligne 0 (index 0 = première ligne)
    
    # Colonnes standard Template DHIS2
    col_section_template: str = 'Section'
    col_data_element_template: str = 'Data Element'
    col_org_unit_template: str = 'Organisation unit'
    col_coc_template: str = 'Category option combo'
    col_value_template: str = 'Value'
    
    # Colonnes standard TCD
    col_etablissement: str = 'NOM_ETAB'
    col_code_etablissement: str = 'CODE_ETAB'
    
    # Generic Category Configuration
    # Defaults to ['SEXE', 'GROUP_AGE'] for backward compatibility
    category_cols: List[str] = field(default_factory=lambda: ['SEXE', 'GROUP_AGE'])
    
    # Value Mappings: {column_name: {old_value: new_value}}
    # Example: {'Nationalite': {'NIGER': 'Nigerien', 'MALI': 'Malien'}}
    value_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # Legacy attributes for backward compatibility
    @property
    def col_age(self):
        return self.category_cols[1] if len(self.category_cols) > 1 else 'GROUP_AGE'
        
    @property
    def col_sexe(self):
        return self.category_cols[0] if len(self.category_cols) > 0 else 'SEXE'


@dataclass
class ProcessingStats:
    """Statistiques de traitement"""
    lignes_traitees: int = 0
    valeurs_inserees: int = 0
    
    # Erreurs par type
    etablissements_non_mappes: Dict[str, int] = field(default_factory=dict)
    data_elements_non_mappes: Dict[str, int] = field(default_factory=dict)
    combinaisons_non_trouvees: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self):
        """Convertit en dictionnaire pour sérialisation JSON"""
        return {
            'lignes_traitees': self.lignes_traitees,
            'valeurs_inserees': self.valeurs_inserees,
            'etablissements_non_mappes': self.etablissements_non_mappes,
            'data_elements_non_mappes': self.data_elements_non_mappes,
            'combinaisons_non_trouvees': self.combinaisons_non_trouvees[:10]  # Limiter à 10 pour JSON
        }


# =============================================================================
# CLASSE DE NORMALISATION
# =============================================================================

class Normalizer:
    """Méthodes statiques de normalisation"""
    
    # Patterns regex compilés une seule fois (optimisation)
    PATTERN_AGE_RANGE = re.compile(r'\[?\s*(\d+)\s*[-–]\s*(\d+)\s*\[?')
    PATTERN_COC_FORMAT1 = re.compile(r'^([FM])\s*\|\s*(.+)$')
    PATTERN_COC_FORMAT2 = re.compile(r'^(.+)\s*\|\s*([FM])$')
    
    @staticmethod
    def normaliser_tranche_age(s: Any) -> Optional[str]:
        """
        Normalise une tranche d'âge vers un format standard.
        
        Règles:
        - '[ 20 - 22 [' → '20-22'
        - '40 ans et plus' → '40+'
        - '- 18 ans' ou 'moins de 18' → '-18'
        - 'ND' ou 'Non Défini' → 'ND'
        
        Args:
            s: Chaîne à normaliser
            
        Returns:
            Chaîne normalisée ou None si invalide
        """
        if pd.isna(s):
            return None
            
        s = str(s).strip()
        
        # Cas spéciaux
        if '40 ans' in s.lower() or '40+' in s.lower():
            return '40+'
        if '18 ans' in s.lower() or re.match(r'^-\s*18', s):
            return '-18'
        if 'ND' in s.upper() or 'NON' in s.upper():
            return 'ND'
        
        # Extraction des bornes numériques
        match = Normalizer.PATTERN_AGE_RANGE.search(s)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
            
        return s
    
    @staticmethod
    def normalize_value(val: Any, column_name: str = None, mappings: Dict[str, Dict[str, str]] = None) -> Optional[str]:
        """
        Generic normalizer for any value.
        Applies specific rules based on value content (e.g. Age) or mappings.
        """
        if pd.isna(val):
            return None
            
        s = str(val).strip()
        
        # 1. Apply Mappings if available
        if mappings and column_name and column_name in mappings:
            if s in mappings[column_name]:
                return mappings[column_name][s]
        
        # 2. Heuristic for Age Ranges
        # If it matches age patterns, use age normalizer
        if 'ANS' in s.upper() or Normalizer.PATTERN_AGE_RANGE.search(s) or '+' in s or re.match(r'^-\s*\d+', s):
             # Only apply if it doesn't look like a standard string
             age_norm = Normalizer.normaliser_tranche_age(s)
             if age_norm: return age_norm

        # 3. Default: Upper case strip
        return s.strip() #.upper() # Keep case sensitivity? DHIS2 usually sensitive, but let's stick to simple strip.

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalise le texte pour la comparaison (majuscules, sans accents, sans caractères spéciaux).
        """
        if not isinstance(text, str):
            text = str(text)
            
        # Supprimer les accents
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
        
        # Majuscules et nettoyage
        text = re.sub(r'[^A-Z0-9]', '', text.upper())
        
        return text

    @staticmethod
    def normaliser_coc(coc: Any) -> Optional[str]:
        """
        Generic COC Normalization.
        Splits by '|', normalizes each part, sorts them alphabetically, and joins back.
        Matches 'Age|Sex' to 'Sex|Age' regardless of order.
        """
        if pd.isna(coc):
            return None
            
        s = str(coc).strip().replace('\t', ' ')
        s = re.sub(r'\s+', ' ', s)
        
        # Split by pipe
        parts = [p.strip() for p in s.split('|')]
        
        # Normalize each part individually
        norm_parts = []
        for p in parts:
            # Try age normalization first
            age_norm = Normalizer.normaliser_tranche_age(p)
            if age_norm and age_norm != p:
                norm_parts.append(age_norm)
            else:
                 # Just strip and uppercase for standard comparison?
                 # Actually, template values should be kept as is but trimmed, 
                 # or normalized same as TCD.
                 # Let's use simple strip.
                norm_parts.append(p.strip())
        
        # Sort to ensure order independence
        norm_parts.sort()
        
        return '|'.join(norm_parts)
    
    @staticmethod
    def normaliser_string(s: Any) -> Optional[str]:
        """
        Normalise une chaîne générique (trim, lowercase).
        
        Args:
            s: Chaîne à normaliser
            
        Returns:
            Chaîne normalisée ou None
        """
        if pd.isna(s):
            return None
        return str(s).strip()


# =============================================================================
# PROCESSEUR AUTOMATIQUE
# =============================================================================

class AutoProcessor:
    """
    Processeur automatique TCD vers Template DHIS2.
    
    Workflow:
    1. Charger template et TCD
    2. Extraire noms exacts depuis le template
    3. Construire mappings dynamiques
    4. Construire index de recherche O(1)
    5. Traiter chaque onglet TCD
    6. Générer rapport détaillé
    """
    
    def __init__(self, metadata: MetadataManager, config: Optional[AutoMappingConfig] = None):
        """
        Initialise le processeur.
        
        Args:
            metadata: MetadataManager avec les métadonnées DHIS2
            config: Configuration des mappings (optionnel)
        """
        self.metadata = metadata
        self.config = config or AutoMappingConfig()
        self.stats = ProcessingStats()
        
        # DataFrames
        self.df_template = None
        self.df_tcd = None
        
        # Mappings construits dynamiquement
        self.mapping_etablissements = {}
        self.mapping_data_elements = {}
        self.index_recherche = {}
        
        logger.info("AutoProcessor initialisé")
    
    def detect_template_columns(self):
        """
        Détecte les noms réels des colonnes dans le template.
        Met à jour la configuration avec les noms trouvés.
        """
        if self.df_template is None:
            return

        def find_col(possible_names, default_idx):
            cols = self.df_template.columns
            # 1. Exact match (case insensitive)
            for name in possible_names:
                for col in cols:
                    if str(col).lower() == name.lower():
                        return col
            
            # 2. Paremter match
            for name in possible_names:
                if name in cols:
                    return name
                    
            # 3. Index fallback
            if len(cols) > default_idx:
                return cols[default_idx]
            return None

        # Section
        self.config.col_section_template = find_col(
            ['Section', 'Groupe', 'Catégorie', 'Category', 'section', 'group'], 0
        )
        
        # Data Element
        self.config.col_data_element_template = find_col(
             ['Data Element', 'Data element', 'dataElementName', 'Element', 'Name'], 1
        )
        
        # Org Unit
        self.config.col_org_unit_template = find_col(
            ['Organisation unit', 'Org unit', 'orgUnitName', 'Organisation', 'Establishment'], 2
        )
        
        # Category Option Combo
        self.config.col_coc_template = find_col(
            ['Category option combo', 'Category option combo name', 'categoryOptionComboName', 'COC', 'Catégorie'], 3
        )

        # Value
        self.config.col_value_template = find_col(
            ['Value', 'value', 'Valeur', 'Nombre'], 4
        )
        
        logger.info(f"Colonnes détectées: Section='{self.config.col_section_template}', DE='{self.config.col_data_element_template}', Org='{self.config.col_org_unit_template}'")

    def load_template(self, template_path: str, sheet_name: str = 'Données'):
        """
        Charge le template DHIS2.
        
        Args:
            template_path: Chemin vers le fichier template Excel
            sheet_name: Nom de l'onglet (défaut: 'Données')
        """
        logger.info(f"Chargement template: {template_path}, sheet: {sheet_name}")
        
        self.df_template = pd.read_excel(
            template_path, 
            sheet_name=sheet_name, 
            header=int(self.config.template_header_row)
        )
        
        self.detect_template_columns()
        
        logger.info(f"Template chargé: {len(self.df_template)} lignes, {len(self.df_template.columns)} colonnes")
        logger.info(f"Colonnes: {self.df_template.columns.tolist()}")
    
    def load_tcd(self, tcd_path: str, sheet_name: str):
        """
        Charge un onglet TCD.
        
        Args:
            tcd_path: Chemin vers le fichier TCD Excel
            sheet_name: Nom de l'onglet à traiter
        """
        logger.info(f"Chargement TCD: {tcd_path}, sheet: {sheet_name}")
        
        self.df_tcd = pd.read_excel(
            tcd_path, 
            sheet_name=sheet_name, 
            header=int(self.config.tcd_header_row)
        )
        
        logger.info(f"TCD chargé: {len(self.df_tcd)} lignes, {len(self.df_tcd.columns)} colonnes")
        logger.info(f"Colonnes: {self.df_tcd.columns.tolist()}")
    
    def build_etablissements_mapping(self):
        """
        Construit le mapping établissements en extrayant les noms EXACTS du template.
        
        Principe clé: Ne jamais coder en dur les noms avec apostrophes.
        Extraire dynamiquement depuis le template pour éviter les problèmes d'encodage.
        """
        logger.info("Construction du mapping établissements...")
        
        # Extraire les noms uniques du template
        noms_template = {
            str(n).strip(): n 
            for n in self.df_template[self.config.col_org_unit_template].unique()
            if pd.notna(n)
        }
        
        logger.info(f"Noms d'organisations dans le template: {len(noms_template)}")
        
        # Construire le mapping avec les patterns fournis
        self.mapping_etablissements = {}
        for acronyme, pattern in self.config.etablissements_patterns.items():
            # CRITIQUE: Toujours stripper la clé de configuration (acronyme TCD)
            clean_acronyme = str(acronyme).strip()
            
            for nom_norm, nom_original in noms_template.items():
                if pattern.lower() in nom_norm.lower():
                    self.mapping_etablissements[clean_acronyme] = nom_original
                    logger.debug(f"Mapping trouvé: '{clean_acronyme}' -> '{nom_original}'")
                    break
        
        logger.info(f"Mappings établissements construits: {len(self.mapping_etablissements)}")
        if len(self.mapping_etablissements) < len(self.config.etablissements_patterns):
            logger.warning("Certains patterns n'ont pas trouvé de correspondance dans le template")

    def build_index_recherche(self):
        """
        Construit un index de recherche rapide basé sur des clés normalisées.
        
        Clé de recherche: "SECTION|DATA_ELEMENT|ETABLISSEMENT|COC_NORMALISE"
        
        Avantages:
        - Recherche O(1) au lieu de O(n)
        - Indépendant des variations de format
        - Facilite le débogage (clés lisibles)
        """
        logger.info("Construction de l'index de recherche...")
        
        # Ajouter colonnes normalisées au template
        self.df_template['_coc_norm'] = self.df_template[self.config.col_coc_template].apply(
            Normalizer.normaliser_coc
        )
        self.df_template['_org_norm'] = self.df_template[self.config.col_org_unit_template].apply(
            lambda x: str(x).strip() if pd.notna(x) else None
        )
        
        # Construire la clé de recherche
        self.df_template['_cle'] = (
            self.df_template[self.config.col_section_template].fillna('').str.strip() + '|' +
            self.df_template[self.config.col_data_element_template].fillna('').str.strip() + '|' +
            self.df_template['_org_norm'].fillna('') + '|' +
            self.df_template['_coc_norm'].fillna('')
        )
        
        # Créer l'index dict {clé: index_ligne}
        self.index_recherche = {
            row['_cle']: idx 
            for idx, row in self.df_template.iterrows()
        }
        
        logger.info(f"Index de recherche construit: {len(self.index_recherche)} clés")
        
        # Afficher quelques exemples de clés pour debug
        exemples = list(self.index_recherche.keys())[:3]
        for cle in exemples:
            logger.debug(f"Exemple de clé: {cle}")
    
    def process_tcd_sheet(self, col_data_element: str, period: str) -> Tuple[List[Dict], ProcessingStats]:
        """
        Traite un onglet TCD et insère les valeurs dans le template.
        
        Points critiques:
        1. Propager les NaN (cellules fusionnées Excel)
        2. Ignorer les lignes "Total"
        3. La dernière colonne contient les valeurs
        4. Construire la clé de recherche normalisée
        5. Collecter les erreurs pour le rapport
        
        Args:
            col_data_element: Nom de la colonne contenant les data elements
            period: Période (ex: '2024', '202401')
            
        Returns:
            Tuple (data_values, stats)
        """
        if self.df_tcd is None:
            raise ValueError("TCD non chargé. Appelez load_tcd() d'abord.")
        
        if self.df_template is None:
            raise ValueError("Template non chargé. Appelez load_template() d'abord.")
        
        logger.info("=" * 80)
        logger.info("DÉBUT DU TRAITEMENT TCD")
        logger.info("=" * 80)
        
        # Réinitialiser les stats
        self.stats = ProcessingStats()
        
        # Supprimer les lignes "Total"
        df = self.df_tcd[~self.df_tcd[self.config.col_etablissement].astype(str).str.contains('Total', na=False, case=False)]
        logger.info(f"Lignes après suppression des totaux: {len(df)}")
        
        # CRITIQUE: Propager les valeurs des cellules fusionnées (fill-down)
        df = df.copy()
        # Propager les valeurs des cellules fusionnées (ffill)
        df = df.copy()
        df[self.config.col_etablissement] = df[self.config.col_etablissement].ffill()
        
        for col in self.config.category_cols:
            if col in df.columns:
                df[col] = df[col].ffill()
        
        logger.info("Cellules fusionnées propagées (ffill)")
        
        col_valeur = df.columns[-1]
        logger.info(f"Colonne valeurs: '{col_valeur}'")
        
        data_values = []
        
        for idx, row in df.iterrows():
            self.stats.lignes_traitees += 1
            
            etab = str(row[self.config.col_etablissement]).strip()
            data_elem = str(row[col_data_element]).strip()
            valeur = row[col_valeur]
            
            if pd.isna(valeur) or valeur == 0 or valeur == '':
                continue
            
            etab_template = self.mapping_etablissements.get(etab)
            if etab_template is None:
                if etab not in self.stats.etablissements_non_mappes:
                    self.stats.etablissements_non_mappes[etab] = 0
                self.stats.etablissements_non_mappes[etab] += int(float(valeur))
                continue
            
            mapping = self.config.data_elements_manuels.get(data_elem)
            if mapping is None:
                if data_elem not in self.stats.data_elements_non_mappes:
                    self.stats.data_elements_non_mappes[data_elem] = 0
                self.stats.data_elements_non_mappes[data_elem] += int(float(valeur))
                continue
            
            section, de_template = mapping
            
            # --- GENERIC COC CONSTRUCTION ---
            normalized_parts = []
            valid_row = True
            
            for col in self.config.category_cols:
                raw_val = row.get(col)
                norm_val = Normalizer.normalize_value(
                    raw_val, 
                    col, 
                    self.config.value_mappings
                )
                
                if norm_val is None:
                    # Special case: If value is missing and we expect it, it might be an aggregate row or error
                    # But if we rely on ffill, it should be there.
                    # Exception: Some columns might be optional? No, usually all required for a COC.
                    valid_row = False
                    break
                
                normalized_parts.append(norm_val)
                
            if not valid_row:
                 continue

            # Sort parts to match Normalizer.normaliser_coc logic
            normalized_parts.sort()
            coc_norm = '|'.join(normalized_parts)
            
            # --------------------------------
            
            cle = f"{section}|{de_template}|{etab_template}|{coc_norm}"
            
            if cle in self.index_recherche:
                idx_template = self.index_recherche[cle]
                
                org_unit_uid = self.df_template.at[idx_template, 'orgUnit']
                data_element_uid = self.df_template.at[idx_template, 'dataElement']
                coc_uid = self.df_template.at[idx_template, 'categoryOptionCombo']
                
                data_value = {
                    'dataElement': data_element_uid,
                    'period': period,
                    'orgUnit': org_unit_uid,
                    'categoryOptionCombo': coc_uid,
                    'value': str(int(float(valeur))),
                    'attributeOptionCombo': 'HllvX50cXC0'
                }
                
                data_values.append(data_value)
                self.stats.valeurs_inserees += 1
                
                if self.stats.valeurs_inserees % 100 == 0:
                    logger.info(f"Valeurs insérées: {self.stats.valeurs_inserees}")
            else:
                self.stats.combinaisons_non_trouvees.append({
                    'cle': cle,
                    'details': {
                        'section': section,
                        'data_element': de_template,
                        'organisation': etab_template,
                        'coc_norm': coc_norm
                    },
                    'valeur': int(float(valeur)),
                    'etablissement': etab,
                    'data_element': data_elem,
                    'coc': coc_norm
                })
        
        logger.info("=" * 80)
        logger.info("FIN DU TRAITEMENT TCD")
        logger.info(f"Lignes traitées: {self.stats.lignes_traitees}")
        logger.info(f"Valeurs insérées: {self.stats.valeurs_inserees}")
        logger.info(f"Établissements non mappés: {len(self.stats.etablissements_non_mappes)}")
        logger.info(f"Data elements non mappés: {len(self.stats.data_elements_non_mappes)}")
        logger.info(f"Combinaisons non trouvées: {len(self.stats.combinaisons_non_trouvees)}")
        logger.info("=" * 80)
        
        return data_values, self.stats

    def analyze_tcd_file(self, tcd_path: str) -> Dict:
        """
        Analyse un fichier TCD et retourne la structure.
        
        Args:
            tcd_path: Chemin vers le fichier TCD Excel
            
        Returns:
            Dict avec informations sur les onglets, colonnes, etc.
        """
        try:
            xl_file = pd.ExcelFile(tcd_path)
            sheets_info = []
            etablissements_uniques = []
            etablissements_avec_codes = {}  # {nom: code}
            
            for idx, sheet_name in enumerate(xl_file.sheet_names):
                df = pd.read_excel(tcd_path, sheet_name=sheet_name, header=int(self.config.tcd_header_row), nrows=100)
                
                # Pour le premier onglet, extraire les établissements uniques avec leurs codes
                if idx == 0:
                    if self.config.col_etablissement in df.columns:
                        # CRITIQUE: Stripper les noms d'établissements extraits
                        etablissements_uniques = sorted([
                            str(v).strip() 
                            for v in df[self.config.col_etablissement].dropna().unique()
                        ])
                    
                    # Extraire aussi les codes si la colonne existe
                    if self.config.col_code_etablissement in df.columns and self.config.col_etablissement in df.columns:
                        for _, row in df.iterrows():
                            nom = str(row.get(self.config.col_etablissement, '')).strip()
                            code = str(row.get(self.config.col_code_etablissement, '')).strip()
                            if nom and code and nom != 'nan' and code != 'nan':
                                etablissements_avec_codes[nom] = code
                
                sheets_info.append({
                    'name': sheet_name,
                    'columns': [str(col) for col in df.columns],
                    'rows': len(df),
                    'sample_values': {
                        str(col): [str(v) for v in df[col].dropna().unique()[:5]]
                        for col in df.columns[:5]  # Première 5 colonnes seulement
                    }
                })
            
            return {
                'success': True,
                'sheet_count': len(sheets_info),
                'sheets': sheets_info,
                'etablissements_uniques': etablissements_uniques,
                'etablissements_avec_codes': etablissements_avec_codes
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse TCD: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_mapping_suggestions(self, sheet_name: str, col_de: str) -> Dict[str, Any]:
        """
        Génère des suggestions de mapping entre les valeurs du TCD et le Template.
        Utilise la distance de Levenshtein sur les textes normalisés.
        """
        if self.df_template is None:
            return {'error': 'Template non chargé'}

        # 1. Extraire les valeurs uniques du TCD
        if not self.config.tcd_path:
             return {'error': 'Chemin TCD non configuré'}
             
        try:
            df = pd.read_excel(self.config.tcd_path, sheet_name=sheet_name, header=int(self.config.tcd_header_row))
            tcd_values = [str(v).strip() for v in df[col_de].dropna().unique() if str(v).strip()]
        except Exception as e:
            return {'error': f"Erreur lecture TCD: {str(e)}"}

        # 2. Préparer les cibles (Template)
        # On veut une liste de (Section, DE Name)
        targets = []
        target_map = {} # (section, de_name) -> original_row
        
        seen = set()
        
        if not self.config.col_section_template or not self.config.col_data_element_template:
             cols = self.df_template.columns.tolist()
             return {'error': f"Colonnes template introuvables. Colonnes dispos: {cols}"}

        for idx, row in self.df_template.iterrows():
            section = str(row[self.config.col_section_template]).strip()
            de_name = str(row[self.config.col_data_element_template]).strip()
            
            key = (section, de_name)
            if key not in seen and section and de_name:
                seen.add(key)
                # Normaliser pour la recherche
                norm_name = Normalizer.normalize_text(de_name)
                # On ajoute aussi le nom brut pour l'affichage
                targets.append({
                    'section': section,
                    'name': de_name,
                    'norm': norm_name
                })

        # 3. Fuzzy Matching
        suggestions = {}
        
        for val in tcd_values:
            val_norm = Normalizer.normalize_text(val)
            if not val_norm:
                continue
                
            best_match = None
            best_score = 0
            
            # Seuil de confiance
            HIGH_CONFIDENCE = 0.85
            MEDIUM_CONFIDENCE = 0.65
            
            for target in targets:
                # Score 1: Ratio sur texte normalisé
                score = difflib.SequenceMatcher(None, val_norm, target['norm']).ratio()
                
                # Bonus: Inclusion (ex: "TOTAL GARCONS" contient "GARCONS")
                if val_norm in target['norm'] or target['norm'] in val_norm:
                    if len(val_norm) > 3 and len(target['norm']) > 3: # Éviter les faux positifs courts
                        score = max(score, 0.7) # Boost
                
                if score > best_score:
                    best_score = score
                    best_match = target
            
            if best_match and best_score >= MEDIUM_CONFIDENCE:
                confidence_level = 'high' if best_score >= HIGH_CONFIDENCE else 'medium'
                suggestions[val] = {
                    'suggested_section': best_match['section'],
                    'suggested_name': best_match['name'],
                    'confidence': confidence_level,
                    'score': round(best_score, 2)
                }
        
        return {
            'success': True,
            'total_tcd': len(tcd_values),
            'mapped_count': len(suggestions),
            'suggestions': suggestions
        }
