"""
Service de calcul et génération de payload DHIS2
=================================================
Traite les fichiers Excel remplis et génère le JSON DHIS2
"""

import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd
from datetime import datetime

from app.services.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


class DataCalculator:
    """
    Calculateur de données DHIS2
    Convertit les données Excel en payload JSON DHIS2
    """
    
    def __init__(self, metadata_manager: MetadataManager):
        """
        Initialise le calculateur

        Args:
            metadata_manager: Instance de MetadataManager
        """
        self.metadata = metadata_manager

    def get_excel_sheets(self, filepath: str) -> List[str]:
        """
        Récupère la liste des onglets d'un fichier Excel

        Args:
            filepath: Chemin du fichier Excel

        Returns:
            Liste des noms d'onglets
        """
        try:
            excel_file = pd.ExcelFile(filepath)
            sheets = excel_file.sheet_names
            logger.info(f"Onglets détectés dans {filepath}: {sheets}")
            return sheets
        except Exception as e:
            logger.error(f"Erreur lecture onglets: {e}")
            raise ValueError(f"Impossible de lire les onglets: {str(e)}")

    def process_template_excel(
        self,
        filepath: str,
        sheet_name: str = "Données",
        mode: str = "normal",
        data_element_id: Optional[str] = None,
        period: Optional[str] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Traite un fichier Excel (mode normal ou tableau croisé)

        Args:
            filepath: Chemin du fichier Excel
            sheet_name: Nom de l'onglet à traiter
            mode: "normal" ou "pivot" (tableau croisé dynamique)
            data_element_id: (Optionnel) ID du data element pour mode pivot mono-DE
            period: (Optionnel) Période pour mode pivot

        Returns:
            Tuple (liste de dataValues, statistiques)
        """
        logger.info(f"[DataCalculator] Traitement du template")
        logger.info(f"  - Filepath: {filepath}")
        logger.info(f"  - Sheet: {sheet_name}")
        logger.info(f"  - Mode: {mode}")
        logger.info(f"  - DE ID: {data_element_id}")
        logger.info(f"  - Period: {period}")

        # Router vers la méthode appropriée selon le mode
        if mode == "pivot":
            # Mode TCD : data_element_id est optionnel (auto-détection depuis la 1ère colonne)
            period_to_use = period or '2024'  # Défaut
            logger.info(f"[DataCalculator] Mode PIVOT détecté, appel _process_pivot_table")
            return self._process_pivot_table(filepath, sheet_name, data_element_id, period_to_use)
        else:
            logger.info(f"[DataCalculator] Mode NORMAL détecté, appel _process_normal_template")
            return self._process_normal_template(filepath, sheet_name)

    def _process_normal_template(self, filepath: str, sheet_name: str) -> Tuple[List[Dict], Dict]:
        """
        Traite un template normal (généré par le TemplateGenerator)

        Args:
            filepath: Chemin du fichier Excel
            sheet_name: Nom de l'onglet

        Returns:
            Tuple (liste de dataValues, statistiques)
        """
        logger.info(f"[_process_normal_template] Début traitement")
        logger.info(f"  - Sheet: {sheet_name}, Skip 5 rows")
        
        # Lire le fichier Excel
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=5)
            logger.info(f"[_process_normal_template] Fichier lu: {len(df)} lignes, colonnes: {list(df.columns)}")
        except Exception as e:
            logger.error(f"[_process_normal_template] ERREUR lecture: {str(e)}")
            raise ValueError(f"Erreur lecture fichier: {str(e)}")

        # Vérifier les colonnes requises (accepter 'value' ou 'VALEUR' pour compatibilité)
        required_cols = ['dataElement', 'period', 'orgUnit', 'categoryOptionCombo', 'attributeOptionCombo']
        missing_core = [col for col in required_cols if col not in df.columns]
        if missing_core:
            raise ValueError(f"Colonnes manquantes: {', '.join(missing_core)}")

        value_col = 'value' if 'value' in df.columns else ('VALEUR' if 'VALEUR' in df.columns else None)
        if not value_col:
            raise ValueError("Colonne manquante: 'value' (ou 'VALEUR')")
        
        # Section column is optional
        section_col = 'section' if 'section' in df.columns else None

        # Filtrer les lignes avec valeur
        df_with_values = df[df[value_col].notna() & (df[value_col] != '')]

        if len(df_with_values) == 0:
            raise ValueError("Aucune valeur trouvée dans la colonne 'VALEUR'. Veuillez remplir au moins une ligne avec une valeur numérique.")

        df = df_with_values

        # Générer les dataValues
        data_values = []
        errors = {
            'invalid_value': 0,
            'missing_data': 0
        }

        for idx, row in df.iterrows():
            try:
                # Valider la valeur
                value = self._parse_value(row[value_col])
                if value is None:
                    errors['invalid_value'] += 1
                    continue

                # Créer le dataValue directement depuis les colonnes techniques
                data_value = {
                    'dataElement': str(row['dataElement']).strip(),
                    'period': str(row['period']).strip(),
                    'orgUnit': str(row['orgUnit']).strip(),
                    'categoryOptionCombo': str(row['categoryOptionCombo']).strip(),
                    'attributeOptionCombo': str(row['attributeOptionCombo']).strip(),
                    'value': str(value)
                }

                # Vérifier que tous les champs sont présents
                if any(not v or v == 'nan' for v in data_value.values()):
                    errors['missing_data'] += 1
                    continue

                data_values.append(data_value)

            except Exception as e:
                logger.warning(f"Erreur ligne {idx}: {e}")
                errors['missing_data'] += 1
                continue

        # Statistiques
        stats = {
            'total_rows': len(df),
            'valid_rows': len(data_values),
            'errors': errors,
            'error_rate': round((sum(errors.values()) / len(df)) * 100, 2) if len(df) > 0 else 0
        }

        logger.info(f"Traitement terminé: {len(data_values)} valeurs valides sur {len(df)}")

        return data_values, stats

    def _process_pivot_table(
        self,
        filepath: str,
        sheet_name: str,
        data_element_id: Optional[str] = None,
        period: str = '2024'
    ) -> Tuple[List[Dict], Dict]:
        """
        Traite un tableau croisé dynamique (TCD)
        Format: Première colonne = noms des indicateurs/data elements
                Autres colonnes = noms des organisations (structures)
                Valeurs = données à importer

        Args:
            filepath: Chemin fichier Excel
            sheet_name: Nom onglet
            data_element_id: (Optionnel) ID unique si toutes les lignes utilisent le même DE
            period: Période (ex: "2024", "202401")

        Returns:
            Tuple (dataValues, stats)
        """
        logger.info(f"[_process_pivot_table] Début traitement TCD")
        logger.info(f"  - Sheet: {sheet_name}")
        logger.info(f"  - Period: {period}")
        logger.info(f"  - DE ID fourni: {data_element_id}")

        # Lire le tableau
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
            logger.info(f"[_process_pivot_table] Fichier lu: {len(df)} lignes, {len(df.columns)} colonnes")
            logger.info(f"[_process_pivot_table] Colonnes: {list(df.columns)}")
        except Exception as e:
            logger.error(f"[_process_pivot_table] ERREUR lecture: {str(e)}")
            raise ValueError(f"Erreur lecture onglet '{sheet_name}': {str(e)}")

        if len(df) == 0:
            logger.error(f"[_process_pivot_table] L'onglet est VIDE")
            raise ValueError("L'onglet est vide")

        data_values = []
        errors = {
            'org': 0,
            'value': 0,
            'de_not_found': 0,
            'de_name_empty': 0
        }

        # Première colonne = indicateurs/data elements
        indicator_col = df.columns[0]
        # Autres colonnes = noms des structures
        org_columns = df.columns[1:]

        default_coc = self.metadata.coc_lookup.get("default", "")
        default_aoc = self.metadata.coc_lookup.get("default", "")

        logger.info(f"TCD détecté: {len(df)} indicateurs x {len(org_columns)} organisations")

        for idx, row in df.iterrows():
            # Récupérer le nom de l'indicateur/data element
            indicator_name = str(row[indicator_col]).strip()
            
            if not indicator_name or indicator_name == '' or indicator_name.lower() == 'nan':
                errors['de_name_empty'] += 1
                continue

            # Résoudre le data element
            if data_element_id:
                # Mode mono-DE : utiliser l'ID fourni pour toutes les lignes
                de_id = data_element_id
            else:
                # Mode multi-DE : chercher le DE par son nom
                de_id = self.metadata.de_name_to_id.get(indicator_name.lower())
                
                if not de_id:
                    errors['de_not_found'] += 1
                    logger.warning(f"Data element non trouvé: '{indicator_name}'")
                    continue

            # Pour chaque organisation (colonne)
            for org_col in org_columns:
                value = row[org_col]

                # Ignorer valeurs vides
                if pd.isna(value) or str(value).strip() == '':
                    continue

                # Résoudre organisation
                org_name = str(org_col).strip()
                org_key = org_name.lower()

                # Essayer par code d'abord
                org_id = self.metadata.org_code_to_id.get(org_key)

                # Fallback sur le nom
                if not org_id:
                    org_id = self.metadata.org_name_to_id.get(org_key)

                if not org_id:
                    errors['org'] += 1
                    logger.warning(f"Organisation inconnue: {org_name}")
                    continue

                # Valider valeur
                val = self._parse_value(value)
                if val is None:
                    errors['value'] += 1
                    continue

                # Créer dataValue
                data_values.append({
                    'dataElement': de_id,
                    'period': period,
                    'orgUnit': org_id,
                    'categoryOptionCombo': default_coc,
                    'attributeOptionCombo': default_aoc,
                    'value': str(int(val) if val.is_integer() else val)
                })

        stats = {
            'total_rows': len(df),
            'total_columns': len(org_columns),
            'valid_rows': len(data_values),
            'unique_data_elements': len(set(dv['dataElement'] for dv in data_values)),
            'errors': errors,
            'error_rate': round((sum(errors.values()) / (len(df) * len(org_columns))) * 100, 2) if len(df) > 0 else 0
        }

        logger.info(f"TCD traité: {len(data_values)} valeurs valides, {stats['unique_data_elements']} data elements")

        return data_values, stats

    def process_custom_excel(
        self, 
        filepath: str, 
        column_mapping: Dict[str, str],
        dataset_id: str,
        default_period: Optional[str] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Traite un fichier Excel personnalisé (non-template)
        
        Args:
            filepath: Chemin du fichier
            column_mapping: Mapping des colonnes (ex: {'org': 'Structure', 'indicator': 'Indicateur'})
            dataset_id: ID du dataset
            default_period: Période par défaut si non présente dans le fichier
            
        Returns:
            Tuple (liste de dataValues, statistiques)
        """
        logger.info(f"Traitement fichier personnalisé: {filepath}")
        
        # Lire le fichier
        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            raise ValueError(f"Erreur lecture fichier: {str(e)}")
        
        # Vérifier le mapping
        required_mappings = ['org', 'indicator', 'value']
        missing = [m for m in required_mappings if m not in column_mapping]
        if missing:
            raise ValueError(f"Mapping manquant: {', '.join(missing)}")
        
        # Vérifier que les colonnes existent
        for key, col in column_mapping.items():
            if col not in df.columns:
                raise ValueError(f"Colonne '{col}' introuvable dans le fichier")
        
        # Récupérer le dataset
        dataset = self._get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} introuvable")
        
        allowed_de_ids = set(e['dataElement']['id'] for e in dataset.get('dataSetElements', []))
        
        # Préparer les données
        df = df.fillna("")
        
        # Colonnes pour le groupement
        group_cols = [column_mapping['org'], column_mapping['indicator']]
        
        # Ajouter les catégories si présentes
        category_cols = {}
        for key, col in column_mapping.items():
            if key.startswith('cat_'):
                group_cols.append(col)
                category_cols[key] = col
        
        # Grouper les données
        value_col = column_mapping['value']
        grouped = df.groupby(group_cols)[value_col].sum().reset_index()
        
        logger.info(f"Données groupées: {len(grouped)} combinaisons")
        
        # Générer les dataValues
        data_values = []
        errors = {
            'org_not_found': 0,
            'indicator_not_found': 0,
            'coc_not_found': 0,
            'invalid_value': 0
        }
        
        default_aoc = self.metadata.coc_lookup.get("default", "")
        
        for _, row in grouped.iterrows():
            # Résoudre l'organisation (d'abord par code, puis par nom)
            org_value = str(row[column_mapping['org']]).strip()
            org_key = org_value.lower()

            # Essayer d'abord par code (plus fiable)
            org_id = self.metadata.org_code_to_id.get(org_key)

            # Fallback sur le nom si code non trouvé
            if not org_id:
                org_id = self.metadata.org_name_to_id.get(org_key)

            if not org_id:
                errors['org_not_found'] += 1
                logger.warning(f"Organisation non trouvée: {org_value}")
                continue
            
            # Résoudre l'indicateur
            ind_name = str(row[column_mapping['indicator']]).strip()
            de_id = self.metadata.de_name_to_id.get(ind_name.lower())
            
            if not de_id or de_id not in allowed_de_ids:
                errors['indicator_not_found'] += 1
                continue
            
            # Résoudre le COC
            data_element = self.metadata.data_elements_map[de_id]
            cc_id = data_element.get('categoryCombo', {}).get('id')
            
            coc_id = self._resolve_coc(cc_id, row, category_cols, column_mapping)
            
            if not coc_id:
                errors['coc_not_found'] += 1
                continue
            
            # Valider la valeur
            value = self._parse_value(row[value_col])
            if value is None:
                errors['invalid_value'] += 1
                continue
            
            # Période
            period = default_period
            if 'period' in column_mapping and column_mapping['period'] in df.columns:
                period = str(row[column_mapping['period']]).strip()
            
            if not period:
                logger.warning("Période manquante, ligne ignorée")
                continue
            
            # Créer le dataValue
            data_value = {
                'dataElement': de_id,
                'period': period,
                'orgUnit': org_id,
                'categoryOptionCombo': coc_id,
                'attributeOptionCombo': default_aoc,
                'value': str(value)
            }
            
            data_values.append(data_value)
        
        # Statistiques
        stats = {
            'total_rows': len(grouped),
            'valid_rows': len(data_values),
            'errors': errors,
            'error_rate': round((sum(errors.values()) / len(grouped)) * 100, 2) if len(grouped) > 0 else 0
        }
        
        logger.info(f"Traitement terminé: {len(data_values)} valeurs valides sur {len(grouped)}")
        
        return data_values, stats
    
    def _resolve_coc(
        self, 
        cc_id: Optional[str], 
        row: pd.Series, 
        category_cols: Dict[str, str],
        column_mapping: Dict[str, str]
    ) -> Optional[str]:
        """
        Résout le categoryOptionCombo avec fuzzy matching
        
        Args:
            cc_id: ID du category combo
            row: Ligne de données
            category_cols: Colonnes de catégories
            column_mapping: Mapping des colonnes
            
        Returns:
            ID du COC ou None
        """
        # Si pas de combo ou combo par défaut
        if not cc_id:
            return self.metadata.coc_lookup.get("default")
        
        cat_combo = self.metadata.cat_combos.get(cc_id)
        if not cat_combo or cat_combo.get('name') == 'default':
            return self.metadata.coc_lookup.get("default")
        
        # Récupérer les options de catégories
        options = []
        for cat in cat_combo.get('categories', []):
            cat_id = cat['id']
            
            # Trouver la colonne correspondante
            cat_col = None
            for key, col in category_cols.items():
                if key == f'cat_{cat_id}':
                    cat_col = col
                    break
            
            if cat_col and cat_col in row.index:
                val = str(row[cat_col]).strip()
                val = self._normalize_category_value(val)
                if val:
                    options.append(val)
        
        # Utiliser le fuzzy matching
        if options:
            coc_name = " | ".join(sorted(options))
            coc_id = self.metadata.get_coc_uid_fuzzy(coc_name)
            if coc_id:
                return coc_id
            
            # Tenter avec "," comme séparateur alternatif
            coc_name_alt = ", ".join(sorted(options))
            coc_id = self.metadata.get_coc_uid_fuzzy(coc_name_alt)
            if coc_id:
                return coc_id
        
        return self.metadata.coc_lookup.get("default")
    
    def _normalize_category_value(self, value: str) -> str:
        """
        Normalise une valeur de catégorie
        
        Args:
            value: Valeur brute
            
        Returns:
            Valeur normalisée
        """
        v = value.lower()
        
        # Normalisation pour le sexe
        if v in ['masculin', 'homme', 'male', 'm', 'h']:
            return 'M'
        if v in ['feminin', 'féminin', 'femme', 'female', 'f']:
            return 'F'
        
        # Autres normalisations possibles
        return value.title()
    
    def _parse_value(self, value) -> Optional[float]:
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
    
    def _get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Récupère un dataset par son ID"""
        return next(
            (ds for ds in self.metadata.datasets if ds.get('id') == dataset_id),
            None
        )
    
    def generate_dhis2_payload(self, data_values: List[Dict]) -> Dict:
        """
        Génère le payload JSON final pour DHIS2
        
        Args:
            data_values: Liste des dataValues
            
        Returns:
            Payload JSON DHIS2
        """
        return {
            "dataValues": data_values
        }
    
    def validate_payload(self, payload: Dict) -> Tuple[bool, List[str]]:
        """
        Valide un payload DHIS2
        
        Args:
            payload: Payload à valider
            
        Returns:
            Tuple (valide, liste d'erreurs)
        """
        errors = []
        
        if 'dataValues' not in payload:
            errors.append("Champ 'dataValues' manquant")
            return False, errors
        
        data_values = payload['dataValues']
        
        if not isinstance(data_values, list):
            errors.append("'dataValues' doit être une liste")
            return False, errors
        
        if len(data_values) == 0:
            errors.append("'dataValues' est vide")
            return False, errors
        
        # Valider chaque dataValue
        required_fields = ['dataElement', 'period', 'orgUnit', 'categoryOptionCombo', 'value']
        
        for idx, dv in enumerate(data_values[:10]):  # Vérifier les 10 premiers
            missing = [f for f in required_fields if f not in dv]
            if missing:
                errors.append(f"DataValue {idx}: champs manquants {missing}")
        
        return len(errors) == 0, errors
