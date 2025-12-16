# Plan d'implémentation - Multi-onglets et Tableaux Croisés (Web)

## Vue d'ensemble

Ajouter les fonctionnalités de **multi-onglets Excel** et **tableaux croisés** à l'application web DHIS2 Manager, similaires à celles déjà implémentées dans l'application desktop (v4.3).

---

## Architecture actuelle

### Backend (Flask)
```
app/
├── routes/
│   └── calculator.py          # Routes API calculateur
├── services/
│   ├── data_calculator.py     # Service traitement données
│   └── metadata_manager.py    # Gestion métadonnées
└── templates/
    └── calculator.html        # Interface calculateur
```

### Flux actuel
1. Upload fichier Excel → `/api/upload-excel`
2. Traitement → `/api/process-template`
3. Utilise `process_template_excel()` qui lit **une seule feuille** : `sheet_name="Données"`

---

## Modifications nécessaires

### 1. Backend - Détection onglets

**Fichier : `app/services/data_calculator.py`**

#### Nouvelle méthode : `get_excel_sheets()`

```python
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
        return excel_file.sheet_names
    except Exception as e:
        logger.error(f"Erreur lecture onglets: {e}")
        raise ValueError(f"Impossible de lire les onglets: {str(e)}")
```

#### Modifier : `process_template_excel()`

**Avant :**
```python
def process_template_excel(self, filepath: str) -> Tuple[List[Dict], Dict]:
    df = pd.read_excel(filepath, sheet_name="Données", skiprows=5)
```

**Après :**
```python
def process_template_excel(
    self,
    filepath: str,
    sheet_name: str = "Données",
    mode: str = "normal"
) -> Tuple[List[Dict], Dict]:
    """
    Traite un fichier Excel (mode normal ou tableau croisé)

    Args:
        filepath: Chemin fichier
        sheet_name: Nom de l'onglet à traiter
        mode: "normal" ou "pivot" (tableau croisé)
    """
    if mode == "pivot":
        return self._process_pivot_table(filepath, sheet_name)
    else:
        return self._process_normal_template(filepath, sheet_name)
```

#### Nouvelle méthode : `_process_pivot_table()`

```python
def _process_pivot_table(
    self,
    filepath: str,
    sheet_name: str,
    data_element_id: str
) -> Tuple[List[Dict], Dict]:
    """
    Traite un tableau croisé (structures en colonnes)

    Args:
        filepath: Chemin fichier Excel
        sheet_name: Nom onglet
        data_element_id: ID du data element à utiliser

    Returns:
        Tuple (dataValues, stats)
    """
    # Lire le tableau
    df = pd.read_excel(filepath, sheet_name=sheet_name)

    data_values = []
    errors = {'org': 0, 'value': 0}

    # Première colonne = indicateurs (ignorée)
    # Autres colonnes = noms des structures
    org_columns = df.columns[1:]

    default_coc = self.metadata.get_default_coc_id()
    default_aoc = self.metadata.get_default_aoc_id()

    for idx, row in df.iterrows():
        for org_col in org_columns:
            value = row[org_col]

            # Ignorer valeurs vides
            if pd.isna(value) or str(value).strip() == '':
                continue

            # Résoudre organisation
            org_name = str(org_col).strip()
            org_id = self.metadata.get_org_unit_id_by_name(org_name)

            if not org_id:
                errors['org'] += 1
                logger.warning(f"Organisation inconnue: {org_name}")
                continue

            # Valider valeur
            try:
                val_num = float(value)
                if val_num < 0:
                    errors['value'] += 1
                    continue
            except (ValueError, TypeError):
                errors['value'] += 1
                continue

            # Créer dataValue
            data_values.append({
                'dataElement': data_element_id,
                'period': '2024',  # TODO: paramétrable
                'orgUnit': org_id,
                'categoryOptionCombo': default_coc,
                'attributeOptionCombo': default_aoc,
                'value': str(int(val_num) if val_num.is_integer() else val_num)
            })

    stats = {
        'total_rows': len(df),
        'total_columns': len(org_columns),
        'data_values': len(data_values),
        'errors_org': errors['org'],
        'errors_value': errors['value']
    }

    return data_values, stats
```

---

### 2. Backend - Routes API

**Fichier : `app/routes/calculator.py`**

#### Nouvelle route : `/api/get-sheets`

```python
@bp.route('/api/get-sheets', methods=['GET'])
def get_excel_sheets():
    """
    Récupère la liste des onglets du fichier Excel uploadé

    Returns:
        JSON avec liste des onglets
    """
    if 'excel_file' not in session:
        return jsonify({'error': 'Aucun fichier uploadé'}), 400

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
```

#### Modifier : `/api/process-template`

**Ajouter paramètres dans la requête :**

