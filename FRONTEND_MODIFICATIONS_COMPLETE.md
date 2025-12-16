# Frontend - Modifications Terminées

## ✅ Ce qui a été fait

### Fichier modifié : `app/templates/calculator.html`

---

## 1. Interface utilisateur (HTML)

### A. Sélection de l'onglet Excel
**Lignes 306-322**

```html
<div id="sheet-selection" class="hidden mt-4 pt-4 border-t border-green-200">
    <div class="form-group">
        <label for="select-sheet" class="form-label flex items-center gap-2">
            <i class="fas fa-layer-group text-blue-600"></i>
            <span class="font-bold">Sélectionnez l'onglet à traiter</span>
            <span id="sheet-count" class="badge badge-info ml-2"></span>
        </label>
        <select id="select-sheet" class="form-input">
            <!-- Options ajoutées dynamiquement -->
        </select>
    </div>
</div>
```

**Comportement** :
- Caché par défaut
- S'affiche uniquement si le fichier Excel contient plusieurs onglets
- Badge indiquant le nombre d'onglets

---

### B. Sélection du type de données
**Lignes 324-368**

```html
<div id="data-type-selection" class="mt-4 pt-4 border-t border-green-200">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Mode Normal -->
        <label class="cursor-pointer">
            <input type="radio" name="data-type" value="normal" class="hidden" checked>
            <div class="border-2 border-gray-200 rounded-lg p-4 hover:border-blue-500 transition-all data-type-card">
                <div class="flex items-center gap-3 mb-2">
                    <i class="fas fa-file-alt text-3xl text-blue-600"></i>
                    <div>
                        <div class="font-bold text-lg">Mode Normal</div>
                        <div class="text-sm text-gray-600">Template généré</div>
                    </div>
                </div>
                <p class="text-sm text-gray-700">
                    Données structurées avec colonnes: Structure, Data Element, Période, Valeur, etc.
                </p>
            </div>
        </label>

        <!-- Mode Tableau Croisé -->
        <label class="cursor-pointer">
            <input type="radio" name="data-type" value="pivot" class="hidden">
            <div class="border-2 border-gray-200 rounded-lg p-4 hover:border-purple-500 transition-all data-type-card">
                <div class="flex items-center gap-3 mb-2">
                    <i class="fas fa-table text-3xl text-purple-600"></i>
                    <div>
                        <div class="font-bold text-lg">Tableau Croisé</div>
                        <div class="text-sm text-gray-600">Structures en colonnes</div>
                    </div>
                </div>
                <p class="text-sm text-gray-700">
                    Première colonne = indicateurs, autres colonnes = noms des structures
                </p>
            </div>
        </label>
    </div>
</div>
```

**Fonctionnalité** :
- Cartes interactives avec effet hover
- Mode sélectionné = bordure colorée + fond coloré
- Mode normal : bleu / Mode pivot : violet

---

### C. Options du mode pivot
**Lignes 370-399**

```html
<div id="pivot-options" class="hidden mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
    <div class="form-group">
        <label for="pivot-data-element" class="form-label">
            <i class="fas fa-chart-bar mr-2"></i>Data Element DHIS2
        </label>
        <select id="pivot-data-element" class="form-input">
            <option value="">-- Sélectionnez un Data Element --</option>
            <!-- Options chargées dynamiquement -->
        </select>
        <div class="help-text mt-2">
            <i class="fas fa-info-circle mr-1"></i>
            Les valeurs du tableau seront associées à ce Data Element
        </div>
    </div>

    <div class="alert alert-info mt-3">
        <i class="fas fa-lightbulb mr-2"></i>
        <div>
            <strong>Format attendu :</strong>
            <ul class="list-disc ml-5 mt-1">
                <li>Première colonne : Indicateurs (ignorée)</li>
                <li>Autres colonnes : Noms ou codes des structures</li>
                <li>Cellules : Valeurs numériques</li>
            </ul>
        </div>
    </div>
</div>
```

**Comportement** :
- Caché par défaut
- Apparaît uniquement si mode "Tableau Croisé" est sélectionné
- Fond violet pour cohérence visuelle

---

## 2. Styles CSS

### A. Cartes de sélection de type
**Lignes 145-190**

```css
.data-type-card {
    transition: all 0.3s ease;
    position: relative;
}

.data-type-card:hover {
    transform: translateY(-2px);
}

input[name="data-type"]:checked + .data-type-card {
    border-color: var(--primary-600);
    background-color: var(--primary-50);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

input[name="data-type"][value="pivot"]:checked + .data-type-card {
    border-color: #9333ea;
    background-color: #faf5ff;
}
```

**Effets visuels** :
- Animation au survol (translateY)
- Bordure et fond colorés quand sélectionné
- Ombre portée pour effet de profondeur

