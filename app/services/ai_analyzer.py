import os
import json
import pandas as pd
import anthropic
from typing import Dict, Any, Optional

class AIAnalysisService:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Fallback for development if not yet in env
            # raise ValueError("ANTHROPIC_API_KEY not found")
            print("WARNING: ANTHROPIC_API_KEY not found")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-7-sonnet-20250219"
    
    def _convert_to_serializable(self, value):
        """Convert pandas types to Python native types"""
        if pd.isna(value):
            return None
        if isinstance(value, (pd.Int64Dtype, pd.Int32Dtype)):
            return int(value)
        if hasattr(value, 'item'):  # numpy types
            return value.item()
        return value

    def analyze_excel(self, file_path: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyzes the first few rows of an Excel file to suggest mapping configuration.
        Can detect pivoted format where data elements are values in columns.
        
        Args:
            file_path: Path to Excel file
            metadata: Optional DHIS2 metadata for enhanced matching
        """
        try:
            # Read all rows for better analysis (pivoted data needs full context)
            df = pd.read_excel(file_path)
            
            # Prepare context for AI
            columns = list(df.columns)
            
            # Analyze column content types
            column_analysis = {}
            for col in columns:
                # Convert pandas types to Python native types for JSON serialization
                sample_values = df[col].dropna().head(10).tolist()
                sample_values = [self._convert_to_serializable(v) for v in sample_values]
                
                dtype = str(df[col].dtype)
                unique_count = int(df[col].nunique())
                null_count = int(df[col].isna().sum())
                
                column_analysis[col] = {
                    "sample_values": sample_values,
                    "dtype": dtype,
                    "unique_count": unique_count,
                    "null_count": null_count
                }
            
            print(f"DEBUG: Analyzing {len(columns)} columns with {len(df)} rows")
            
            prompt = f"""Tu es un expert en analyse de données DHIS2. Analyse ce fichier Excel pour déterminer le mapping optimal.

COLONNES DISPONIBLES: {columns}

ANALYSE DÉTAILLÉE DES COLONNES:
{json.dumps(column_analysis, indent=2, ensure_ascii=False)}

OBJECTIF: Identifier le mapping correct pour l'importation DHIS2.

=== MODE DE TRAITEMENT ===
Détermine le mode approprié:

1. MODE "values" (Données agrégées):
   - Utilisé quand il y a UNE colonne contenant des valeurs numériques déjà calculées
   - Mots-clés typiques: "Nombre", "Total", "Valeur", "Value", "Count", "Effectif", "Quantité"
   - Exemple: Une ligne = un total pour une combinaison (Structure + Période + Indicateur)
   
2. MODE "count" (Comptage individuel):
   - Utilisé quand CHAQUE LIGNE représente un cas/événement unique à compter
   - Pas de colonne de valeur agrégée
   - Exemple: Une ligne = un patient, une consultation, un cas

=== MAPPING DES COLONNES ===

Identifie ces colonnes OBLIGATOIRES:

1. **org_unit** (Unité d'organisation) - OBLIGATOIRE:
   Mots-clés: "Structure", "FOSA", "Centre", "Hôpital", "District", "Formation sanitaire", 
             "Facility", "Organisation unit", "OU", "UID"
   Contient: Noms de structures de santé ou codes UID

2. **period** (Période) - OBLIGATOIRE:
   Mots-clés: "Période", "Date", "Mois", "Année", "Trimestre", "Year", "Month", "Quarter", "Period", "PE"
   Contient: Dates, années (2023, 2024), mois (janvier, 01), trimestres (Q1, T1)

3. **data_element** (Élément de donnée) - OBLIGATOIRE:
   Mots-clés: "Indicateur", "Élément", "Service", "Maladie", "Activité", "Data Element", "DE", "DX"
   Contient: Noms d'indicateurs ou de services de santé

4. **value** (Valeur numérique) - UNIQUEMENT si mode "values":
   Mots-clés: "Nombre", "Total", "Valeur", "Value", "Count", "Effectif", "Quantité"
   Contient: Nombres, valeurs numériques agrégées
   Type: int64, float64
   
5. **categories** (Catégories/Désagrégations) - OPTIONNEL:
   Mots-clés: "Sexe", "Genre", "Âge", "Tranche d'âge", "Type", "Catégorie", "Category"
   Contient: Désagrégations (H/F, 0-5 ans, etc.)
   Critère: Colonnes avec peu de valeurs uniques (< 20)

6. **section** (Section du dataset) - OPTIONNEL:
   Mots-clés: "Section", "Rubrique", "Groupe", "Chapitre", "Domaine"
   Contient: Noms de groupes ou sections logiques du formulaire
   Critère: Rarement présent dans les données brutes, plus courant en templates
   Utilité: Organise les données selon la structure du formulaire DHIS2

=== RÈGLES DE DÉCISION ===

1. Cherche d'ABORD les colonnes contenant des mots-clés exacts
2. Analyse le CONTENU des colonnes (valeurs) pour confirmer
3. Vérifie la COHÉRENCE: 
   - org_unit doit avoir des noms de structures
   - period doit avoir des dates/années
   - value doit être numérique
4. Si AUCUNE colonne "value" n'existe → mode "count"
5. Les colonnes avec peu de valeurs uniques (< 20) sont probablement des catégories

RÉPONDS UNIQUEMENT avec un objet JSON (SANS markdown, SANS ```):
{{
    "processing_mode": "values" ou "count",
    "confidence": 0.0 à 1.0,
    "reasoning": "Explication détaillée EN FRANÇAIS: pourquoi ce mode? Pourquoi ces colonnes? Quels indices ont guidé le choix? Incluez mention de sections si détectées.",
    "mapping": {{
        "org_unit": "nom_exact_colonne" ou null,
        "period": "nom_exact_colonne" ou null,
        "data_element": "nom_exact_colonne" ou null,
        "value": "nom_exact_colonne" ou null,
        "section": "nom_exact_colonne" ou null,
        "categories": ["colonne1", "colonne2"] ou []
    }},
    "warnings": ["Liste de problèmes potentiels détectés"]
}}

IMPORTANT: Les noms de colonnes doivent correspondre EXACTEMENT aux colonnes du fichier."""
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,  # Increased for more detailed analysis
                temperature=0.3,  # Lower temperature for more consistent results
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text content
            text = message.content[0].text
            
            # Clean response (remove markdown code blocks if present)
            text = text.replace('```json', '').replace('```', '').strip()
            print(f"DEBUG: AI Response: {text}")
            
            result = json.loads(text)
            
            # Validate the mapping
            validation_errors = self._validate_mapping(result, columns)
            if validation_errors:
                result['warnings'] = result.get('warnings', []) + validation_errors
                result['confidence'] = max(0.3, result.get('confidence', 0.5) - 0.2)
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"AI Analysis Error: {error_msg}")
            
            # Fallback to heuristic analysis if AI fails
            print("Falling back to heuristic analysis...")
            return self._heuristic_analysis(file_path)
    
    def _validate_mapping(self, result: Dict[str, Any], columns: list) -> list:
        """Validate that mapped columns exist and make sense"""
        errors = []
        mapping = result.get('mapping', {})
        
        # Check that mapped columns exist
        for key, value in mapping.items():
            if value and key != 'categories':
                if value not in columns:
                    errors.append(f"Colonne mappée '{value}' pour '{key}' n'existe pas")
            elif key == 'categories' and isinstance(value, list):
                for cat in value:
                    if cat not in columns:
                        errors.append(f"Colonne catégorie '{cat}' n'existe pas")
        
        # Check required fields
        if not mapping.get('org_unit'):
            errors.append("Colonne 'org_unit' (unité d'organisation) non identifiée")
        if not mapping.get('period'):
            errors.append("Colonne 'period' (période) non identifiée")
        if not mapping.get('data_element'):
            errors.append("Colonne 'data_element' (élément de donnée) non identifiée")
        
        # Check value column for 'values' mode
        if result.get('processing_mode') == 'values' and not mapping.get('value'):
            errors.append("Mode 'values' nécessite une colonne 'value' (valeur numérique)")
        
        return errors
    
    def _heuristic_analysis(self, file_path: str) -> Dict[str, Any]:
        """Fallback heuristic analysis when AI fails"""
        try:
            df = pd.read_excel(file_path, nrows=15)
            columns = list(df.columns)
            
            mapping = {
                'org_unit': None,
                'period': None,
                'data_element': None,
                'value': None,
                'section': None,
                'categories': []
            }
            
            # Keywords for column identification
            org_unit_keywords = ['structure', 'fosa', 'centre', 'hôpital', 'hospital', 'district', 
                                'facility', 'organisation', 'org unit', 'ou']
            period_keywords = ['période', 'period', 'date', 'mois', 'month', 'année', 'year', 
                              'trimestre', 'quarter', 'pe']
            data_element_keywords = ['indicateur', 'indicator', 'élément', 'element', 'service', 
                                    'maladie', 'disease', 'activité', 'activity', 'de', 'dx']
            value_keywords = ['nombre', 'total', 'valeur', 'value', 'count', 'effectif', 
                            'quantité', 'quantity']
            section_keywords = ['section', 'rubrique', 'groupe', 'group', 'chapitre', 'chapter', 
                               'domaine', 'domain']
            category_keywords = ['sexe', 'genre', 'gender', 'âge', 'age', 'tranche', 'type', 
                               'catégorie', 'category']
            
            # Try to match columns
            for col in columns:
                col_lower = str(col).lower()
                
                # Check org_unit
                if not mapping['org_unit'] and any(kw in col_lower for kw in org_unit_keywords):
                    mapping['org_unit'] = col
                    continue
                
                # Check period
                if not mapping['period'] and any(kw in col_lower for kw in period_keywords):
                    mapping['period'] = col
                    continue
                
                # Check data_element
                if not mapping['data_element'] and any(kw in col_lower for kw in data_element_keywords):
                    mapping['data_element'] = col
                    continue
                
                # Check section
                if not mapping['section'] and any(kw in col_lower for kw in section_keywords):
                    mapping['section'] = col
                    continue
                
                # Check value (must be numeric)
                if not mapping['value'] and any(kw in col_lower for kw in value_keywords):
                    if pd.api.types.is_numeric_dtype(df[col]):
                        mapping['value'] = col
                        continue
                
                # Check categories (few unique values)
                if any(kw in col_lower for kw in category_keywords):
                    unique_count = df[col].nunique()
                    if unique_count < 20:
                        mapping['categories'].append(col)
            
            # Determine processing mode
            processing_mode = 'values' if mapping['value'] else 'count'
            
            # Calculate confidence
            required_fields = ['org_unit', 'period', 'data_element']
            if processing_mode == 'values':
                required_fields.append('value')
            
            found_fields = sum(1 for field in required_fields if mapping.get(field))
            confidence = found_fields / len(required_fields)
            
            warnings = []
            if confidence < 1.0:
                missing = [f for f in required_fields if not mapping.get(f)]
                warnings.append(f"Colonnes manquantes: {', '.join(missing)}")
            
            return {
                "success": True,
                "processing_mode": processing_mode,
                "confidence": confidence,
                "reasoning": f"Analyse heuristique (fallback). Colonnes identifiées par mots-clés. Confiance: {confidence:.0%}",
                "mapping": mapping,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur heuristique: {str(e)}"
            }
    
    def extract_pivoted_data_elements(self, file_path: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extrait les data elements d'un fichier Excel au format pivoté.
        
        Format attendu: Les data elements sont les VALEURS dans les colonnes, pas les noms des colonnes.
        Exemple:
        | Cycle     | Nationalité | OrgUnit | Period | Value |
        |-----------|-------------|---------|--------|-------|
        | 1er cycle | Niger       | Niamey  | 2024   | 100   |
        | 2e cycle  | Benin       | Niamey  | 2024   | 150   |
        
        Ici "1er cycle", "2e cycle" sont des data elements DHIS2 (valeurs dans colonne "Cycle")
        
        Returns:
            Dict avec les data elements extraits et matchés avec DHIS2
        """
        try:
            df = pd.read_excel(file_path)
            columns = list(df.columns)
            
            print(f"\n[PIVOTED] Analyse du fichier: {len(df)} lignes, {len(columns)} colonnes")
            print(f"[PIVOTED] Colonnes trouvées: {columns}")
            
            # Récupérer les DE DHIS2 du dataset si metadata fourni
            dhis2_de_names = {}  # nom_lower -> {id, name, section}
            if metadata:
                dataset_id = metadata.get('dataset_id')
                if dataset_id and 'data_elements_map' in metadata:
                    # Construire un index des DE par nom (lowercase pour matching)
                    for de_id, de_info in metadata['data_elements_map'].items():
                        de_name = de_info.get('name') or de_info.get('displayName', '')
                        de_name_lower = de_name.lower().strip()
                        
                        # Trouver la section du DE
                        de_section = None
                        if 'de_to_section' in metadata and de_id in metadata['de_to_section']:
                            section_info = metadata['de_to_section'][de_id]
                            de_section = section_info.get('name')
                        
                        dhis2_de_names[de_name_lower] = {
                            'id': de_id,
                            'name': de_name,
                            'section': de_section
                        }
                    
                    print(f"[PIVOTED] {len(dhis2_de_names)} data elements DHIS2 chargés pour matching")
                else:
                    print("[PIVOTED] WARNING: Pas de metadata DHIS2 disponible - matching impossible")
            
            # Identifier les colonnes système (ne pas les analyser)
            system_keywords = ['structure', 'fosa', 'centre', 'hôpital', 'hospital', 'district',
                             'facility', 'organisation', 'org', 'ou', 'période', 'period', 
                             'date', 'mois', 'month', 'année', 'year', 'trimestre', 'quarter',
                             'nombre', 'total', 'valeur', 'value', 'count', 'effectif', 
                             'quantité', 'quantity', 'pe']
            
            section_col = None
            de_columns = []
            system_columns = []
            
            # Identifier la colonne section
            for col in columns:
                col_lower = str(col).lower()
                if any(kw in col_lower for kw in ['section', 'rubrique', 'groupe', 'chapitre', 'domaine']):
                    section_col = col
                    break
            
            # Analyser chaque colonne pour voir si elle contient des DE DHIS2
            for col in columns:
                if col == section_col:
                    continue
                    
                col_lower = str(col).lower()
                
                # Vérifier si c'est une colonne système
                is_system = any(kw in col_lower for kw in system_keywords)
                is_numeric = pd.api.types.is_numeric_dtype(df[col])
                
                if is_system or is_numeric:
                    system_columns.append(col)
                    print(f"[PIVOTED] '{col}' → Colonne système (keyword match ou numérique)")
                else:
                    # Vérifier si les valeurs de cette colonne matchent des DE DHIS2
                    unique_values = df[col].dropna().unique()
                    matched_count = 0
                    matched_examples = []
                    
                    if dhis2_de_names:
                        # Compter combien de valeurs matchent des DE DHIS2
                        for val in unique_values:
                            val_lower = str(val).strip().lower()
                            if val_lower and val_lower != '-' and val_lower in dhis2_de_names:
                                matched_count += 1
                                if len(matched_examples) < 3:
                                    matched_examples.append(str(val))
                        
                        # Si au moins 1 valeur match, c'est une colonne DE
                        if matched_count > 0:
                            de_columns.append(col)
                            print(f"[PIVOTED] '{col}' → Colonne DE ({matched_count}/{len(unique_values)} valeurs matchées)")
                            print(f"           Exemples matchés: {', '.join(matched_examples)}")
                        else:
                            system_columns.append(col)
                            print(f"[PIVOTED] '{col}' → Colonne système (aucun match avec DE DHIS2)")
                    else:
                        # Sans metadata, deviner basé sur les valeurs non nulles
                        if len(unique_values) > 0:
                            de_columns.append(col)
                            print(f"[PIVOTED] '{col}' → Colonne DE potentielle ({len(unique_values)} valeurs uniques)")
            
            # Extraire les data elements qui matchent DHIS2
            sections_mapping = {}
            all_data_elements = []
            unmatched_values = []
            
            if section_col:
                # Grouper par section
                for section_name in df[section_col].dropna().unique():
                    section_rows = df[df[section_col] == section_name]
                    section_des = []
                    
                    for de_col in de_columns:
                        unique_values = section_rows[de_col].dropna().unique()
                        for val in unique_values:
                            val_str = str(val).strip()
                            if val_str and val_str != '-':
                                val_lower = val_str.lower()
                                
                                # Chercher dans DHIS2 DE
                                dhis2_match = dhis2_de_names.get(val_lower) if dhis2_de_names else None
                                
                                de_info = {
                                    'name': val_str,
                                    'column': de_col,
                                    'section': section_name,
                                    'dhis2_matched': dhis2_match is not None
                                }
                                
                                if dhis2_match:
                                    de_info['dhis2_id'] = dhis2_match['id']
                                    de_info['dhis2_name'] = dhis2_match['name']
                                    de_info['dhis2_section'] = dhis2_match['section']
                                else:
                                    unmatched_values.append(val_str)
                                
                                section_des.append(de_info)
                                all_data_elements.append(de_info)
                    
                    if section_des:
                        sections_mapping[section_name] = section_des
            else:
                # Pas de section, regrouper par colonne DE
                for de_col in de_columns:
                    unique_values = df[de_col].dropna().unique()
                    col_des = []
                    
                    for val in unique_values:
                        val_str = str(val).strip()
                        if val_str and val_str != '-':
                            val_lower = val_str.lower()
                            
                            # Chercher dans DHIS2 DE
                            dhis2_match = dhis2_de_names.get(val_lower) if dhis2_de_names else None
                            
                            de_info = {
                                'name': val_str,
                                'column': de_col,
                                'section': de_col,
                                'dhis2_matched': dhis2_match is not None
                            }
                            
                            if dhis2_match:
                                de_info['dhis2_id'] = dhis2_match['id']
                                de_info['dhis2_name'] = dhis2_match['name']
                                de_info['dhis2_section'] = dhis2_match['section']
                            else:
                                unmatched_values.append(val_str)
                            
                            col_des.append(de_info)
                            all_data_elements.append(de_info)
                    
                    if col_des:
                        sections_mapping[de_col] = col_des
            
            # Statistiques
            total_des = len(all_data_elements)
            total_sections = len(sections_mapping)
            matched_des = sum(1 for de in all_data_elements if de.get('dhis2_matched'))
            
            print(f"\n[PIVOTED] RÉSUMÉ:")
            print(f"  - Colonnes DE identifiées: {len(de_columns)}")
            print(f"  - Colonnes système ignorées: {len(system_columns)}")
            print(f"  - Total valeurs DE extraites: {total_des}")
            print(f"  - Auto-matchées avec DHIS2: {matched_des}")
            print(f"  - À mapper manuellement: {len(unmatched_values)}")
            print(f"  - Sections: {total_sections}")
            
            return {
                "success": True,
                "format": "pivoted",
                "has_section_column": section_col is not None,
                "section_column": section_col,
                "data_element_columns": de_columns,
                "system_columns": system_columns,
                "sections_mapping": sections_mapping,
                "all_data_elements": all_data_elements,
                "unmatched_values": unmatched_values,
                "statistics": {
                    "total_data_elements": total_des,
                    "matched_with_dhis2": matched_des,
                    "unmatched": len(unmatched_values),
                    "total_sections": total_sections,
                    "de_columns_count": len(de_columns)
                },
                "reasoning": f"Format pivoté: {total_des} valeurs trouvées dans {len(de_columns)} colonnes. {matched_des} matchent avec DHIS2, {len(unmatched_values)} à mapper manuellement."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur d'analyse: {str(e)}"
            }