```python
@bp.route('/api/process-template', methods=['POST'])
def process_template():
    """
    Traite un fichier Excel

    Body JSON:
        {
            "sheet_name": "Premier Cycle",    # Onglet à traiter
            "mode": "normal",                 # "normal" ou "pivot"
            "data_element_id": "xyz123"       # Si mode pivot
        }
    """
    # Récupérer paramètres
    data = request.get_json() or {}
    sheet_name = data.get('sheet_name', 'Données')
    mode = data.get('mode', 'normal')
    data_element_id = data.get('data_element_id')

    # Validation mode pivot
    if mode == 'pivot' and not data_element_id:
        return jsonify({
            'error': 'data_element_id requis en mode tableau croisé'
        }), 400

    # Traiter selon mode
    if mode == 'pivot':
        data_values, stats = calculator._process_pivot_table(
            filepath,
            sheet_name,
            data_element_id
        )
    else:
        data_values, stats = calculator.process_template_excel(
            filepath,
            sheet_name
        )

    # ... reste du code
```

---

### 3. Frontend - Interface

**Fichier : `app/templates/calculator.html`**

#### Ajouter sélecteur d'onglets

**Après l'upload du fichier, afficher :**

```html
<!-- Section sélection onglet (masquée par défaut) -->
<div id="sheet-selector" class="hidden mt-4">
    <div class="card">
        <div class="card-header">
            <h3 class="card-title">📑 Onglets détectés</h3>
        </div>
        <div class="card-body">
            <div class="form-group">
                <label for="select-sheet">Sélectionnez l'onglet à traiter :</label>
                <select id="select-sheet" class="form-control">
                    <!-- Options ajoutées dynamiquement -->
                </select>
                <p class="text-muted mt-2">
                    <span id="sheet-count">0</span> onglet(s) disponible(s)
                </p>
            </div>
        </div>
    </div>
</div>
```

#### Ajouter sélecteur de mode

```html
<!-- Section mode de traitement -->
<div id="mode-selector" class="hidden mt-4">
    <div class="card">
        <div class="card-header">
            <h3 class="card-title">⚙️ Type de données</h3>
        </div>
        <div class="card-body">
            <div class="mode-selection">
                <!-- Mode Normal -->
                <label class="mode-card">
                    <input type="radio" name="processing-mode" value="normal" checked>
                    <div class="mode-card-inner">
                        <div class="mode-check">✓</div>
                        <div class="mode-icon">📋</div>
                        <h4>Données normales</h4>
                        <p>Template généré par le Générateur</p>
                        <p class="text-sm text-muted">
                            Fichier avec colonnes techniques pré-remplies
                        </p>
                    </div>
                </label>

                <!-- Mode Tableau Croisé -->
                <label class="mode-card">
                    <input type="radio" name="processing-mode" value="pivot">
                    <div class="mode-card-inner">
                        <div class="mode-check">✓</div>
                        <div class="mode-icon">📊</div>
                        <h4>Tableau croisé</h4>
                        <p>Structures en colonnes</p>
                        <p class="text-sm text-muted">
                            Première colonne = indicateurs<br>
                            Autres colonnes = structures<br>
                            Valeurs = intersections
                        </p>
                    </div>
                </label>
            </div>

            <!-- Options pour mode pivot -->
            <div id="pivot-options" class="hidden mt-4">
                <div class="alert alert-info">
                    <strong>Mode Tableau Croisé activé</strong>
                    <p>Les colonnes du fichier Excel représentent les structures.</p>
                    <p>Sélectionnez le Data Element correspondant aux valeurs :</p>
                </div>

                <div class="form-group">
                    <label for="pivot-data-element">Data Element :</label>
                    <select id="pivot-data-element" class="form-control">
                        <option value="">-- Sélectionner --</option>
                        <!-- Options chargées depuis métadonnées -->
                    </select>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### JavaScript - Logique

```javascript
// Après upload du fichier
async function onFileUploaded(filename) {
    // Récupérer les onglets
    const response = await fetch('/calculator/api/get-sheets');
    const data = await response.json();

    if (data.success) {
        // Afficher sélecteur si > 1 onglet
        if (data.count > 1) {
            populateSheetSelector(data.sheets);
            document.getElementById('sheet-selector').classList.remove('hidden');
        }

        // Afficher sélecteur de mode
        document.getElementById('mode-selector').classList.remove('hidden');
    }
}

function populateSheetSelector(sheets) {
    const select = document.getElementById('select-sheet');
    select.innerHTML = '';

    sheets.forEach(sheet => {
        const option = document.createElement('option');
        option.value = sheet;
        option.textContent = sheet;
        select.appendChild(option);
    });

    document.getElementById('sheet-count').textContent = sheets.length;
}

// Changement de mode
document.querySelectorAll('input[name="processing-mode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        const mode = e.target.value;
        const pivotOptions = document.getElementById('pivot-options');

        if (mode === 'pivot') {
            pivotOptions.classList.remove('hidden');
            loadDataElements(); // Charger liste des DE
        } else {
            pivotOptions.classList.add('hidden');
        }
    });
});

