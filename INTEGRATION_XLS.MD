# 🧠 Prompts d'Intégration - TCD vers Template DHIS2

## Table des matières
1. [Prompt Principal - Intégration Complète](#prompt-1)
2. [Prompt Analyse de Code Existant](#prompt-2)
3. [Prompt Refactoring et Amélioration](#prompt-3)
4. [Prompt Débogage et Diagnostic](#prompt-4)
5. [Prompt Extension pour Nouveaux Datasets](#prompt-5)
6. [Annexe - Documentation Technique Complète](#annexe)

---

<a name="prompt-1"></a>
## 📌 PROMPT 1 : Intégration Complète dans une Application Existante

```
Tu es un expert en développement Python spécialisé dans les systèmes d'information sanitaire et éducatif, particulièrement DHIS2. Tu dois intégrer un algorithme de traitement de données TCD (Tableaux Croisés Dynamiques) vers des templates DHIS2 dans une application existante.

## CONTEXTE DU PROJET

L'application existante permet de remplir des templates DHIS2 à partir de données TCD Excel, mais le résultat actuel n'est pas satisfaisant. Tu dois intégrer un nouvel algorithme robuste qui résout les problèmes identifiés.

## PROBLÈMES COURANTS À RÉSOUDRE

1. **Problèmes de normalisation des données**
   - Les tranches d'âge ont des formats incohérents : "[ 20 - 22 [", "[20-22[", "20 - 22"
   - Les CategoryOptionCombo (COC) ont des espaces et tabulations variables
   - Les apostrophes typographiques (') vs droites (') causent des erreurs de matching

2. **Problèmes de mapping**
   - Les noms d'établissements sont des acronymes dans les TCD mais des noms complets dans les templates
   - Les DataElements ont des variations orthographiques ("2ème" vs "2e", "1ère" vs "1ere")
   - Les cellules fusionnées dans les TCD créent des NaN qu'il faut propager

3. **Problèmes de structure**
   - Les templates DHIS2 ont un header à la ligne 5 (index 5)
   - Les TCD ont un header à la ligne 2 (index 2)
   - La dernière colonne du TCD contient toujours les valeurs à insérer

## ALGORITHME À INTÉGRER

### Étape 1 : Normalisation des données

```python
def normaliser_tranche_age(s):
    """
    Normalise une tranche d'âge vers un format standard.
    
    Règles:
    - '[ 20 - 22 [' → '20-22'
    - '40 ans et plus' → '40+'
    - '- 18 ans' ou 'moins de 18' → '-18'
    - 'ND' ou 'Non Défini' → 'ND'
    
    Algorithme:
    1. Nettoyer les espaces
    2. Détecter les cas spéciaux (40+, -18, ND)
    3. Extraire les bornes numériques avec regex
    4. Retourner le format normalisé 'borne1-borne2'
    """
    if pd.isna(s):
        return None
    s = str(s).strip()
    
    # Cas spéciaux
    if '40 ans' in s.lower() or '40+' in s.lower():
        return '40+'
    if '18 ans' in s.lower() or re.match(r'^-\s*18', s):
        return '-18'
    if 'ND' in s.upper():
        return 'ND'
    
    # Extraction des bornes
    match = re.search(r'\[?\s*(\d+)\s*[-–]\s*(\d+)\s*\[?', s)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return s


def normaliser_coc(coc):
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
    """
    if pd.isna(coc):
        return None
    s = str(coc).strip().replace('\t', ' ')
    s = re.sub(r'\s+', ' ', s)
    
    # Format 1: "X | [NN - NN["
    match1 = re.match(r'^([FM])\s*\|\s*(.+)$', s)
    if match1:
        return f"{match1.group(1)}|{normaliser_tranche_age(match1.group(2))}"
    
    # Format 2: "- 18 ans | X" ou "40 ans + | X"
    match2 = re.match(r'^(.+)\s*\|\s*([FM])$', s)
    if match2:
        return f"{match2.group(2)}|{normaliser_tranche_age(match2.group(1))}"
    
    return s
```

### Étape 2 : Construction des mappings dynamiques

```python
def construire_mapping_etablissements(df_template, patterns):
    """
    Construit le mapping établissements en extrayant les noms EXACTS du template.
    
    Principe clé: Ne jamais coder en dur les noms avec apostrophes ou caractères spéciaux.
    Extraire dynamiquement depuis le template pour éviter les problèmes d'encodage.
    
    Args:
        df_template: DataFrame du template DHIS2
        patterns: Dict {'ACRONYME': 'partie_du_nom_à_chercher'}
    
    Returns:
        Dict {'ACRONYME': 'nom_exact_du_template'}
    """
    # Extraire les noms uniques et les normaliser
    noms_template = {
        str(n).strip(): n 
        for n in df_template['orgUnitName'].unique()
        if pd.notna(n)
    }
    
    mapping = {}
    for acronyme, pattern in patterns.items():
        for nom_norm, nom_original in noms_template.items():
            if pattern.lower() in nom_norm.lower():
                mapping[acronyme] = nom_norm
                break
    
    return mapping
```

### Étape 3 : Index de recherche optimisé

```python
def construire_index_recherche(df_template):
    """
    Construit un index de recherche rapide basé sur des clés normalisées.
    
    Clé de recherche: "SECTION|DATA_ELEMENT|ETABLISSEMENT|COC_NORMALISE"
    
    Avantages:
    - Recherche O(1) au lieu de O(n)
    - Indépendant des variations de format
    - Facilite le débogage (clés lisibles)
    """
    # Ajouter colonnes normalisées
    df_template['_coc_norm'] = df_template['categoryOptionComboName'].apply(normaliser_coc)
    df_template['_org_norm'] = df_template['orgUnitName'].apply(lambda x: str(x).strip() if pd.notna(x) else None)
    
    # Construire la clé
    df_template['_cle'] = (
        df_template['section'].fillna('').str.strip() + '|' +
        df_template['dataElementName'].fillna('').str.strip() + '|' +
        df_template['_org_norm'].fillna('') + '|' +
        df_template['_coc_norm'].fillna('')
    )
    
    # Créer l'index
    return {row['_cle']: idx for idx, row in df_template.iterrows()}
```

### Étape 4 : Traitement des TCD avec propagation des NaN

```python
def traiter_onglet_tcd(df_tcd, col_etablissement, col_age, col_sexe, col_data, mapping_etab, mapping_de, index_recherche, df_template):
    """
    Traite un onglet TCD et insère les valeurs dans le template.
    
    Points critiques:
    1. Propager les NaN (cellules fusionnées Excel)
    2. Ignorer les lignes "Total"
    3. La dernière colonne contient les valeurs
    4. Construire la clé de recherche normalisée
    5. Collecter les erreurs pour le rapport
    """
    # Supprimer les totaux
    df_tcd = df_tcd[~df_tcd[col_etablissement].astype(str).str.contains('Total', na=False)]
    
    # CRITIQUE: Propager les valeurs des cellules fusionnées
    df_tcd[col_etablissement] = df_tcd[col_etablissement].ffill()
    df_tcd[col_age] = df_tcd[col_age].ffill()
    df_tcd[col_sexe] = df_tcd[col_sexe].ffill()
    
    # Dernière colonne = valeurs
    col_valeur = df_tcd.columns[-1]
    
    stats = {'valeurs': 0, 'erreurs': 0}
    erreurs = []
    
    for idx, row in df_tcd.iterrows():
        etab = str(row[col_etablissement]).strip()
        age = row[col_age]
        sexe = row[col_sexe]
        data_elem = str(row[col_data]).strip()
        valeur = row[col_valeur]
        
        # Ignorer les lignes sans valeur
        if pd.isna(valeur) or valeur == 0:
            continue
        
        # Mapper l'établissement
        etab_template = mapping_etab.get(etab)
        if etab_template is None:
            erreurs.append({'type': 'etablissement', 'valeur': etab, 'count': int(valeur)})
            continue
        
        # Mapper le data element
        mapping = mapping_de.get(data_elem)
        if mapping is None:
            erreurs.append({'type': 'data_element', 'valeur': data_elem, 'count': int(valeur)})
            continue
        
        section, de_template = mapping
        
        # Construire le COC normalisé
        sexe = str(sexe).strip().upper()
        age_norm = normaliser_tranche_age(age)
        coc_norm = f"{sexe}|{age_norm}"
        
        # Construire la clé et rechercher
        cle = f"{section}|{de_template}|{etab_template}|{coc_norm}"
        
        if cle in index_recherche:
            idx_template = index_recherche[cle]
            df_template.at[idx_template, 'value'] = int(valeur)
            stats['valeurs'] += 1
        else:
            erreurs.append({'type': 'combinaison', 'cle': cle, 'valeur': int(valeur)})
            stats['erreurs'] += 1
    
    return stats, erreurs
```

## STRUCTURE DE DONNÉES ATTENDUE

### Template DHIS2 (colonnes)
| Colonne | Description |
|---------|-------------|
| section | Nom de la section (Cycle, Nationalité, etc.) |
| dataElementName | Nom du data element |
| dataElement | UID DHIS2 du data element |
| orgUnitName | Nom de l'établissement |
| orgUnit | UID DHIS2 de l'établissement |
| categoryOptionComboName | Combinaison SEXE + AGE |
| categoryOptionCombo | UID DHIS2 du COC |
| value | VALEUR À REMPLIR |
| period | Période (ex: 2023) |

### TCD (colonnes standards)
| Colonne | Description |
|---------|-------------|
| NOM_ETAB | Acronyme de l'établissement |
| GROUP_AGE | Tranche d'âge |
| SEXE | F ou M |
| [VARIABLE] | Data element (CYCLE, DIPLÔME, etc.) |
| Nombre de... | Valeur (dernière colonne) |

## INSTRUCTIONS D'INTÉGRATION

1. **Analyser le code existant** pour identifier les points d'intégration
2. **Remplacer les fonctions de normalisation** par celles fournies
3. **Implémenter l'index de recherche** pour optimiser les performances
4. **Ajouter la propagation des NaN** pour gérer les cellules fusionnées
5. **Extraire dynamiquement les noms** depuis le template (ne pas coder en dur)
6. **Générer un rapport détaillé** des erreurs

## CODE EXISTANT À ANALYSER

[COLLER ICI LE CODE EXISTANT DE L'APPLICATION]

## TÂCHE

Analyse le code existant et propose une intégration intelligente de l'algorithme décrit ci-dessus. Identifie :
1. Les fonctions à remplacer
2. Les fonctions à améliorer
3. Les nouvelles fonctions à ajouter
4. Les modifications de structure nécessaires

Fournis le code refactorisé complet avec des commentaires expliquant chaque modification.
```

---

<a name="prompt-2"></a>
## 📌 PROMPT 2 : Analyse et Diagnostic du Code Existant

```
Tu es un expert en analyse de code Python et en systèmes DHIS2. Tu dois analyser un code existant de traitement TCD vers template DHIS2 qui ne fonctionne pas correctement.

## PROBLÈMES CONNUS

L'application actuelle présente les problèmes suivants :
- Les valeurs ne sont pas correctement insérées dans le template
- Certains établissements ne sont pas reconnus
- Les tranches d'âge ne matchent pas
- Des données sont perdues sans explication

## POINTS DE VÉRIFICATION CRITIQUES

Analyse le code en vérifiant ces points précis :

### 1. Normalisation des chaînes
```python
# ❌ MAUVAIS - Comparaison directe
if etab_tcd == etab_template:

# ✅ BON - Normalisation avant comparaison
if etab_tcd.strip().lower() == etab_template.strip().lower():
```

### 2. Gestion des apostrophes
```python
# ❌ MAUVAIS - Apostrophe codée en dur (peut être ' ou ')
nom = "Ecole d'Economie"

# ✅ BON - Extraction dynamique depuis le template
noms_template = df_template['orgUnitName'].unique()
nom = next((n for n in noms_template if 'Economie' in n), None)
```

### 3. Gestion des cellules fusionnées Excel
```python
# ❌ MAUVAIS - Ignorer les NaN
df = df.dropna()

# ✅ BON - Propager les valeurs
df['NOM_ETAB'] = df['NOM_ETAB'].ffill()  # Forward fill
```

### 4. Format des tranches d'âge
```python
# ❌ MAUVAIS - Format rigide
if age == '[20 - 22[':

# ✅ BON - Normalisation flexible
def normaliser_age(s):
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)', s)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
```

### 5. Recherche dans le template
```python
# ❌ MAUVAIS - Recherche linéaire O(n) pour chaque ligne
for idx, row in df_template.iterrows():
    if row['section'] == section and row['dataElement'] == de:
        ...

# ✅ BON - Index de recherche O(1)
index = {f"{row['section']}|{row['dataElement']}": idx for idx, row in df_template.iterrows()}
if cle in index:
    idx = index[cle]
```

### 6. Gestion des espaces et tabs
```python
# ❌ MAUVAIS - Ne pas nettoyer
coc = row['categoryOptionComboName']

# ✅ BON - Nettoyer tabs et espaces multiples
coc = row['categoryOptionComboName'].replace('\t', ' ')
coc = re.sub(r'\s+', ' ', coc).strip()
```

## CODE À ANALYSER

[COLLER LE CODE EXISTANT ICI]

## TÂCHE

1. Identifie TOUS les problèmes dans le code selon les points ci-dessus
2. Pour chaque problème, explique :
   - Où il se trouve (ligne/fonction)
   - Pourquoi c'est un problème
   - Comment le corriger
3. Classe les problèmes par criticité (Critique, Important, Mineur)
4. Propose un plan de correction ordonné

Format de sortie attendu :
```
## PROBLÈME 1 [CRITIQUE]
- Localisation: fonction xyz(), ligne XX
- Description: ...
- Impact: ...
- Correction: ...
```
```

---

<a name="prompt-3"></a>
## 📌 PROMPT 3 : Refactoring et Amélioration de Performance

```
Tu es un expert en refactoring Python et optimisation de performance. Tu dois améliorer un code de traitement de données TCD vers DHIS2.

## OBJECTIFS DU REFACTORING

1. **Performance** : Le code doit traiter 10 000+ lignes en moins de 5 secondes
2. **Maintenabilité** : Code modulaire et bien documenté
3. **Robustesse** : Gestion complète des erreurs et cas limites
4. **Extensibilité** : Facile à adapter pour de nouveaux datasets

## ARCHITECTURE CIBLE

```
tcd_processor/
├── __init__.py
├── config.py          # Configuration et mappings
├── normalizers.py     # Fonctions de normalisation
├── processor.py       # Classe principale TCDProcessor
├── reporters.py       # Génération de rapports
└── utils.py           # Utilitaires
```

## PATTERNS À IMPLÉMENTER

### Pattern 1 : Configuration externalisée
```python
@dataclass
class MappingConfig:
    """Configuration des mappings - modifiable sans changer le code."""
    etablissements_patterns: Dict[str, str]
    onglets_mapping: Dict[str, str]
    data_elements_manuels: Dict[str, Tuple[str, str]]
    template_header_row: int = 5
    tcd_header_row: int = 2
```

### Pattern 2 : Classe de normalisation statique
```python
class Normalizer:
    """Méthodes statiques de normalisation - réutilisables."""
    
    @staticmethod
    def normaliser_tranche_age(s: Any) -> Optional[str]:
        ...
    
    @staticmethod
    def normaliser_coc(coc: Any) -> Optional[str]:
        ...
```

### Pattern 3 : Processeur avec chaînage fluide
```python
processor = TCDProcessor(template, tcd, config)
processor.load().process().save(output)

# Ou étape par étape pour debug
processor.load()
processor.build_mappings()
processor.build_index()
processor.process_all_sheets()
print(processor.stats)
processor.save(output)
```

### Pattern 4 : Statistiques structurées
```python
@dataclass
class ProcessingStats:
    lignes_traitees: int = 0
    valeurs_inserees: int = 0
    etablissements_non_mappes: Dict[str, int] = field(default_factory=dict)
    combinaisons_non_trouvees: List[Dict] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convertit en DataFrame pour export."""
        ...
```

## OPTIMISATIONS REQUISES

### 1. Vectorisation Pandas
```python
# ❌ LENT - Itération ligne par ligne
for idx, row in df.iterrows():
    df.at[idx, 'norm'] = normaliser(row['col'])

# ✅ RAPIDE - Vectorisation
df['norm'] = df['col'].apply(normaliser)
```

### 2. Index de recherche avec dict
```python
# ❌ LENT - O(n) par recherche
mask = (df['a'] == val_a) & (df['b'] == val_b)
result = df[mask]

# ✅ RAPIDE - O(1) avec index
index = {(row['a'], row['b']): idx for idx, row in df.iterrows()}
if (val_a, val_b) in index:
    result = df.loc[index[(val_a, val_b)]]
```

### 3. Compilation regex une seule fois
```python
# ❌ LENT - Recompilation à chaque appel
def func(s):
    return re.search(r'\d+', s)

# ✅ RAPIDE - Compilation unique
PATTERN_DIGITS = re.compile(r'\d+')
def func(s):
    return PATTERN_DIGITS.search(s)
```

## CODE ACTUEL À REFACTORISER

[COLLER LE CODE ICI]

## TÂCHE

1. Refactorise le code selon l'architecture cible
2. Implémente les patterns décrits
3. Applique les optimisations de performance
4. Ajoute une gestion complète des erreurs
5. Documente chaque fonction avec docstrings
6. Ajoute des type hints partout

Fournis le code complet refactorisé, organisé en modules.
```

---

<a name="prompt-4"></a>
## 📌 PROMPT 4 : Débogage et Diagnostic des Erreurs

```
Tu es un expert en débogage Python. Tu dois diagnostiquer pourquoi un traitement TCD vers DHIS2 ne produit pas les résultats attendus.

## SYMPTÔMES RAPPORTÉS

- X valeurs attendues mais seulement Y insérées
- Certains établissements sont ignorés sans raison apparente
- Le rapport montre des "combinaisons non trouvées" qui devraient exister

## MÉTHODOLOGIE DE DIAGNOSTIC

### Étape 1 : Vérifier les données d'entrée
```python
# Afficher les valeurs uniques pour identifier les variations
print("=== ÉTABLISSEMENTS DANS LE TCD ===")
print(df_tcd['NOM_ETAB'].unique())

print("\n=== ÉTABLISSEMENTS DANS LE TEMPLATE ===")
for org in df_template['orgUnitName'].unique():
    print(f"  '{org}' -> repr: {repr(org)}")
```

### Étape 2 : Comparer caractère par caractère
```python
def compare_strings(s1, s2):
    """Compare deux chaînes caractère par caractère."""
    print(f"String 1: '{s1}' (len={len(s1)})")
    print(f"String 2: '{s2}' (len={len(s2)})")
    
    for i, (c1, c2) in enumerate(zip(s1, s2)):
        if c1 != c2:
            print(f"  Diff at pos {i}: '{c1}' (ord={ord(c1)}) vs '{c2}' (ord={ord(c2)})")
    
    if len(s1) != len(s2):
        print(f"  Length diff: {len(s1)} vs {len(s2)}")
```

### Étape 3 : Tracer une ligne spécifique
```python
def debug_ligne(row, mapping_etab, mapping_de, index_recherche):
    """Trace le traitement d'une ligne pour comprendre où ça échoue."""
    print(f"\n=== DEBUG LIGNE ===")
    print(f"Établissement TCD: '{row['NOM_ETAB']}'")
    
    etab_template = mapping_etab.get(row['NOM_ETAB'].strip())
    print(f"Établissement mappé: {etab_template}")
    if etab_template is None:
        print("  ❌ ÉCHEC: Établissement non trouvé dans le mapping")
        print(f"  Mappings disponibles: {list(mapping_etab.keys())}")
        return
    
    data_elem = row['CYCLE'].strip()  # Adapter selon l'onglet
    mapping = mapping_de.get(data_elem)
    print(f"Data element TCD: '{data_elem}'")
    print(f"Data element mappé: {mapping}")
    if mapping is None:
        print("  ❌ ÉCHEC: Data element non trouvé dans le mapping")
        return
    
    section, de_template = mapping
    
    sexe = str(row['SEXE']).strip().upper()
    age_norm = normaliser_tranche_age(row['GROUP_AGE'])
    coc_norm = f"{sexe}|{age_norm}"
    print(f"COC construit: '{coc_norm}'")
    
    cle = f"{section}|{de_template}|{etab_template}|{coc_norm}"
    print(f"Clé de recherche: '{cle}'")
    
    if cle in index_recherche:
        print(f"  ✅ TROUVÉ à l'index {index_recherche[cle]}")
    else:
        print("  ❌ ÉCHEC: Clé non trouvée dans l'index")
        # Chercher des clés similaires
        similaires = [k for k in index_recherche.keys() if etab_template in k and de_template in k]
        print(f"  Clés similaires: {similaires[:5]}")
```

### Étape 4 : Générer un rapport de diagnostic
```python
def generer_diagnostic(df_tcd, df_template, mapping_etab, mapping_de):
    """Génère un rapport complet de diagnostic."""
    rapport = {
        'etab_tcd_non_mappes': [],
        'de_tcd_non_mappes': [],
        'coc_template_uniques': set(),
        'coc_tcd_uniques': set(),
    }
    
    # Établissements TCD non mappés
    for etab in df_tcd['NOM_ETAB'].dropna().unique():
        if etab.strip() not in mapping_etab:
            rapport['etab_tcd_non_mappes'].append(etab)
    
    # COC uniques dans le template (normalisés)
    for coc in df_template['categoryOptionComboName'].dropna().unique():
        rapport['coc_template_uniques'].add(normaliser_coc(coc))
    
    # COC uniques dans le TCD
    for _, row in df_tcd.iterrows():
        if pd.notna(row['SEXE']) and pd.notna(row['GROUP_AGE']):
            sexe = str(row['SEXE']).strip().upper()
            age = normaliser_tranche_age(row['GROUP_AGE'])
            rapport['coc_tcd_uniques'].add(f"{sexe}|{age}")
    
    # COC dans TCD mais pas dans template
    rapport['coc_manquants'] = rapport['coc_tcd_uniques'] - rapport['coc_template_uniques']
    
    return rapport
```

## ERREUR À DIAGNOSTIQUER

[DÉCRIRE L'ERREUR SPÉCIFIQUE OU COLLER LES LOGS]

## CODE CONCERNÉ

[COLLER LE CODE]

## DONNÉES D'EXEMPLE

[COLLER UN ÉCHANTILLON DES DONNÉES TCD ET TEMPLATE]

## TÂCHE

1. Analyse les symptômes et le code
2. Identifie la cause racine probable
3. Propose des tests de diagnostic à exécuter
4. Fournis le correctif avec explication
```

---

<a name="prompt-5"></a>
## 📌 PROMPT 5 : Extension pour Nouveaux Datasets

```
Tu es un expert en développement Python et DHIS2. Tu dois étendre un système de traitement TCD existant pour supporter de nouveaux datasets.

## SYSTÈME EXISTANT

Le système actuel traite les datasets suivants :
- Effectifs étudiants par cycle
- Effectifs par nationalité
- Effectifs par année d'étude
- Effectifs par diplôme

## NOUVEAU DATASET À INTÉGRER

[DÉCRIRE LE NOUVEAU DATASET]

Exemple de structure :
- Nom du dataset : [NOM]
- Sections : [LISTE DES SECTIONS]
- Data elements : [LISTE]
- Dimensions : [AGE, SEXE, AUTRES...]

## ÉTAPES D'EXTENSION

### 1. Analyser le nouveau template DHIS2
```python
def analyser_template(template_path):
    """Analyse un template pour comprendre sa structure."""
    df = pd.read_excel(template_path, sheet_name="Données", header=5)
    
    print("=== STRUCTURE DU TEMPLATE ===")
    print(f"Colonnes: {df.columns.tolist()}")
    print(f"Lignes: {len(df)}")
    
    print("\n=== SECTIONS ===")
    for section in df['section'].dropna().unique():
        print(f"\n  {section}:")
        des = df[df['section'] == section]['dataElementName'].unique()
        for de in des:
            print(f"    - {de}")
    
    print("\n=== CATEGORY OPTION COMBOS ===")
    for coc in df['categoryOptionComboName'].dropna().unique():
        print(f"  '{coc}' -> repr: {repr(coc)}")
    
    print("\n=== ORG UNITS ===")
    for org in df['orgUnitName'].dropna().unique():
        print(f"  '{org}'")
    
    return df
```

### 2. Analyser le nouveau TCD
```python
def analyser_tcd(tcd_path, sheet_name):
    """Analyse un onglet TCD pour comprendre sa structure."""
    df = pd.read_excel(tcd_path, sheet_name=sheet_name, header=2)
    
    print(f"=== STRUCTURE TCD: {sheet_name} ===")
    print(f"Colonnes: {df.columns.tolist()}")
    
    print("\n=== VALEURS UNIQUES PAR COLONNE ===")
    for col in df.columns:
        uniques = df[col].dropna().unique()
        print(f"\n  {col} ({len(uniques)} valeurs):")
        for v in uniques[:10]:
            print(f"    - '{v}'")
        if len(uniques) > 10:
            print(f"    ... et {len(uniques) - 10} autres")
    
    return df
```

### 3. Créer les nouveaux mappings
```python
# Ajouter dans MappingConfig

# Nouveaux établissements
config.etablissements_patterns['NOUVEAU_CODE'] = 'Partie du nom'

# Nouvel onglet TCD
config.onglets_mapping['nouvel_onglet'] = 'NOM_COLONNE_DATA_ELEMENT'

# Nouveaux data elements
config.data_elements_manuels['VALEUR_TCD'] = ('Section Template', 'DataElement Template')
```

### 4. Gérer les nouvelles dimensions (si différentes de SEXE|AGE)
```python
def construire_coc_personnalise(row, dimensions):
    """
    Construit un COC pour des dimensions personnalisées.
    
    Args:
        row: Ligne du TCD
        dimensions: Liste des colonnes à combiner ['DIM1', 'DIM2']
    
    Returns:
        COC normalisé "DIM1|DIM2"
    """
    parties = []
    for dim in dimensions:
        val = row.get(dim)
        if pd.notna(val):
            parties.append(normaliser_dimension(str(val).strip(), dim))
        else:
            return None
    return '|'.join(parties)
```

## TEMPLATE DU NOUVEAU DATASET

[COLLER UN EXTRAIT DU NOUVEAU TEMPLATE]

## TCD DU NOUVEAU DATASET

[COLLER UN EXTRAIT DU NOUVEAU TCD]

## TÂCHE

1. Analyse les structures du nouveau template et TCD
2. Identifie les mappings nécessaires
3. Détermine si de nouvelles normalisations sont requises
4. Propose les modifications du code existant
5. Fournis le code d'extension complet
```

---

<a name="annexe"></a>
## 📚 ANNEXE : Documentation Technique Complète

### A. Algorithme de Traitement - Vue d'ensemble

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   TEMPLATE      │     │   PROCESSEUR     │     │      TCD        │
│    DHIS2        │     │                  │     │    (Excel)      │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                        │
         │  1. Charger           │                        │
         │◄──────────────────────┤                        │
         │                       │  2. Charger            │
         │                       ├───────────────────────►│
         │                       │                        │
         │  3. Extraire noms     │                        │
         │◄──────────────────────┤                        │
         │     exacts            │                        │
         │                       │                        │
         │  4. Construire        │                        │
         │     mappings          │                        │
         │◄──────────────────────┤                        │
         │                       │                        │
         │  5. Construire        │                        │
         │     index O(1)        │                        │
         │◄──────────────────────┤                        │
         │                       │                        │
         │                       │  6. Pour chaque        │
         │                       │     onglet TCD         │
         │                       │◄───────────────────────┤
         │                       │                        │
         │                       │  7. Propager NaN       │
         │                       │     (ffill)            │
         │                       │◄───────────────────────┤
         │                       │                        │
         │                       │  8. Pour chaque ligne  │
         │                       │◄───────────────────────┤
         │                       │                        │
         │  9. Construire clé    │                        │
         │     normalisée        │                        │
         │◄──────────────────────┤                        │
         │                       │                        │
         │  10. Rechercher &     │                        │
         │      insérer valeur   │                        │
         │◄──────────────────────┤                        │
         │                       │                        │
         │  11. Sauvegarder      │                        │
         │◄──────────────────────┤                        │
         │                       │                        │
         ▼                       ▼                        ▼
   ┌─────────────┐        ┌─────────────┐         ┌─────────────┐
   │  TEMPLATE   │        │   RAPPORT   │         │   STATS     │
   │   REMPLI    │        │   ERREURS   │         │             │
   └─────────────┘        └─────────────┘         └─────────────┘
```

### B. Format de la Clé de Recherche

```
SECTION | DATA_ELEMENT | ETABLISSEMENT | COC_NORMALISE
   │          │              │               │
   │          │              │               └─► "F|20-22" ou "M|40+"
   │          │              │
   │          │              └─► Nom exact extrait du template
   │          │
   │          └─► Nom exact du data element
   │
   └─► Nom de la section (Cycle, Nationalité, etc.)

Exemple:
"Cycle|1er cycle|Centre Privé de Santé Publique|F|20-22"
```

### C. Règles de Normalisation des Tranches d'Âge

| Entrée | Sortie | Règle |
|--------|--------|-------|
| `[ 20 - 22 [` | `20-22` | Extraction bornes |
| `[20-22[` | `20-22` | Extraction bornes |
| `20 - 22` | `20-22` | Extraction bornes |
| `[ 28 - 30 [ ` | `28-30` | Trim + extraction |
| `40 ans et plus` | `40+` | Cas spécial 40+ |
| `40 ans +` | `40+` | Cas spécial 40+ |
| `- 18 ans` | `-18` | Cas spécial moins de 18 |
| `moins de 18` | `-18` | Cas spécial moins de 18 |
| `ND` | `ND` | Non défini |

### D. Gestion des Erreurs - Types et Causes

| Type d'erreur | Cause probable | Solution |
|---------------|----------------|----------|
| Établissement non mappé | Acronyme inconnu | Ajouter dans `etablissements_patterns` |
| Data element non mappé | Variation orthographique | Ajouter dans `data_elements_manuels` |
| Combinaison non trouvée | Template incomplet | Vérifier si la combinaison existe dans DHIS2 |
| Valeur NaN | Cellule fusionnée non propagée | Vérifier `ffill()` |
| Apostrophe mismatch | Encodage différent | Extraire dynamiquement depuis le template |

### E. Configuration Recommandée

```python
config = MappingConfig(
    # Mapping établissements : ACRONYME -> partie du nom à chercher
    etablissements_patterns={
        'CPSP': 'Centre Privé de Santé Publique',
        'ESEG': 'Economie et de Gestion',
        'UAZ': 'UNIVERSITE AGADEZ',
        # ... autres
    },
    
    # Mapping onglets : nom_onglet -> colonne_data_element
    onglets_mapping={
        'cycle': 'CYCLE',
        'nationalité': 'GROUP_NAT',
        'annee_etud': 'ANNE_ETU',
        'diplome': 'DIPLÔME',
    },
    
    # Mappings manuels pour les variations orthographiques
    data_elements_manuels={
        '2ème cycle': ('Cycle', '2e cycle'),
        '1ère année': ("Niveau d'étude", '1ere année'),
        'NIGER': ('Nationalité', 'Niger'),
        # ... autres
    },
    
    # Positions des headers
    template_header_row=5,
    tcd_header_row=2,
)
```

---

## 🔧 Utilisation des Prompts

1. **Pour une nouvelle intégration** : Utiliser le Prompt 1
2. **Pour diagnostiquer un problème** : Utiliser les Prompts 2 et 4
3. **Pour améliorer les performances** : Utiliser le Prompt 3
4. **Pour ajouter un nouveau dataset** : Utiliser le Prompt 5

Chaque prompt est conçu pour être auto-suffisant et contient toute la logique métier nécessaire.