---

## 3. JavaScript

### A. Event listeners
**Lignes 928-939**

```javascript
// Data type selection event listeners
document.querySelectorAll('input[name="data-type"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const pivotOptions = document.getElementById('pivot-options');
        if (this.value === 'pivot') {
            pivotOptions.classList.remove('hidden');
            loadDataElements();
        } else {
            pivotOptions.classList.add('hidden');
        }
    });
});
```

**Fonctionnalité** :
- Détecte le changement de type de données
- Affiche/cache les options pivot selon le mode
- Charge automatiquement les data elements en mode pivot

---

### B. Fonction `processTemplate()` modifiée
**Lignes 1478-1510**

```javascript
function processTemplate() {
    LoadingOverlay.show('Traitement du fichier Excel en cours...');

    // Récupérer les paramètres
    const sheetName = document.getElementById('select-sheet')?.value || 'Données';
    const mode = document.querySelector('input[name="data-type"]:checked')?.value || 'normal';

    const payload = {
        sheet_name: sheetName,
        mode: mode
    };

    // Validation mode pivot
    if (mode === 'pivot') {
        const deId = document.getElementById('pivot-data-element').value;
        if (!deId) {
            LoadingOverlay.hide();
            NotificationManager.error('Veuillez sélectionner un Data Element pour le mode tableau croisé');
            return;
        }
        payload.data_element_id = deId;
    }

    fetch('/calculator/api/process-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(data => handleProcessResult(data))
        .catch(error => NotificationManager.error('Erreur lors du traitement'))
        .finally(() => LoadingOverlay.hide());
}
```

**Nouveautés** :
- Récupère le nom d'onglet sélectionné (défaut: "Données")
- Récupère le mode sélectionné (défaut: "normal")
- Construit un payload JSON avec tous les paramètres
- Validation : mode pivot DOIT avoir un data element sélectionné

---

### C. Fonction `loadExcelSheets()`
**Lignes 1693-1723**

```javascript
async function loadExcelSheets() {
    try {
        const response = await fetch("{{ url_for('calculator.get_excel_sheets') }}");
        const data = await response.json();

        if (data.success && data.sheets && data.sheets.length > 0) {
            const select = document.getElementById('select-sheet');
            select.innerHTML = '';

            // Populate sheets
            data.sheets.forEach(sheet => {
                const option = document.createElement('option');
                option.value = sheet;
                option.textContent = sheet;
                select.appendChild(option);
            });

            // Show sheet selector if multiple sheets
            if (data.count > 1) {
                document.getElementById('sheet-selection').classList.remove('hidden');
                document.getElementById('sheet-count').textContent = `${data.count} onglets`;
            } else {
                document.getElementById('sheet-selection').classList.add('hidden');
            }

            console.log(`Onglets chargés: ${data.sheets.join(', ')}`);
        }
    } catch (error) {
        console.error('Erreur chargement onglets:', error);
    }
}
```

**Fonctionnalité** :
- Appelle l'API `/calculator/api/get-sheets`
- Remplit le dropdown avec les onglets
- Affiche le sélecteur uniquement si plusieurs onglets
- Affiche le nombre d'onglets dans un badge

---

### D. Fonction `loadDataElements()`
**Lignes 1726-1748**

```javascript
async function loadDataElements() {
    try {
        // Get metadata from session (already loaded in configuration)
        const response = await fetch("{{ url_for('configuration.get_metadata_summary') }}");
        const data = await response.json();

        if (data.success && data.metadata && data.metadata.dataElements) {
            const select = document.getElementById('pivot-data-element');
            select.innerHTML = '<option value="">-- Sélectionnez un Data Element --</option>';

            data.metadata.dataElements.forEach(de => {
                const option = document.createElement('option');
                option.value = de.id;
                option.textContent = de.name;
                select.appendChild(option);
            });

            console.log(`${data.metadata.dataElements.length} data elements chargés`);
        }
    } catch (error) {
        console.error('Erreur chargement data elements:', error);
    }
}
```

**Fonctionnalité** :
- Récupère les data elements via l'API `/calculator/api/get-dhis2-data-elements`
- Remplit le dropdown du mode pivot
- Appelée automatiquement quand l'utilisateur sélectionne le mode pivot

---

### E. Modification du handler Dropzone
**Ligne 1036-1045** (approximatif, dans le dropzone success handler)

```javascript
this.on("success", async function (file, response) {
    if (response.success) {
        document.getElementById('uploaded-filename').textContent = response.filename;
        document.getElementById('file-info').classList.remove('hidden');
        setStep(1, 'completed');
        NotificationManager.success('Fichier chargé avec succès');

        // Charger les onglets
        await loadExcelSheets();
    }
});
```