// Traitement
async function processFile() {
    const sheetName = document.getElementById('select-sheet').value || 'Données';
    const mode = document.querySelector('input[name="processing-mode"]:checked').value;

    const payload = {
        sheet_name: sheetName,
        mode: mode
    };

    // Si mode pivot, ajouter DE
    if (mode === 'pivot') {
        const deId = document.getElementById('pivot-data-element').value;
        if (!deId) {
            alert('Veuillez sélectionner un Data Element');
            return;
        }
        payload.data_element_id = deId;
    }

    // Appeler API
    const response = await fetch('/calculator/api/process-template', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (result.success) {
        displayResults(result);
    } else {
        alert('Erreur: ' + result.error);
    }
}
```

---

### 4. Métadonnées - Méthodes utilitaires

**Fichier : `app/services/metadata_manager.py`**

Ajouter méthodes si manquantes :

```python
def get_default_coc_id(self) -> str:
    """Retourne l'ID du categoryOptionCombo par défaut"""
    for coc in self.metadata.get('categoryOptionCombos', []):
        if coc.get('name') == 'default':
            return coc['id']
    raise ValueError("categoryOptionCombo 'default' introuvable")

def get_default_aoc_id(self) -> str:
    """Retourne l'ID du attributeOptionCombo par défaut"""
    # Généralement identique au COC par défaut
    return self.get_default_coc_id()

def get_org_unit_id_by_name(self, name: str) -> Optional[str]:
    """
    Recherche l'ID d'une orgUnit par son nom

    Args:
        name: Nom de l'organisation (case-insensitive)

    Returns:
        ID de l'orgUnit ou None si introuvable
    """
    name_lower = name.strip().lower()

    for org in self.metadata.get('organisationUnits', []):
        if org.get('name', '').strip().lower() == name_lower:
            return org['id']

    return None
```

---

## Tests à effectuer

### Test 1 : Fichier mono-onglet normal
- Upload fichier Excel classique
- Vérifier que sélecteur d'onglets **ne s'affiche pas**
- Mode "normal" par défaut
- Traitement OK

### Test 2 : Fichier multi-onglets normal
- Upload fichier avec 3+ onglets
- Sélecteur d'onglets **s'affiche**
- Sélectionner onglet
- Mode "normal"
- Traitement OK

### Test 3 : Tableau croisé mono-onglet
- Upload fichier tableau croisé
- Mode "pivot"
- Sélectionner Data Element
- Traitement OK
- Vérifier résolution des structures depuis colonnes

### Test 4 : Tableau croisé multi-onglets
- Upload fichier avec plusieurs onglets tableau croisé
- Sélectionner onglet 1
- Mode "pivot", sélectionner DE1
- Export
- Changer onglet 2
- Sélectionner DE2
- Export
- Vérifier 2 exports distincts

---

## Compatibilité

### Rétrocompatibilité
- **Fichiers existants** fonctionnent toujours
- **Mode par défaut** : "normal" + onglet "Données"
- **Pas de breaking changes** dans l'API

### Migration
- Aucune migration nécessaire
- Les anciennes URLs fonctionnent
- Nouvelles fonctionnalités opt-in

---

## Documentation

### Fichiers à créer

1. **GUIDE_TABLEAUX_CROISES_WEB.md**
   - Guide utilisateur web
   - Screenshots
   - Exemples

2. **CHANGELOG_WEB_v2.0.md**
   - Liste des modifications
   - Breaking changes (aucun)
   - Nouvelles fonctionnalités

3. **API_DOCS.md**
   - Documentation API mise à jour
   - Nouveaux endpoints
   - Nouveaux paramètres

---

## Priorisation

### Phase 1 (Essentiel)
1. ✅ Détection onglets backend
2. ✅ API `/api/get-sheets`
3. ✅ Sélecteur onglets UI
4. ✅ Modifier traitement pour accepter `sheet_name`

### Phase 2 (Important)
5. ✅ Traitement tableau croisé backend
6. ✅ Sélecteur mode UI
7. ✅ API avec paramètre `mode`
8. ✅ Interface pour mode pivot

### Phase 3 (Amélioration)
9. ⬜ Validation frontend
10. ⬜ Messages d'erreur détaillés
11. ⬜ Preview des données avant traitement
12. ⬜ Tests unitaires

---

## Estimation

- **Phase 1** : 2-3 heures
- **Phase 2** : 3-4 heures
- **Phase 3** : 2-3 heures

**Total** : 7-10 heures

---

## Notes techniques

### Gestion de session
- Stocker `selected_sheet` et `processing_mode` en session
- Permettre changement d'onglet sans re-upload

### Performance
- Pas d'impact significatif
- Lecture onglets = opération rapide
- Cache possible si fichier volumineux

### Sécurité
- Valider nom onglet (éviter path traversal)
- Limiter taille fichier
- Timeout sur traitement

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
**Version cible** : 2.0
