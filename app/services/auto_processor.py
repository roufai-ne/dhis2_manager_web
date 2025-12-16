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
    
    # Colonnes standard TCD
    col_etablissement: str = 'NOM_ETAB'
    col_code_etablissement: str = 'CODE_ETAB'
    col_age: str = 'GROUP_AGE'
    col_sexe: str = 'SEXE'


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
    def normaliser_coc(coc: Any) -> Optional[str]:
        """
        Normalise un CategoryOptionCombo.
        
        Formats d'entrée possibles:
        - 'F | [20 - 22[' → 'F|20-22'
        - 'M | [22- 24[\t' → 'M|22-24'
        - '- 18 ans | F' → 'F|-18'
        - '40 ans +\t | M' → 'M|40+'
        
        Algorithme:
        1. Supprimer tabs et normaliser espaces
        2. Détecter le format (SEXE | AGE ou AGE | SEXE)
        3. Extraire sexe et âge
        4. Normaliser l'âge
        5. Retourner 'SEXE|AGE_NORMALISE'
        
        Args:
            coc: CategoryOptionCombo à normaliser
            
        Returns:
            COC normalisé 'SEXE|AGE' ou None
        """
        if pd.isna(coc):
            return None
            
        s = str(coc).strip().replace('\t', ' ')
        s = re.sub(r'\s+', ' ', s)
        
        # Format 1: "X | [NN - NN["
        match1 = Normalizer.PATTERN_COC_FORMAT1.match(s)
        if match1:
            sexe = match1.group(1)
            age = Normalizer.normaliser_tranche_age(match1.group(2))
            return f"{sexe}|{age}" if age else None
        
        # Format 2: "- 18 ans | X" ou "40 ans + | X"
        match2 = Normalizer.PATTERN_COC_FORMAT2.match(s)
        if match2:
            age = Normalizer.normaliser_tranche_age(match2.group(1))
            sexe = match2.group(2)
            return f"{sexe}|{age}" if age else None
        
        return s
    
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
            for n in self.df_template['orgUnitName'].unique()
            if pd.notna(n)
        }
        
        logger.info(f"Noms d'organisations dans le template: {len(noms_template)}")
        
        # Construire le mapping avec les patterns fournis
        self.mapping_etablissements = {}
        for acronyme, pattern in self.config.etablissements_patterns.items():
            for nom_norm, nom_original in noms_template.items():
                if pattern.lower() in nom_norm.lower():
                    self.mapping_etablissements[acronyme] = nom_original
                    logger.debug(f"Mapping trouvé: '{acronyme}' -> '{nom_original}'")
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
        self.df_template['_coc_norm'] = self.df_template['categoryOptionComboName'].apply(
            Normalizer.normaliser_coc
        )
        self.df_template['_org_norm'] = self.df_template['orgUnitName'].apply(
            lambda x: str(x).strip() if pd.notna(x) else None
        )
        
        # Construire la clé de recherche
        self.df_template['_cle'] = (
            self.df_template['section'].fillna('').str.strip() + '|' +
            self.df_template['dataElementName'].fillna('').str.strip() + '|' +
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
        df[self.config.col_etablissement] = df[self.config.col_etablissement].ffill()
        df[self.config.col_age] = df[self.config.col_age].ffill()
        df[self.config.col_sexe] = df[self.config.col_sexe].ffill()
        
        logger.info("Cellules fusionnées propagées (ffill)")
        
        # Dernière colonne = valeurs
        col_valeur = df.columns[-1]
        logger.info(f"Colonne valeurs: '{col_valeur}'")
        
        # Initialiser la liste des dataValues
        data_values = []
        
        # Traiter chaque ligne
        for idx, row in df.iterrows():
            self.stats.lignes_traitees += 1
            
            etab = str(row[self.config.col_etablissement]).strip()
            age = row[self.config.col_age]
            sexe = row[self.config.col_sexe]
            data_elem = str(row[col_data_element]).strip()
            valeur = row[col_valeur]
            
            # Ignorer les lignes sans valeur
            if pd.isna(valeur) or valeur == 0 or valeur == '':
                continue
            
            # Mapper l'établissement
            etab_template = self.mapping_etablissements.get(etab)
            if etab_template is None:
                # Comptabiliser l'erreur
                if etab not in self.stats.etablissements_non_mappes:
                    self.stats.etablissements_non_mappes[etab] = 0
                self.stats.etablissements_non_mappes[etab] += int(float(valeur))
                continue
            
            # Mapper le data element
            mapping = self.config.data_elements_manuels.get(data_elem)
            if mapping is None:
                # Comptabiliser l'erreur
                if data_elem not in self.stats.data_elements_non_mappes:
                    self.stats.data_elements_non_mappes[data_elem] = 0
                self.stats.data_elements_non_mappes[data_elem] += int(float(valeur))
                continue
            
            section, de_template = mapping
            
            # Construire le COC normalisé
            sexe_norm = str(sexe).strip().upper()
            age_norm = Normalizer.normaliser_tranche_age(age)
            
            if not age_norm:
                logger.warning(f"Âge non normalisable: '{age}'")
                continue
            
            coc_norm = f"{sexe_norm}|{age_norm}"
            
            # Construire la clé et rechercher
            cle = f"{section}|{de_template}|{etab_template}|{coc_norm}"
            
            if cle in self.index_recherche:
                idx_template = self.index_recherche[cle]
                
                # Récupérer les UIDs depuis le template
                org_unit_uid = self.df_template.at[idx_template, 'orgUnit']
                data_element_uid = self.df_template.at[idx_template, 'dataElement']
                coc_uid = self.df_template.at[idx_template, 'categoryOptionCombo']
                
                # Créer le dataValue
                data_value = {
                    'dataElement': data_element_uid,
                    'period': period,
                    'orgUnit': org_unit_uid,
                    'categoryOptionCombo': coc_uid,
                    'value': str(int(float(valeur))),
                    'attributeOptionCombo': 'HllvX50cXC0'  # Default COC
                }
                
                data_values.append(data_value)
                self.stats.valeurs_inserees += 1
                
                # Log tous les 100 valeurs
                if self.stats.valeurs_inserees % 100 == 0:
                    logger.info(f"Valeurs insérées: {self.stats.valeurs_inserees}")
            else:
                # Combinaison non trouvée
                self.stats.combinaisons_non_trouvees.append({
                    'cle': cle,
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
                        etablissements_uniques = sorted([str(v) for v in df[self.config.col_etablissement].dropna().unique()])
                    
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