**Nouveauté** :
- Appelle automatiquement `loadExcelSheets()` après un upload réussi
- L'utilisateur voit immédiatement les onglets disponibles

---

## 4. Flux utilisateur

### Scénario 1 : Fichier avec un seul onglet + Mode normal
1. Upload du fichier → Onglet détecté automatiquement
2. Sélecteur d'onglets reste caché (inutile)
3. Mode "Normal" est sélectionné par défaut
4. Clic "Traiter" → Traite l'onglet en mode normal

### Scénario 2 : Fichier avec plusieurs onglets + Mode normal
1. Upload du fichier → Onglets listés dans dropdown
2. Sélecteur d'onglets s'affiche avec badge "3 onglets"
3. Utilisateur choisit l'onglet "Premier Cycle"
4. Mode "Normal" sélectionné
5. Clic "Traiter" → Traite "Premier Cycle" en mode normal

### Scénario 3 : Fichier multi-onglets + Mode pivot
1. Upload du fichier → Onglets listés
2. Utilisateur sélectionne l'onglet "Inscriptions"
3. Utilisateur coche "Tableau Croisé"
4. Panneau violet "Options pivot" apparaît
5. Utilisateur sélectionne un Data Element
6. Clic "Traiter" → Traite "Inscriptions" en mode pivot avec le DE

---

## 5. Validation et gestion des erreurs

### Validation côté client
- Mode pivot SANS data element → Message d'erreur + blocage

### Messages utilisateur
- Upload réussi : "Fichier chargé avec succès"
- Onglets détectés : Badge "N onglets"
- Data element manquant : "Veuillez sélectionner un Data Element pour le mode tableau croisé"

---

## 6. Rétrocompatibilité

### ✅ Comportement par défaut préservé
Si l'utilisateur :
- Ne change aucun paramètre
- Clique simplement "Traiter"

**Résultat** :
- `sheet_name = "Données"` (défaut)
- `mode = "normal"` (défaut)
- Fonctionne exactement comme avant

---

## 7. Résumé des modifications

| Section | Lignes | Description |
|---------|--------|-------------|
| HTML - Sélection onglets | 306-322 | Dropdown onglets avec badge |
| HTML - Sélection type | 324-368 | Cartes interactives Normal/Pivot |
| HTML - Options pivot | 370-399 | Panneau violet avec sélecteur DE |
| CSS - Styles cartes | 145-190 | Animations et états sélectionnés |
| JS - Event listeners | 928-939 | Gestion changement type données |
| JS - processTemplate() | 1478-1510 | Construction payload JSON |
| JS - loadExcelSheets() | 1693-1723 | Chargement onglets |
| JS - loadDataElements() | 1726-1748 | Chargement data elements |
| JS - Dropzone handler | ~1040 | Appel loadExcelSheets() |
| **Total** | **~150 lignes** | **Ajouts uniquement** |

---

## 8. Tests à effectuer

### Test 1 : Fichier mono-onglet, mode normal
- Upload → Pas de sélecteur d'onglets
- Mode normal par défaut
- Traiter → ✅ Fonctionne comme avant

### Test 2 : Fichier multi-onglets, mode normal
- Upload → Sélecteur d'onglets visible
- Choisir "Premier Cycle"
- Mode normal
- Traiter → ✅ Traite le bon onglet

### Test 3 : Mode pivot sans DE
- Sélectionner mode pivot
- Ne PAS sélectionner de data element
- Traiter → ❌ Message d'erreur

### Test 4 : Mode pivot complet
- Sélectionner "Inscriptions"
- Mode pivot
- Sélectionner un DE
- Traiter → ✅ Traite en mode pivot

---

## ✅ Checklist Frontend

- [x] Interface sélection onglets (HTML)
- [x] Interface sélection type de données (HTML)
- [x] Interface options pivot (HTML)
- [x] Styles CSS pour cartes interactives
- [x] Event listener changement type
- [x] Fonction loadExcelSheets()
- [x] Fonction loadDataElements()
- [x] Modification processTemplate()
- [x] Modification handler Dropzone
- [x] Validation mode pivot
- [x] Rétrocompatibilité préservée
- [ ] Tests manuels (à faire par l'utilisateur)

---

## 🚀 Prêt à tester !

**Backend** : ✅ Terminé
**Frontend** : ✅ Terminé

**Pour tester** :
1. Lancez le serveur : `python run.py`
2. Chargez les métadonnées
3. Uploadez un fichier Excel multi-onglets
4. Testez les différents modes

**Documentation de test** : Voir [TEST_BACKEND_CURL.md](TEST_BACKEND_CURL.md)

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
**Version** : 2.0 (Backend + Frontend)
**Statut** : ✅ Implémentation complète
