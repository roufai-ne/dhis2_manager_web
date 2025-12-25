Dropzone.autoDiscover = false;

let templateDropzone, mappingDropzone;
let excelColumns = [];
let datasetCategories = [];
let datasetElements = [];
let metadataFilters = {
    org_unit_groups: [],
    org_unit_levels: [],
    data_element_groups: []
};

function updateCalculatorPeriodOptions(typeSelectId, periodSelectId) {
    const typeSelect = document.getElementById(typeSelectId);
    const periodSelect = document.getElementById(periodSelectId);
    const periodType = typeSelect.value;

    periodSelect.innerHTML = ''; // Clear

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth(); // 0-11

    let options = [];

    if (periodType === 'Monthly') {
        // Last 18 months + Next 6 months
        for (let i = -18; i <= 6; i++) {
            const d = new Date(currentYear, currentMonth + i, 1);
            const year = d.getFullYear();
            const month = d.getMonth() + 1;
            const monthStr = month < 10 ? '0' + month : month;
            const label = d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
            const formattedLabel = label.charAt(0).toUpperCase() + label.slice(1);
            options.push({ value: `${year}${monthStr}`, label: formattedLabel, sort: d.getTime() });
        }
    }
    else if (periodType === 'Quarterly') {
        // Last 3 years + Next 1 year
        for (let y = currentYear - 3; y <= currentYear + 1; y++) {
            for (let q = 1; q <= 4; q++) {
                options.push({ value: `${y}Q${q}`, label: `${y} - Trimestre ${q}`, sort: parseInt(`${y}${q}`) });
            }
        }
    }
    else if (periodType === 'SixMonthly') {
        // Last 5 years + Next 1 year
        for (let y = currentYear - 5; y <= currentYear + 1; y++) {
            options.push({ value: `${y}S1`, label: `${y} - Semestre 1 (Jan-Juin)`, sort: parseInt(`${y}1`) });
            options.push({ value: `${y}S2`, label: `${y} - Semestre 2 (Juil-Déc)`, sort: parseInt(`${y}2`) });
        }
    }
    else if (periodType === 'Yearly' || periodType === 'FinancialYear') {
        // Last 10 years + Next 2 years
        for (let y = currentYear - 10; y <= currentYear + 2; y++) {
            options.push({ value: `${y}`, label: `${y}`, sort: y });
        }
    }
    else {
        // Fallback
        for (let y = currentYear - 5; y <= currentYear + 2; y++) {
            options.push({ value: `${y}`, label: `${y}`, sort: y });
        }
    }

    // Sort descending
    options.sort((a, b) => b.sort - a.sort);

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        periodSelect.appendChild(option);
    });

    // Select first automatically (most recent)
    if (options.length > 0) {
        periodSelect.value = options[0].value;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Period Dropdowns
    updateCalculatorPeriodOptions('pivot-period-type', 'pivot-period');
    updateCalculatorPeriodOptions('auto-period-type', 'auto-period');

    initializeDropzone();
    loadMetadataFilters();

    // Event listeners
    // Mode switching
    document.querySelectorAll('input[name="processing-mode"]').forEach(radio => {
        radio.addEventListener('change', function () {
            // Hide all sections
            document.getElementById('template-upload-section').classList.add('hidden');
            document.getElementById('auto-sections').classList.add('hidden');

            // Show selected section
            if (this.value === 'template') {
                document.getElementById('template-upload-section').classList.remove('hidden');
            } else if (this.value === 'auto') {
                document.getElementById('auto-sections').classList.remove('hidden');
            }
        });
    });

    document.getElementById('mapping-dataset').addEventListener('change', onDatasetChange);
    document.getElementById('btn-process').addEventListener('click', processFile);
    document.getElementById('btn-process-mapping').addEventListener('click', processFile);
    document.getElementById('btn-new-calculation').addEventListener('click', () => window.location.reload());

    // JSON Preview/Download buttons
    document.getElementById('btn-preview-json').addEventListener('click', previewJson);
    document.getElementById('btn-close-preview').addEventListener('click', closeJsonPreview);
    document.getElementById('btn-download-json').addEventListener('click', downloadJson);
    const btnDownloadCsvNames = document.getElementById('btn-download-csv-names');
    if (btnDownloadCsvNames) {
        btnDownloadCsvNames.addEventListener('click', function () {
            window.open('/calculator/api/download-csv-names', '_blank');
        });
    }
    const btnSend = document.getElementById('btn-send-dhis2');
    if (btnSend) btnSend.addEventListener('click', sendToDhis2);

    // AI Analysis
    document.getElementById('btn-analyze-ai').addEventListener('click', analyzeWithAI);

    // Data type selection event listeners
    document.querySelectorAll('input[name="data-type"]').forEach(radio => {
        radio.addEventListener('change', function () {
            const pivotOptions = document.getElementById('pivot-options');
            if (this.value === 'pivot') {
                pivotOptions.classList.remove('hidden');
                loadDataElements();
            } else {
                pivotOptions.classList.add('hidden');
            }
        });
    });

    // Load datasets
    fetch('/configuration/api/datasets')
        .then(r => r.json())
        .then(data => {
            const select = document.getElementById('mapping-dataset');
            data.datasets.forEach(ds => {
                const option = document.createElement('option');
                option.value = ds.id;
                option.textContent = ds.name;
                select.appendChild(option);
            });
        })
        .catch(() => NotificationManager.error('Erreur lors du chargement des datasets'));
});

function loadMetadataFilters() {
    fetch('/calculator/api/get-metadata-filters')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                metadataFilters = data;

                // Populate Org Unit Filters
                const groupSelect = document.getElementById('filter-org-group');
                data.org_unit_groups.forEach(g => {
                    const opt = document.createElement('option');
                    opt.value = g.id;
                    opt.textContent = g.name;
                    groupSelect.appendChild(opt);
                });

                const levelSelect = document.getElementById('filter-org-level');
                data.org_unit_levels.forEach(l => {
                    const opt = document.createElement('option');
                    opt.value = l.level;
                    opt.textContent = l.name;
                    levelSelect.appendChild(opt);
                });
            }
        })
        .catch(e => console.error('Error loading filters:', e));
}

function toggleOrgMode() {
    const mode = document.querySelector('input[name="org-mode"]:checked').value;
    if (mode === 'column') {
        document.getElementById('org-mode-column').classList.remove('hidden');
        document.getElementById('org-mode-fixed').classList.add('hidden');
    } else {
        document.getElementById('org-mode-column').classList.add('hidden');
        document.getElementById('org-mode-fixed').classList.remove('hidden');
        // Load initial list if empty
        if (document.getElementById('map-org-fixed').options.length <= 1) {
            updateOrgUnitList();
        }
    }
}

function updateOrgUnitList() {
    const groupId = document.getElementById('filter-org-group').value;
    const level = document.getElementById('filter-org-level').value;
    const select = document.getElementById('map-org-fixed');
    const hint = document.getElementById('org-count-hint');

    select.innerHTML = '<option value="">Chargement...</option>';
    select.disabled = true;

    fetch('/calculator/api/get-filtered-org-units', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: groupId, level: level })
    })
        .then(r => r.json())
        .then(data => {
            select.innerHTML = '<option value="">-- Sélectionnez une organisation --</option>';
            if (data.success) {
                data.org_units.forEach(ou => {
                    const opt = document.createElement('option');
                    opt.value = ou.id;
                    opt.textContent = ou.name;
                    select.appendChild(opt);
                });
                hint.textContent = `${data.count} organisation(s) trouvée(s)`;
                if (data.count >= 1000) {
                    hint.textContent += ' (Limité à 1000)';
                }
            }
        })
        .catch(e => {
            console.error(e);
            select.innerHTML = '<option value="">Erreur</option>';
        })
        .finally(() => {
            select.disabled = false;
        });
}

function initializeDropzone() {
    // Template dropzone
    templateDropzone = new Dropzone('#excel-dropzone', {
        url: window.CalculatorConfig.uploadUrl,
        maxFiles: 1,
        maxFilesize: 50,
        acceptedFiles: '.xlsx,.xls',
        addRemoveLinks: true,
        dictDefaultMessage: '',

        init: function () {
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

            this.on("error", function (file, errorMessage) {
                const msg = typeof errorMessage === 'object' ? errorMessage.error : errorMessage;
                NotificationManager.error(msg);
                this.removeFile(file);
            });
        }
    });

    // Mapping dropzone
    mappingDropzone = new Dropzone('#mapping-dropzone', {
        url: window.CalculatorConfig.uploadUrl,
        maxFiles: 1,
        maxFilesize: 50,
        acceptedFiles: '.xlsx,.xls',
        addRemoveLinks: true,
        dictDefaultMessage: '',

        init: function () {
            this.on("success", function (file, response) {
                if (response.success) {
                    document.getElementById('mapping-filename').textContent = response.filename;
                    document.getElementById('mapping-file-info').classList.remove('hidden');
                    document.getElementById('ai-analysis-section').classList.remove('hidden'); // Show AI button
                    NotificationManager.success('Fichier chargé avec succès');

                    // Charger les onglets pour le mode mapping (qui chargera ensuite les colonnes)
                    loadMappingSheets();
                }
            });

            this.on("error", function (file, errorMessage) {
                const msg = typeof errorMessage === 'object' ? errorMessage.error : errorMessage;
                NotificationManager.error(msg);
                this.removeFile(file);
            });
        }
    });
}

function analyzeWithAI() {
    if (!mappingDropzone.files || mappingDropzone.files.length === 0) {
        NotificationManager.error('Veuillez d\'abord charger un fichier Excel');
        return;
    }

    const file = mappingDropzone.files[0];
    const formData = new FormData();
    formData.append('file', file);

    LoadingOverlay.show('Analyse IA en cours...');

    // D'abord essayer de détecter le format pivoté
    fetch('/calculator/api/extract-pivoted-data-elements', {
        method: 'POST',
        body: formData
    })
        .then(r => r.json())
        .then(data => {
            if (data.success && data.format === 'pivoted' && data.statistics.matched_with_dhis2 > 0) {
                // Format pivoté détecté avec des matches
                LoadingOverlay.hide();
                showPivotedMappingInterface(data);

                const colsList = data.data_element_columns.join(', ');
                NotificationManager.success(
                    `✓ Format pivoté détecté!\n` +
                    `${data.statistics.matched_with_dhis2} DE auto-matchés, ${data.statistics.unmatched} à mapper.\n` +
                    `Colonnes DE: ${colsList}`
                );
            } else {
                // Format classique, utiliser l'analyse normale
                return fetch('/calculator/api/analyze-file', {
                    method: 'POST',
                    body: formData
                });
            }
        })
        .then(r => r ? r.json() : null)
        .then(data => {
            if (data) {
                if (data.success) {
                    applyAISuggestions(data);
                    NotificationManager.success('Analyse terminée ! Configuration appliquée.');
                } else {
                    NotificationManager.error(data.error || 'Erreur lors de l\'analyse');
                }
            }
        })
        .catch(e => NotificationManager.error('Erreur réseau: ' + e.message))
        .finally(() => LoadingOverlay.hide());
}

function applyAISuggestions(data) {
    console.log('AI Analysis Result:', data);

    // Show AI result badge with confidence color
    const badge = document.getElementById('ai-result-badge');
    badge.classList.remove('hidden');

    const confidence = Math.round(data.confidence * 100);
    document.getElementById('ai-confidence').textContent = confidence;

    // Color code based on confidence
    const badgeElement = badge.querySelector('span');
    if (confidence >= 80) {
        badgeElement.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
    } else if (confidence >= 60) {
        badgeElement.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800';
    } else {
        badgeElement.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800';
    }

    // Show reasoning
    let reasoningHtml = `<strong>Analyse:</strong> ${data.reasoning}`;

    // Show warnings if any
    if (data.warnings && data.warnings.length > 0) {
        reasoningHtml += `<br><br><strong class="text-orange-600">⚠️ Avertissements:</strong><ul class="list-disc ml-5 mt-1">`;
        data.warnings.forEach(w => {
            reasoningHtml += `<li>${w}</li>`;
        });
        reasoningHtml += `</ul>`;
    }

    document.getElementById('ai-reasoning').innerHTML = reasoningHtml;

    // Show mapping configuration section
    document.getElementById('mapping-config').classList.remove('hidden');

    // Set Processing Mode
    const modeRadio = document.querySelector(`input[name="processing-mode-mapping"][value="${data.processing_mode}"]`);
    if (modeRadio) {
        modeRadio.checked = true;
        console.log(`Set processing mode to: ${data.processing_mode}`);
    }

    // Apply Column Mappings
    if (data.mapping) {
        const m = data.mapping;
        console.log('Applying mappings:', m);

        // Org Unit
        if (m.org_unit) {
            const orgModeRadio = document.querySelector('input[name="org-mode"][value="column"]');
            if (orgModeRadio) {
                orgModeRadio.checked = true;
                toggleOrgMode();
                setTimeout(() => {
                    setSelectValue('map-org', m.org_unit);
                    console.log(`Mapped org_unit to column: ${m.org_unit}`);
                }, 100);
            }
        }

        // Period - Try to extract from data if it's a column
        if (m.period) {
            console.log(`Period column detected: ${m.period} (manual mapping may be required)`);
            NotificationManager.info(`Période détectée dans la colonne "${m.period}". Vérifiez le format dans les données.`);
        }

        // Data Element
        if (m.data_element) {
            setTimeout(() => {
                const deSelect = document.getElementById('map-data-element');
                if (deSelect) {
                    setSelectValue('map-data-element', m.data_element);
                    console.log(`Mapped data_element to column: ${m.data_element}`);
                }
            }, 100);
        }

        // Value Column (for values mode)
        if (data.processing_mode === 'values' && m.value) {
            setTimeout(() => {
                const valueSelect = document.getElementById('map-value-column');
                if (valueSelect) {
                    setSelectValue('map-value-column', m.value);
                    console.log(`Mapped value to column: ${m.value}`);
                }
            }, 100);
        }

        // Categories - Apply to category mapping dropdowns
        if (m.categories && Array.isArray(m.categories) && m.categories.length > 0) {
            setTimeout(() => {
                const catMappings = document.querySelectorAll('.category-mapping');
                m.categories.forEach((catCol, idx) => {
                    if (catMappings[idx]) {
                        setSelectValue(catMappings[idx].id, catCol);
                        console.log(`Mapped category ${idx} to column: ${catCol}`);
                    }
                });

                if (m.categories.length > 0) {
                    NotificationManager.info(`${m.categories.length} catégorie(s) détectée(s): ${m.categories.join(', ')}`);
                }
            }, 200);
        }
    }

    // Show success message with confidence level
    if (confidence >= 80) {
        NotificationManager.success(`Analyse IA complète! Confiance élevée (${confidence}%). Vérifiez les mappings suggérés.`);
    } else if (confidence >= 60) {
        NotificationManager.warning(`Analyse IA terminée avec confiance moyenne (${confidence}%). Vérifiez attentivement les mappings.`);
    } else {
        NotificationManager.warning(`Analyse IA terminée mais confiance faible (${confidence}%). Corrigez manuellement les mappings.`);
    }

    // Scroll to config
    document.getElementById('mapping-config').scrollIntoView({ behavior: 'smooth' });
}

function setSelectValue(selectId, value) {
    const select = document.getElementById(selectId);
    if (!select) return;

    // Find option with text matching value (fuzzy match?)
    for (let i = 0; i < select.options.length; i++) {
        if (select.options[i].text === value) {
            select.selectedIndex = i;
            return;
        }
    }
}

function onDatasetChange() {
    const datasetId = document.getElementById('mapping-dataset').value;
    if (!datasetId) return;

    LoadingOverlay.show('Chargement des informations du dataset...');

    fetch('/calculator/api/get-dataset-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                datasetCategories = data.categories || [];
                datasetElements = data.data_elements || [];
                document.getElementById('dataset-period-type').textContent = data.period_type || 'N/A';
                document.getElementById('dataset-categories').textContent =
                    datasetCategories.map(c => c.name).join(', ') || 'Aucune';
                document.getElementById('dataset-info').classList.remove('hidden');

                if (excelColumns.length > 0) {
                    buildMappingInterface();
                }
            }
        })
        .catch(error => NotificationManager.error('Erreur lors du chargement des informations'))
        .finally(() => LoadingOverlay.hide());
}

function loadExcelColumns() {
    LoadingOverlay.show('Lecture des colonnes Excel...');

    // Get selected sheet from mapping mode
    const sheetSelector = document.getElementById('mapping-select-sheet');
    const sheetName = sheetSelector ? sheetSelector.value : null;

    console.log(`[loadExcelColumns] Sheet sélectionné: ${sheetName}`);

    // Build URL with sheet parameter
    let url = '/calculator/api/get-columns';
    if (sheetName) {
        url += `?sheet_name=${encodeURIComponent(sheetName)}`;
        console.log(`[loadExcelColumns] URL avec sheet: ${url}`);
    } else {
        console.log(`[loadExcelColumns] Aucun sheet spécifié, utilise le premier par défaut`);
    }

    fetch(url, {
        method: 'GET'
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                excelColumns = data.columns;
                NotificationManager.success(`${excelColumns.length} colonnes détectées`);

                const datasetId = document.getElementById('mapping-dataset').value;
                if (datasetId) {
                    buildMappingInterface();
                } else {
                    NotificationManager.info('Veuillez sélectionner un dataset');
                }
            }
        })
        .catch(error => NotificationManager.error('Erreur lors de la lecture des colonnes'))
        .finally(() => LoadingOverlay.hide());
}

function buildMappingInterface() {
    // Populate organisation mapping (Column Mode)
    populateSelect('map-org', excelColumns);

    // Build category mappings
    const categoryMappingsDiv = document.getElementById('category-mappings');
    categoryMappingsDiv.innerHTML = '';

    // Add category mappings if any
    datasetCategories.forEach((cat, index) => {
        const mappingRow = document.createElement('div');
        mappingRow.className = 'mapping-row';
        mappingRow.innerHTML = `
                <div class="mapping-label">
                    <i class="fas fa-tag text-orange-600 mr-2"></i>
                    ${cat.name}
                    <span class="text-red-500">*</span>
                </div>
                <div class="mapping-arrow">
                    <i class="fas fa-arrow-right"></i>
                </div>
                <div class="mapping-select">
                    <select id="map-cat-${cat.id}" class="form-input category-mapping" data-cat-id="${cat.id}">
                        <option value="">-- Sélectionnez une colonne --</option>
                    </select>
                </div>
            `;
        categoryMappingsDiv.appendChild(mappingRow);
        populateSelect(`map-cat-${cat.id}`, excelColumns);
    });

    // Add data element mappings
    const dataElementsDiv = document.createElement('div');

    // Filter Header
    const filterHeader = document.createElement('div');
    filterHeader.className = 'flex items-center justify-between mt-6 mb-4';
    filterHeader.innerHTML = `
            <h3 class="text-lg font-bold text-gray-900 flex items-center">
                <i class="fas fa-list mr-2 text-blue-600"></i>
                Mappez les data elements
            </h3>
            <div class="flex items-center gap-2">
                <label class="text-sm text-gray-600">Filtrer par groupe:</label>
                <select id="de-group-filter" class="form-select text-sm rounded-md border-gray-300" onchange="filterDataElements()">
                    <option value="">Tous les groupes</option>
                </select>
            </div>
        `;
    dataElementsDiv.appendChild(filterHeader);

    // DE List Container
    const deListContainer = document.createElement('div');
    deListContainer.id = 'de-list-container';
    dataElementsDiv.appendChild(deListContainer);

    categoryMappingsDiv.appendChild(dataElementsDiv);

    // Populate DE Group Filter
    const groupFilter = document.getElementById('de-group-filter');
    metadataFilters.data_element_groups.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.name;
        groupFilter.appendChild(opt);
    });

    // Build DE Rows
    datasetElements.forEach((de, index) => {
        const mappingRow = document.createElement('div');
        mappingRow.className = 'mapping-row de-row';
        // Store groups as data attribute for filtering
        const groups = de.groups ? de.groups.map(g => g.id).join(',') : '';
        mappingRow.dataset.groups = groups;

        mappingRow.innerHTML = `
                <div class="mapping-label" title="${de.name}">
                    <i class="fas fa-chart-bar text-blue-600 mr-2"></i>
                    <span class="truncate block">${de.name}</span>
                </div>
                <div class="mapping-arrow">
                    <i class="fas fa-arrow-right"></i>
                </div>
                <div class="mapping-select">
                    <select id="map-de-${de.id}" class="form-input de-mapping" data-de-id="${de.id}">
                        <option value="">-- Optionnel --</option>
                    </select>
                </div>
            `;
        deListContainer.appendChild(mappingRow);
        populateSelect(`map-de-${de.id}`, excelColumns);
    });

    document.getElementById('mapping-config').classList.remove('hidden');
}

function filterDataElements() {
    const groupId = document.getElementById('de-group-filter').value;
    const rows = document.querySelectorAll('.de-row');

    rows.forEach(row => {
        if (!groupId) {
            row.classList.remove('hidden');
        } else {
            const groups = row.dataset.groups ? row.dataset.groups.split(',') : [];
            if (groups.includes(groupId)) {
                row.classList.remove('hidden');
            } else {
                row.classList.add('hidden');
            }
        }
    });
}

function populateSelect(selectId, columns) {
    const select = document.getElementById(selectId);
    // Clear existing options except first
    while (select.options.length > 1) {
        select.remove(1);
    }

    columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        select.appendChild(option);
    });
}

function processFile() {
    const mode = document.querySelector('input[name="processing-mode"]:checked').value;

    if (mode === 'template') {
        processTemplate();
    } else {
        processMapping();
    }
}

function processTemplate() {
    LoadingOverlay.show('Traitement du fichier Excel en cours...');

    // Récupérer les paramètres
    const sheetName = document.getElementById('select-sheet')?.value || 'Données';
    const mode = document.querySelector('input[name="data-type"]:checked')?.value || 'normal';

    const payload = {
        sheet_name: sheetName,
        mode: mode
    };

    // Mode pivot/TCD
    if (mode === 'pivot') {
        // Période (requise)
        const period = document.getElementById('pivot-period')?.value?.trim();
        if (!period) {
            LoadingOverlay.hide();
            NotificationManager.error('Veuillez entrer une période pour le mode tableau croisé');
            return;
        }
        payload.period = period;

        // Data Element (optionnel - auto-détection si vide)
        const deId = document.getElementById('pivot-data-element')?.value;
        if (deId) {
            payload.data_element_id = deId;
        }
        // Si vide, les DE seront auto-détectés depuis la première colonne
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

function processMapping() {
    const datasetId = document.getElementById('mapping-dataset').value;
    const period = document.getElementById('mapping-period').value;
    const processingMode = document.querySelector('input[name="processing-mode-mapping"]:checked').value;

    // Org Unit Logic
    const orgMode = document.querySelector('input[name="org-mode"]:checked').value;
    let orgColumn = null;
    let fixedOrgUnit = null;

    if (orgMode === 'column') {
        orgColumn = document.getElementById('map-org').value;
        if (!orgColumn) {
            NotificationManager.error('Veuillez sélectionner une colonne pour l\'organisation');
            return;
        }
    } else {
        fixedOrgUnit = document.getElementById('map-org-fixed').value;
        if (!fixedOrgUnit) {
            NotificationManager.error('Veuillez sélectionner une organisation fixe');
            return;
        }
    }

    if (!period) {
        NotificationManager.error('Veuillez saisir une période');
        return;
    }

    // Collect mappings
    const categoryMapping = {};
    document.querySelectorAll('.category-mapping').forEach(select => {
        if (select.value) {
            categoryMapping[select.dataset.catId] = select.value;
        }
    });

    const dataElementMapping = {};
    document.querySelectorAll('.de-mapping').forEach(select => {
        if (select.value) {
            dataElementMapping[select.dataset.deId] = select.value;
        }
    });

    LoadingOverlay.show('Traitement du mapping en cours...');

    fetch('/calculator/api/process-custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            dataset_id: datasetId,
            period: period,
            org_column: orgColumn,
            org_mode: orgMode,
            fixed_org_unit: fixedOrgUnit,
            category_mapping: categoryMapping,
            data_element_mapping: dataElementMapping,
            processing_mode: processingMode
        })
    })
        .then(r => r.json())
        .then(data => handleProcessResult(data))
        .catch(error => NotificationManager.error('Erreur lors du traitement'))
        .finally(() => LoadingOverlay.hide());
}

function handleProcessResult(data) {
    if (data.success) {
        // Update stats
        document.getElementById('stat-total').textContent = data.total_values;
        document.getElementById('stat-valid').textContent = data.stats.valid;
        document.getElementById('stat-errors').textContent = data.stats.errors;

        const errorRate = data.total_values > 0
            ? Math.round((data.stats.errors / data.total_values) * 100)
            : 0;
        document.getElementById('stat-error-rate').textContent = errorRate + '%';

        // Show errors if any
        const errorDetails = document.getElementById('error-details');
        const errorList = document.getElementById('error-list');
        errorList.innerHTML = '';

        if (data.stats.errors > 0 && data.stats.error_details) {
            data.stats.error_details.slice(0, 10).forEach(err => {
                const div = document.createElement('div');
                div.className = 'text-sm text-red-700 mb-1';
                div.textContent = `Ligne ${err.row}: ${err.message}`;
                errorList.appendChild(div);
            });
            if (data.stats.error_details.length > 10) {
                const more = document.createElement('div');
                more.className = 'text-sm font-bold mt-2';
                more.textContent = `... et ${data.stats.error_details.length - 10} autres erreurs`;
                errorList.appendChild(more);
            }
            errorDetails.classList.remove('hidden');
        } else {
            errorDetails.classList.add('hidden');
        }

        // Show preview
        const tbody = document.getElementById('preview-tbody');
        tbody.innerHTML = '';
        data.preview.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                    <td class="px-4 py-2 border-b">${row.dataElement}</td>
                    <td class="px-4 py-2 border-b">${row.period}</td>
                    <td class="px-4 py-2 border-b">${row.orgUnit}</td>
                    <td class="px-4 py-2 border-b font-mono">${row.value}</td>
                `;
            tbody.appendChild(tr);
        });

        // Show results section
        document.getElementById('results-section').classList.remove('hidden');
        document.getElementById('download-section').classList.remove('hidden');

        // Update JSON info
        document.getElementById('json-info').textContent =
            `Fichier: ${data.json_filename} (${data.total_values} valeurs)`;

        setStep(2, 'completed');
        setStep(3, 'active');

        // Scroll to results
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
    } else {
        NotificationManager.error(data.error || 'Erreur inconnue');
        if (data.details) {
            displayValidationErrors(data.details);
        }
    }
}

function previewJson() {
    LoadingOverlay.show('Chargement de l\'aperçu...');
    fetch('/calculator/api/preview-json')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('json-preview-container');
            const content = document.getElementById('json-content');

            // Clear content
            content.innerHTML = '';
            // remove pre property if it was there
            content.removeAttribute('style');

            // Create Data Grid
            if (data.dataValues && Array.isArray(data.dataValues)) {
                const wrapper = document.createElement('div');
                wrapper.className = 'overflow-auto max-h-[500px] border border-gray-200 rounded-lg shadow-inner bg-white';

                const table = document.createElement('table');
                table.className = 'min-w-full divide-y divide-gray-200 text-sm';
                const thead = document.createElement('thead');
                thead.className = 'bg-gray-50 sticky top-0 shadow-sm';
                thead.innerHTML = `
                        <tr>
                            <th class="px-4 py-3 text-left font-bold text-gray-700 border-b">Data Element</th>
                            <th class="px-4 py-3 text-left font-bold text-gray-700 border-b">Organisation</th>
                            <th class="px-4 py-3 text-left font-bold text-gray-700 border-b">Période</th>
                            <th class="px-4 py-3 text-left font-bold text-gray-700 border-b">COC</th>
                            <th class="px-4 py-3 text-right font-bold text-gray-700 border-b">Valeur</th>
                        </tr>
                    `;
                table.appendChild(thead);

                const tbody = document.createElement('tbody');
                tbody.className = 'bg-white divide-y divide-gray-200';

                data.dataValues.forEach(row => {
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-blue-50 transition-colors duration-150';
                    tr.innerHTML = `
                             <td class="px-4 py-2 font-medium text-gray-900">${row.dataElement}</td>
                             <td class="px-4 py-2 text-gray-600">${row.orgUnit}</td>
                             <td class="px-4 py-2 text-gray-600">${row.period}</td>
                             <td class="px-4 py-2 text-gray-500 text-xs">${row.categoryOptionCombo || '-'}</td>
                             <td class="px-4 py-2 text-right font-mono font-bold text-blue-600">${row.value}</td>
                         `;
                    tbody.appendChild(tr);
                });

                table.appendChild(tbody);

                wrapper.appendChild(table);
                content.appendChild(wrapper);

                // Add summary
                const summary = document.createElement('div');
                summary.className = 'flex justify-between items-center mt-3 text-sm text-gray-500 px-1';
                summary.innerHTML = `
                        <span><i class="fas fa-table mr-2"></i>Tableau de données</span>
                        <span class="font-bold">Total: ${data.dataValues.length} enregistrements</span>
                    `;
                content.appendChild(summary);

            } else {
                // Fallback to JSON dump
                const pre = document.createElement('pre');
                pre.className = 'bg-gray-800 text-green-400 p-4 rounded overflow-auto max-h-96 text-xs font-mono';
                pre.textContent = JSON.stringify(data, null, 2);
                content.appendChild(pre);
            }

            container.classList.remove('hidden');
            container.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(e => {
            console.error(e);
            NotificationManager.error('Erreur lors de l\'aperçu');
        })
        .finally(() => LoadingOverlay.hide());
}

function closeJsonPreview() {
    document.getElementById('json-preview-container').classList.add('hidden');
}

function downloadJson() {
    window.location.href = '/calculator/api/download-json';
}

function sendToDhis2() {
    NotificationManager.warning('Envoi vers DHIS2 en cours...', 'Confirmation');

    setTimeout(() => {
        LoadingOverlay.show('Envoi vers DHIS2 en cours...');

        fetch('/calculator/api/send-to-dhis2', {
            method: 'POST'
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    NotificationManager.success(data.message);
                    // Show details if available
                    if (data.details && data.details.importCount) {
                        const counts = data.details.importCount;
                        NotificationManager.info(
                            `Importés: ${counts.imported} | Mis à jour: ${counts.updated} | Ignorés: ${counts.ignored} | Supprimés: ${counts.deleted}`,
                            'Détails de l\'import'
                        );
                    }
                } else {
                    NotificationManager.error(data.error || 'Erreur lors de l\'envoi');
                }
            })
            .catch(e => NotificationManager.error('Erreur réseau'))
            .finally(() => LoadingOverlay.hide());
    }, 100);
}

// Load Excel sheets
async function loadExcelSheets() {
    try {
        const response = await fetch(window.CalculatorConfig.getSheetsUrl);
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

// Load sheets for mapping mode
async function loadMappingSheets() {
    try {
        const response = await fetch(window.CalculatorConfig.getSheetsUrl);
        const data = await response.json();

        if (data.success && data.sheets && data.sheets.length > 0) {
            const select = document.getElementById('mapping-select-sheet');
            select.innerHTML = '';

            // Populate sheets
            data.sheets.forEach(sheet => {
                const option = document.createElement('option');
                option.value = sheet;
                option.textContent = sheet;
                select.appendChild(option);
            });

            // Auto-reload columns when sheet changes
            select.addEventListener('change', function () {
                loadExcelColumns();
            });

            console.log(`[Mapping] Onglets chargés: ${data.sheets.join(', ')}`);

            // Charger les colonnes du premier onglet par défaut
            loadExcelColumns();
        }
    } catch (error) {
        console.error('Erreur chargement onglets mapping:', error);
    }
}

// Load data elements for pivot mode
async function loadDataElements() {
    try {
        // Get data elements from the calculator API
        const response = await fetch(window.CalculatorConfig.getDhis2DeUrl);
        const data = await response.json();

        if (data.success && data.data_elements) {
            const select = document.getElementById('pivot-data-element');
            select.innerHTML = '<option value="">-- Sélectionnez un Data Element --</option>';

            data.data_elements.forEach(de => {
                const option = document.createElement('option');
                option.value = de.id;
                option.textContent = de.name;
                select.appendChild(option);
            });

            console.log(`${data.count} data elements chargés`);
        }
    } catch (error) {
        console.error('Erreur chargement data elements:', error);
    }
}

function setStep(step, status) {
    const el = document.getElementById(`step-${step}`);
    if (status === 'active') {
        el.classList.add('active');
        el.classList.remove('completed');
    } else if (status === 'completed') {
        el.classList.add('completed');
        el.classList.remove('active');
    } else {
        el.classList.remove('active', 'completed');
    }
}

function displayValidationErrors(errors) {
    // Implementation depends on how errors are formatted
    console.error(errors);
    NotificationManager.error('Erreurs de validation détectées. Consultez la console pour plus de détails.');
}

// ========== PIVOTED FORMAT FUNCTIONS ==========
let pivotedData = null;
let dhis2DataElements = [];

// Load DHIS2 DE list for dropdowns
fetch('/calculator/api/get-dhis2-data-elements')
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            dhis2DataElements = data.data_elements;
            console.log(`Loaded ${dhis2DataElements.length} DHIS2 data elements for pivoted mapping`);
        }
    })
    .catch(err => console.error('Error loading DHIS2 DE:', err));

function showPivotedMappingInterface(data) {
    pivotedData = data;

    // Hide normal mapping, show pivoted
    document.getElementById('mapping-config').classList.add('hidden');
    document.getElementById('pivoted-mapping').classList.remove('hidden');

    // Update statistics
    document.getElementById('pivot-stat-total').textContent = data.statistics.total_data_elements;
    document.getElementById('pivot-stat-matched').textContent = data.statistics.matched_with_dhis2;
    document.getElementById('pivot-stat-unmatched').textContent = data.statistics.unmatched;
    document.getElementById('pivot-stat-sections').textContent = data.statistics.total_sections;

    // Build sections view
    const container = document.getElementById('pivoted-sections-container');
    container.innerHTML = '';

    for (const [sectionName, dataElements] of Object.entries(data.sections_mapping)) {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'mb-8';

        const matchedCount = dataElements.filter(de => de.dhis2_matched).length;

        sectionDiv.innerHTML = `
                <h3 class="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <i class="fas fa-folder-open text-purple-600"></i>
                    ${sectionName}
                    <span class="text-sm font-normal text-gray-500">(${dataElements.length} éléments, ${matchedCount} auto-matchés)</span>
                </h3>
                <div class="space-y-3">
                    ${dataElements.map((de, idx) => {
            const isMatched = de.dhis2_matched;
            const uniqueId = `pivot-${sectionName.replace(/[^a-zA-Z0-9]/g, '_')}-${idx}`;
            return `
                        <div class="flex items-center gap-4 p-4 ${isMatched ? 'bg-green-50 border-2 border-green-200' : 'bg-gray-50'} rounded-lg">
                            <div class="flex-1">
                                <div class="font-semibold text-gray-900">${de.name}</div>
                                <div class="text-sm text-gray-500">Colonne: ${de.column}</div>
                            </div>
                            <div class="flex-1">
                                ${isMatched ? `
                                    <div class="p-3 bg-white rounded border-2 border-green-500">
                                        <div class="flex items-center gap-2">
                                            <i class="fas fa-check-circle text-green-600"></i>
                                            <span class="font-semibold text-green-800">${de.dhis2_name}</span>
                                        </div>
                                        <input type="hidden" 
                                               id="${uniqueId}"
                                               data-de-name="${de.name}" 
                                               data-column="${de.column}" 
                                               data-section="${sectionName}"
                                               value="${de.dhis2_id}">
                                    </div>
                                ` : `
                                    <select class="form-select w-full border-orange-500" 
                                            id="${uniqueId}"
                                            data-de-name="${de.name}" 
                                            data-column="${de.column}" 
                                            data-section="${sectionName}">
                                        <option value="">-- Sélectionner un Data Element DHIS2 --</option>
                                        ${dhis2DataElements.map(dhis2De => `
                                            <option value="${dhis2De.id}" 
                                                    data-name="${dhis2De.name}">
                                                ${dhis2De.name}
                                            </option>
                                        `).join('')}
                                    </select>
                                `}
                            </div>
                            <div class="w-24 text-center">
                                ${isMatched ?
                    '<span class="px-3 py-1 text-xs font-bold rounded-full bg-green-600 text-white">AUTO</span>' :
                    '<span class="px-3 py-1 text-xs font-bold rounded-full bg-orange-500 text-white">MANUEL</span>'
                }
                            </div>
                        </div>
                    `}).join('')}
                </div>
            `;

        container.appendChild(sectionDiv);
    }

    // Attach validate button handler
    document.getElementById('btn-validate-pivoted').onclick = validatePivotedMapping;
}

function autoMatchPivoted() {
    if (!pivotedData || !dhis2DataElements.length) {
        NotificationManager.error('Données non chargées');
        return;
    }

    let matchCount = 0;

    // Simple fuzzy matching
    document.querySelectorAll('select[id^="pivot-"]').forEach(select => {
        const deName = select.dataset.deName.toLowerCase().trim();

        // Find best match
        let bestMatch = null;
        let bestScore = 0;

        dhis2DataElements.forEach(dhis2De => {
            const dhis2Name = dhis2De.name.toLowerCase().trim();

            // Exact match
            if (dhis2Name === deName) {
                bestMatch = dhis2De;
                bestScore = 100;
            }
            // Contains match
            else if (dhis2Name.includes(deName) || deName.includes(dhis2Name)) {
                const score = Math.max(deName.length / dhis2Name.length, dhis2Name.length / deName.length) * 80;
                if (score > bestScore) {
                    bestMatch = dhis2De;
                    bestScore = score;
                }
            }
        });

        if (bestMatch && bestScore > 60) {
            select.value = bestMatch.id;
            matchCount++;
        }
    });

    NotificationManager.success(`${matchCount} correspondances automatiques trouvées`);
}

function validatePivotedMapping() {
    const mapping = [];
    let hasErrors = false;

    // Check all selects (manual mapping) and hidden inputs (auto-matched)
    document.querySelectorAll('[id^="pivot-"]').forEach(input => {
        const value = input.value;

        if (!value) {
            if (input.tagName === 'SELECT') {
                input.classList.add('border-red-500');
                hasErrors = true;
            }
        } else {
            if (input.tagName === 'SELECT') {
                input.classList.remove('border-red-500');
            }

            mapping.push({
                extracted_de: input.dataset.deName,
                column: input.dataset.column,
                section: input.dataset.section,
                dhis2_de_id: value
            });
        }
    });

    if (hasErrors) {
        NotificationManager.error('Veuillez sélectionner un Data Element DHIS2 pour chaque élément non-matché');
        return;
    }

    console.log('Pivoted mapping validated:', mapping);

    // TODO: Process the pivoted data with mapping
    LoadingOverlay.show('Traitement du format pivoté en cours...');

    // For now, just show success
    setTimeout(() => {
        LoadingOverlay.hide();
        NotificationManager.success(`Mapping validé! ${mapping.length} correspondances établies (${pivotedData.statistics.matched_with_dhis2} auto, ${mapping.length - pivotedData.statistics.matched_with_dhis2} manuels).`);
        // TODO: Call backend to transform and process pivoted data
    }, 1000);
}

// ============================================================================
// TCD MODE FUNCTIONS
// ============================================================================

let tcdDropzone = null;
let tcdAnalysisData = null;
let tcdMappingConfig = {};

// Initialize TCD Dropzone
if (document.getElementById('tcd-dropzone')) {
    tcdDropzone = new Dropzone('#tcd-dropzone', {
        url: window.CalculatorConfig.uploadUrl,
        maxFiles: 1,
        maxFilesize: 50,
        acceptedFiles: '.xlsx,.xls',
        addRemoveLinks: true,
        dictDefaultMessage: '',

        init: function () {
            this.on("success", function (file, response) {
                if (response.success) {
                    document.getElementById('tcd-filename').textContent = response.filename;
                    document.getElementById('tcd-file-info').classList.remove('hidden');
                    NotificationManager.success('Fichier TCD chargé avec succès');
                }
            });

            this.on("error", function (file, errorMessage) {
                const msg = typeof errorMessage === 'object' ? errorMessage.error : errorMessage;
                NotificationManager.error(msg);
                this.removeFile(file);
            });
        }
    });
}

// Analyze TCD File
document.getElementById('btn-analyze-tcd')?.addEventListener('click', async function () {
    LoadingOverlay.show('Analyse du fichier TCD en cours...');

    try {
        const response = await fetch('/calculator/api/tcd/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            tcdAnalysisData = data;
            populateTCDSheets(data);
            document.getElementById('tcd-config-section').classList.remove('hidden');
            NotificationManager.success(`${data.sheet_count} onglets détectés`);
        } else {
            NotificationManager.error(data.error || 'Erreur lors de l\'analyse');
        }
    } catch (error) {
        NotificationManager.error('Erreur lors de l\'analyse du fichier');
    } finally {
        LoadingOverlay.hide();
    }
});

// Populate TCD Sheets
function populateTCDSheets(data) {
    const select = document.getElementById('tcd-sheet');
    select.innerHTML = '<option value="">-- Sélectionnez un onglet --</option>';

    data.sheets.forEach(sheet => {
        const option = document.createElement('option');
        option.value = sheet;
        option.textContent = sheet;

        const analysis = data.sheets_analysis[sheet];
        if (analysis) {
            option.textContent += ` (${analysis.lignes} lignes)`;
        }

        select.appendChild(option);
    });

    select.addEventListener('change', onTCDSheetChange);
}

// On TCD Sheet Change
function onTCDSheetChange() {
    const sheetName = document.getElementById('tcd-sheet').value;

    if (!sheetName || !tcdAnalysisData) return;

    const analysis = tcdAnalysisData.sheets_analysis[sheetName];

    if (!analysis) return;

    // Show sheet info
    document.getElementById('tcd-sheet-info').textContent =
        `${analysis.lignes} lignes, ${analysis.cols_categories.length} colonnes de catégories`;

    // Populate data element column selector
    const colSelect = document.getElementById('tcd-col-de');
    colSelect.innerHTML = '<option value="">-- Sélectionnez une colonne --</option>';

    analysis.cols_categories.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        colSelect.appendChild(option);
    });
}

// TCD Org Mode Switching
document.querySelectorAll('input[name="tcd-org-mode"]').forEach(radio => {
    radio.addEventListener('change', function () {
        const fixedSection = document.getElementById('tcd-fixed-org-section');
        const orgMappingContainer = document.getElementById('tcd-org-mapping-container');

        if (this.value === 'fixed') {
            fixedSection.classList.remove('hidden');
            orgMappingContainer?.classList.add('hidden');
            loadOrganizationsForTCD();
        } else {
            fixedSection.classList.add('hidden');
            orgMappingContainer?.classList.remove('hidden');
        }
    });
});

// Load organizations for TCD fixed mode
async function loadOrganizationsForTCD() {
    const select = document.getElementById('tcd-fixed-org');

    try {
        const response = await fetch('/calculator/api/get-org-units');
        const data = await response.json();

        if (data.success) {
            select.innerHTML = '<option value="">-- Sélectionnez une organisation --</option>';

            data.org_units.forEach(org => {
                const option = document.createElement('option');
                option.value = org.id;
                option.textContent = org.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading organizations:', error);
    }
}

// Generate Mapping Suggestions
document.getElementById('btn-tcd-suggestions')?.addEventListener('click', async function () {
    const sheetName = document.getElementById('tcd-sheet').value;
    const colDE = document.getElementById('tcd-col-de').value;

    if (!sheetName || !colDE) {
        NotificationManager.error('Veuillez sélectionner un onglet et une colonne DE');
        return;
    }

    LoadingOverlay.show('Génération des suggestions...');

    try {
        const response = await fetch('/calculator/api/tcd/mapping-suggestions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sheet_name: sheetName,
                col_data_element: colDE
            })
        });

        const data = await response.json();

        if (data.success) {
            displayTCDMappingSuggestions(data.suggestions);
            document.getElementById('tcd-mapping-section').classList.remove('hidden');
            NotificationManager.success(
                `${data.mapped_de}/${data.total_de} Data Elements mappés, ${data.mapped_org}/${data.total_org} Orgs mappées`
            );
        } else {
            NotificationManager.error(data.error || 'Erreur lors de la génération des suggestions');
        }
    } catch (error) {
        NotificationManager.error('Erreur lors de la génération des suggestions');
    } finally {
        LoadingOverlay.hide();
    }
});

// Display TCD Mapping Suggestions
function displayTCDMappingSuggestions(suggestions) {
    const orgMode = document.querySelector('input[name="tcd-org-mode"]:checked').value;

    // Data Elements Mapping
    const deList = document.getElementById('tcd-de-mapping-list');
    deList.innerHTML = '';

    Object.entries(suggestions.data_elements || {}).forEach(([valTCD, info]) => {
        const div = document.createElement('div');
        div.className = 'bg-white border border-gray-200 rounded-lg p-4';

        const confidence = info.confidence === 'high' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700';

        div.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <div class="font-bold text-gray-900">${valTCD}</div>
                    <span class="text-xs ${confidence} px-2 py-0.5 rounded-full font-semibold">${info.confidence}</span>
                </div>
                <div class="text-sm text-gray-600">→ ${info.suggested}</div>
                <input type="hidden" class="tcd-de-mapping" data-tcd-value="${valTCD}" value="${info.suggested}">
            `;

        deList.appendChild(div);
    });

    // Organizations Mapping (only if not fixed mode)
    if (orgMode !== 'fixed') {
        const orgList = document.getElementById('tcd-org-mapping-list');
        orgList.innerHTML = '';

        Object.entries(suggestions.etablissements || {}).forEach(([valTCD, info]) => {
            const div = document.createElement('div');
            div.className = 'bg-white border border-gray-200 rounded-lg p-4';

            const confidence = info.confidence === 'high' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700';

            div.innerHTML = `
                    <div class="flex items-center justify-between mb-2">
                        <div class="font-bold text-gray-900">${valTCD}</div>
                        <span class="text-xs ${confidence} px-2 py-0.5 rounded-full font-semibold">${info.match_type}: ${info.confidence}</span>
                    </div>
                    <div class="text-sm text-gray-600">→ ${info.suggested}</div>
                    <input type="hidden" class="tcd-org-mapping" data-tcd-value="${valTCD}" value="${info.suggested}">
                `;

            orgList.appendChild(div);
        });
    }
}

// Process TCD
document.getElementById('btn-tcd-process')?.addEventListener('click', async function () {
    const sheetName = document.getElementById('tcd-sheet').value;
    const colDE = document.getElementById('tcd-col-de').value;
    const period = document.getElementById('tcd-period').value;
    const orgMode = document.querySelector('input[name="tcd-org-mode"]:checked').value;
    const fixedOrg = document.getElementById('tcd-fixed-org').value;

    if (!sheetName || !colDE || !period) {
        NotificationManager.error('Veuillez remplir tous les champs requis');
        return;
    }

    if (orgMode === 'fixed' && !fixedOrg) {
        NotificationManager.error('Veuillez sélectionner une organisation fixe');
        return;
    }

    // Build mapping config
    const mappingConfig = {
        data_elements: {},
        etablissements: {}
    };

    // Collect DE mappings
    document.querySelectorAll('.tcd-de-mapping').forEach(input => {
        const tcdValue = input.dataset.tcdValue;
        const dhis2Value = input.value;
        if (!mappingConfig.data_elements[sheetName]) {
            mappingConfig.data_elements[sheetName] = {};
        }
        mappingConfig.data_elements[sheetName][tcdValue] = ['', dhis2Value];  // [section, de_name]
    });

    // Collect Org mappings
    if (orgMode !== 'fixed') {
        document.querySelectorAll('.tcd-org-mapping').forEach(input => {
            const tcdValue = input.dataset.tcdValue;
            const dhis2Value = input.value;
            mappingConfig.etablissements[tcdValue] = dhis2Value;
        });
    }

    LoadingOverlay.show('Traitement du fichier TCD en cours...');

    try {
        const response = await fetch('/calculator/api/tcd/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sheet_name: sheetName,
                col_data_element: colDE,
                period: period,
                org_mode: orgMode,
                fixed_org_unit: orgMode === 'fixed' ? fixedOrg : null,
                mapping_config: mappingConfig
            })
        });

        const data = await response.json();

        if (data.success) {
            displayTCDReport(data);
            document.getElementById('results-section').classList.remove('hidden');
            document.getElementById('download-section').classList.remove('hidden');
            setStep(2, 'completed');
            NotificationManager.success(`${data.total_values} valeurs générées avec succès`);
        } else {
            NotificationManager.error(data.error || 'Erreur lors du traitement');
            if (data.stats) {
                displayTCDReport(data);
            }
        }
    } catch (error) {
        NotificationManager.error('Erreur lors du traitement du fichier');
    } finally {
        LoadingOverlay.hide();
    }
});

// Display TCD Report
function displayTCDReport(data) {
    const stats = data.stats;

    // Update stats
    document.getElementById('tcd-stat-lignes').textContent = stats.lignes_traitees || 0;
    document.getElementById('tcd-stat-valeurs').textContent = stats.valeurs_inserees || 0;
    document.getElementById('tcd-stat-org-nm').textContent = Object.keys(stats.etablissements_non_mappes || {}).length;
    document.getElementById('tcd-stat-de-nm').textContent = Object.keys(stats.data_elements_non_mappes || {}).length;

    // Show report section
    document.getElementById('tcd-report-section').classList.remove('hidden');

    // Show errors if any
    const hasErrors = Object.keys(stats.etablissements_non_mappes || {}).length > 0 ||
        Object.keys(stats.data_elements_non_mappes || {}).length > 0;

    if (hasErrors) {
        document.getElementById('tcd-errors-container').classList.remove('hidden');

        // Unmapped Orgs
        if (Object.keys(stats.etablissements_non_mappes || {}).length > 0) {
            document.getElementById('tcd-unmapped-orgs').classList.remove('hidden');
            const orgList = document.getElementById('tcd-unmapped-orgs-list');
            orgList.innerHTML = '';

            Object.entries(stats.etablissements_non_mappes).forEach(([org, count]) => {
                const div = document.createElement('div');
                div.textContent = `${org}: ${count} étudiants`;
                orgList.appendChild(div);
            });
        }

        // Unmapped DEs
        if (Object.keys(stats.data_elements_non_mappes || {}).length > 0) {
            document.getElementById('tcd-unmapped-des').classList.remove('hidden');
            const deList = document.getElementById('tcd-unmapped-des-list');
            deList.innerHTML = '';

            Object.entries(stats.data_elements_non_mappes).forEach(([de, count]) => {
                const div = document.createElement('div');
                div.textContent = `${de}: ${count} étudiants`;
                deList.appendChild(div);
            });
        }
    }

    // Update results section stats (reuse existing)
    if (data.total_values) {
        document.getElementById('stat-total').textContent = data.total_values;
        document.getElementById('stat-valid').textContent = stats.valeurs_inserees;
        document.getElementById('stat-errors').textContent = stats.lignes_traitees - stats.valeurs_inserees;

        document.getElementById('json-info').textContent =
            `Fichier: ${data.json_filename} (${data.total_values} valeurs)`;
    }
}

// =============================================================================
// MODE AUTOMATIQUE - JavaScript
// =============================================================================

let autoTemplateFile = null;
let autoTCDAnalysis = null;
let autoTCDDropzone = null;
let autoTemplateOrgs = [];
let autoTCDEtablissements = [];
let autoTemplateSectionsDE = {};
let autoTCDValeursDE = [];
let autoTemplateOrgsCodes = {};  // {nom: code}
let autoTCDEtabsCodes = {};  // {nom: code}

// Upload Template
document.getElementById('auto-template-input')?.addEventListener('change', async function (e) {
    const file = e.target.files[0];
    if (!file) return;

    // Upload le template au serveur
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/calculator/api/upload-template', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            autoTemplateFile = result.filepath;
            autoTemplateOrgs = result.organisations_uniques || [];
            autoTemplateOrgsCodes = result.organisations_avec_codes || {};
            autoTemplateSectionsDE = result.sections_de || {};

            // Afficher les infos du template
            document.getElementById('auto-template-info').classList.remove('hidden');
            document.getElementById('auto-template-filename').textContent = file.name;
            document.getElementById('auto-template-rows').textContent = result.rows || '...';
            document.getElementById('auto-template-orgs').textContent = result.orgs || '...';

            // Afficher étape 2
            document.getElementById('auto-step2').classList.remove('hidden');

            // Initialiser le Dropzone TCD
            initializeAutoTCDDropzone();

            NotificationManager.success('Template chargé avec succès');
        } else {
            NotificationManager.error(result.error || 'Erreur lors du chargement du template');
        }
    } catch (error) {
        console.error('Erreur upload template:', error);
        NotificationManager.error('Erreur lors du chargement du template');
    }
});

// Initialiser Dropzone TCD
function initializeAutoTCDDropzone() {
    if (autoTCDDropzone) {
        autoTCDDropzone.destroy();
    }

    Dropzone.autoDiscover = false;

    autoTCDDropzone = new Dropzone("#auto-tcd-dropzone", {
        url: window.CalculatorConfig.uploadUrl,
        maxFiles: 1,
        maxFilesize: 50,
        acceptedFiles: '.xlsx,.xls',
        addRemoveLinks: true,
        dictDefaultMessage: '',
        init: function () {
            this.on("success", async function (file, response) {
                console.log('[Auto] TCD uploadé:', response);

                // Analyser le TCD
                try {
                    const analyzeResponse = await fetch('/calculator/api/auto/analyze-tcd', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });

                    const data = await analyzeResponse.json();

                    if (data.success) {
                        autoTCDAnalysis = data;
                        autoTCDEtablissements = data.etablissements_uniques || [];
                        autoTCDEtabsCodes = data.etablissements_avec_codes || {};
                        autoTCDValeursDE = data.valeurs_de_uniques || [];

                        // Afficher info fichier
                        document.getElementById('auto-tcd-info').classList.remove('hidden');
                        document.getElementById('auto-tcd-filename').textContent = response.filename;
                        document.getElementById('auto-tcd-sheets').textContent = data.sheet_count;

                        // Remplir le select des onglets
                        const sheetSelect = document.getElementById('auto-sheet-select');
                        sheetSelect.innerHTML = '<option value="">-- Sélectionnez un onglet --</option>';
                        data.sheets.forEach(sheet => {
                            const option = document.createElement('option');
                            option.value = sheet.name;
                            option.textContent = `${sheet.name} (${sheet.rows} lignes)`;
                            sheetSelect.appendChild(option);
                        });

                        // Afficher étape 3
                        document.getElementById('auto-step3').classList.remove('hidden');

                        NotificationManager.success(`TCD analysé: ${data.sheet_count} onglets trouvés`);
                    } else {
                        NotificationManager.error('Erreur analyse TCD: ' + data.error);
                    }
                } catch (error) {
                    console.error('[Auto] Erreur analyse:', error);
                    NotificationManager.error('Erreur lors de l\'analyse du TCD');
                }
            });

            this.on("error", function (file, message) {
                console.error('[Auto] Erreur upload TCD:', message);
                NotificationManager.error('Erreur upload: ' + (message.error || message));
            });
        }
    });
}

// Changement d'onglet
document.getElementById('auto-sheet-select')?.addEventListener('change', function () {
    const sheetName = this.value;
    if (!sheetName || !autoTCDAnalysis) return;

    const sheet = autoTCDAnalysis.sheets.find(s => s.name === sheetName);
    if (!sheet) return;

    // Afficher info onglet
    document.getElementById('auto-sheet-info').textContent =
        `${sheet.rows} lignes détectées`;

    // Helper to create options
    const createOptions = (selectedVal = '') => {
        let opts = '<option value="">-- Sélectionner --</option>';
        sheet.columns.forEach(col => {
            const selected = col === selectedVal ? 'selected' : '';
            opts += `<option value="${col}" ${selected}>${col}</option>`;
        });
        return opts;
    };

    // Remplir select colonnes data element
    const colSelect = document.getElementById('auto-col-de');
    colSelect.innerHTML = '<option value="">-- Sélectionnez la colonne --</option>';
    sheet.columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        colSelect.appendChild(option);
    });

    // Remplir select colonne code établissement
    const colCodeSelect = document.getElementById('auto-col-code-etab');
    colCodeSelect.innerHTML = '<option value="">-- Aucun (pas de mapping auto) --</option>';
    sheet.columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        // Auto-sélectionner si c'est une colonne qui ressemble à un code
        if (col.toLowerCase().includes('code') && col.toLowerCase().includes('et')) {
            option.selected = true;
        }
        colCodeSelect.appendChild(option);
    });

    // --- GESTION DES COLONNES DE CATEGORIES ---
    const catContainer = document.getElementById('auto-cat-cols-container');
    catContainer.innerHTML = ''; // Start fresh

    // Fonction pour ajouter une colonne
    window.addAutoCategoryColumn = function (selectedValue = '') {
        const div = document.createElement('div');
        div.className = 'flex gap-2 items-center';
        div.innerHTML = `
                <select class="form-input auto-cat-col-select flex-1">
                    ${createOptions(selectedValue)}
                </select>
                <button type="button" class="btn btn-sm btn-ghost text-red-500 hover:bg-red-50" onclick="this.parentElement.remove()">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        catContainer.appendChild(div);
    };

    // Essayer de détecter Sexe et Age automatiquement
    let autoAdded = false;
    sheet.columns.forEach(col => {
        const lower = col.toLowerCase();
        if (lower.includes('sex') || lower.includes('genre') || lower.includes('age') || lower.includes('tranche')) {
            window.addAutoCategoryColumn(col);
            autoAdded = true;
        }
    });

    // Si rien détecté, ajouter 2 vides par défaut (cas standard Age+Sexe)
    if (!autoAdded) {
        window.addAutoCategoryColumn();
        window.addAutoCategoryColumn();
    }

    // Cacher l'étape 4 en attendant la sélection de la colonne
    document.getElementById('auto-step4').classList.add('hidden');
});

// Add button listener
document.getElementById('btn-add-cat-col')?.addEventListener('click', () => {
    if (window.addAutoCategoryColumn) window.addAutoCategoryColumn();
});

// Changement de colonne data element
document.getElementById('auto-col-de')?.addEventListener('change', async function () {
    const colName = this.value;
    const sheetName = document.getElementById('auto-sheet-select').value;
    const colCode = document.getElementById('auto-col-code-etab').value;

    if (!colName || !sheetName) return;

    try {
        // Extraire les valeurs uniques de cette colonne
        const response = await fetch('/calculator/api/auto/extract-tcd-values', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sheet_name: sheetName,
                column_name: colName,
                column_code: colCode
            })
        });

        const data = await response.json();

        if (data.success) {
            autoTCDValeursDE = data.valeurs || [];
            autoTCDEtablissements = data.etablissements_uniques || [];
            autoTCDEtabsCodes = data.etablissements_avec_codes || {};

            console.log('Établissements TCD:', autoTCDEtablissements.length);
            console.log('Codes TCD:', Object.keys(autoTCDEtabsCodes).length);
            console.log('Codes Template:', Object.keys(autoTemplateOrgsCodes).length);

            // Afficher étape 4
            document.getElementById('auto-step4').classList.remove('hidden');

            // Initialiser les mappings maintenant que nous avons toutes les données
            setTimeout(async () => {
                // Effacer les conteneurs
                document.getElementById('auto-org-mappings').innerHTML = '';
                document.getElementById('auto-de-mappings').innerHTML = '';

                // Faire le mapping automatique des établissements par code
                autoMapOrganisationsByCode();

                // Ajouter un mapping vide pour les autres
                addAutoOrgMapping();

                // --- CHARGER SUGGESTIONS INTELLIGENTES ---
                let suggestions = {};
                try {
                    LoadingOverlay.show('Recherche de correspondances intelligentes...');
                    const sugResp = await fetch('/calculator/api/tcd/mapping-suggestions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            sheet_name: sheetName,
                            col_data_element: colName
                        })
                    });
                    const sugData = await sugResp.json();
                    if (sugData.success && sugData.suggestions && sugData.suggestions.data_elements) {
                        suggestions = sugData.suggestions.data_elements;

                        // Afficher un petit toast récapitulatif
                        const count = Object.keys(suggestions).length;
                        if (count > 0) {
                            NotificationManager.success(`${count} suggestions trouvées automatiquement`);
                        }
                    }
                } catch (e) {
                    console.warn("Erreur suggestions:", e);
                } finally {
                    LoadingOverlay.hide();
                }

                // Remplir les Data Elements avec suggestions
                // On itère sur toutes les valeurs uniques trouvées
                autoTCDValeursDE.forEach(val => {
                    if (suggestions[val]) {
                        // Si suggestion trouvée, on pré-remplit
                        const s = suggestions[val];
                        addAutoDEMapping(val, s.suggested_section, s.suggested_name);
                    } else {
                        // Sinon vide
                        addAutoDEMapping(val);
                    }
                });

            }, 100);
        } else {
            NotificationManager.error('Erreur extraction valeurs: ' + data.error);
        }
    } catch (error) {
        console.error('Erreur extraction valeurs:', error);
        NotificationManager.error('Erreur lors de l\'extraction des valeurs');
    }
});

// Fonction de mapping automatique par code
function autoMapOrganisationsByCode() {
    // Inverser le dictionnaire template pour chercher par code
    const templateCodeToName = {};
    for (const [nom, code] of Object.entries(autoTemplateOrgsCodes)) {
        templateCodeToName[code] = nom;
    }

    let mappedCount = 0;
    let unmappedTCD = [];

    // Pour chaque établissement TCD
    for (const [nomTCD, codeTCD] of Object.entries(autoTCDEtabsCodes)) {
        // Chercher le matching dans le template par code
        if (codeTCD && templateCodeToName[codeTCD]) {
            // Mapping trouvé automatiquement
            const nomTemplate = templateCodeToName[codeTCD];
            addAutoOrgMapping(nomTCD, nomTemplate);
            mappedCount++;
        } else {
            // Pas de mapping automatique trouvé
            unmappedTCD.push(nomTCD);
        }
    }

    // Afficher un message sur les mappings automatiques
    if (mappedCount > 0) {
        NotificationManager.success(`${mappedCount} établissement(s) mappé(s) automatiquement par code`);
    }

    if (unmappedTCD.length > 0) {
        NotificationManager.warning(`${unmappedTCD.length} établissement(s) nécessitent un mapping manuel`);
    }
}

// Ajouter mapping organisation
function addAutoOrgMapping(acronyme = '', pattern = '') {
    const container = document.getElementById('auto-org-mappings');
    const div = document.createElement('div');
    div.className = 'grid grid-cols-[1fr_1fr_auto] gap-4 items-center';

    // Créer les options pour les selects
    let tcdOptions = '<option value="">-- Établissement TCD --</option>';
    autoTCDEtablissements.forEach(etab => {
        const selected = etab === acronyme ? 'selected' : '';
        tcdOptions += `<option value="${etab}" ${selected}>${etab}</option>`;
    });

    let templateOptions = '<option value="">-- Organisation Template --</option>';
    autoTemplateOrgs.forEach(org => {
        const selected = org === pattern ? 'selected' : '';
        templateOptions += `<option value="${org}" ${selected}>${org}</option>`;
    });

    div.innerHTML = `
            <select class="form-input auto-org-acronyme">${tcdOptions}</select>
            <select class="form-input auto-org-pattern">${templateOptions}</select>
            <button type="button" class="btn btn-sm bg-red-500 text-white hover:bg-red-600" onclick="this.parentElement.remove()">
                <i class="fas fa-trash"></i>
            </button>
        `;
    container.appendChild(div);
}

// Ajouter mapping data element
function addAutoDEMapping(valeur = '', section = '', de = '') {
    const container = document.getElementById('auto-de-mappings');
    const div = document.createElement('div');
    div.className = 'grid grid-cols-[1fr_1fr_1fr_auto] gap-4 items-center';

    // Créer les options pour valeur TCD
    let valeurOptions = '<option value="">-- Valeur TCD --</option>';
    autoTCDValeursDE.forEach(val => {
        const selected = val === valeur ? 'selected' : '';
        valeurOptions += `<option value="${val}" ${selected}>${val}</option>`;
    });

    // Créer les options pour sections
    let sectionOptions = '<option value="">-- Section --</option>';
    Object.keys(autoTemplateSectionsDE).forEach(sec => {
        const selected = sec === section ? 'selected' : '';
        sectionOptions += `<option value="${sec}" ${selected}>${sec}</option>`;
    });

    // Créer le select DE (vide au départ, rempli quand section choisie)
    let deOptions = '<option value="">-- Data Element --</option>';
    if (section && autoTemplateSectionsDE[section]) {
        autoTemplateSectionsDE[section].forEach(dataElem => {
            const selected = dataElem === de ? 'selected' : '';
            deOptions += `<option value="${dataElem}" ${selected}>${dataElem}</option>`;
        });
    }

    div.innerHTML = `
            <select class="form-input auto-de-valeur">${valeurOptions}</select>
            <select class="form-input auto-de-section">${sectionOptions}</select>
            <select class="form-input auto-de-name">${deOptions}</select>
            <button type="button" class="btn btn-sm bg-red-500 text-white hover:bg-red-600" onclick="this.parentElement.remove()">
                <i class="fas fa-trash"></i>
            </button>
        `;
    container.appendChild(div);

    // Ajouter l'événement pour filtrer les DE quand section change
    const sectionSelect = div.querySelector('.auto-de-section');
    const deSelect = div.querySelector('.auto-de-name');

    sectionSelect.addEventListener('change', function () {
        const selectedSection = this.value;
        deSelect.innerHTML = '<option value="">-- Data Element --</option>';

        if (selectedSection && autoTemplateSectionsDE[selectedSection]) {
            autoTemplateSectionsDE[selectedSection].forEach(dataElem => {
                const option = document.createElement('option');
                option.value = dataElem;
                option.textContent = dataElem;
                deSelect.appendChild(option);
            });
        }
    });
}

// Traiter
async function processAuto() {
    const sheetName = document.getElementById('auto-sheet-select').value;
    const colDE = document.getElementById('auto-col-de').value;
    const period = document.getElementById('auto-period').value;

    if (!autoTemplateFile || !sheetName || !colDE || !period) {
        NotificationManager.error('Veuillez remplir tous les champs requis');
        return;
    }

    // Récupérer les colonnes de catégories
    const category_cols = [];
    document.querySelectorAll('.auto-cat-col-select').forEach(sel => {
        if (sel.value) category_cols.push(sel.value);
    });

    if (category_cols.length === 0) {
        NotificationManager.error('Veuillez sélectionner au moins une colonne de catégorie (ex: Sexe)');
        return;
    }

    // Récupérer les mappings
    const etablissements_patterns = {};
    document.querySelectorAll('#auto-org-mappings > div').forEach(div => {
        const acronyme = div.querySelector('.auto-org-acronyme').value.trim();
        const pattern = div.querySelector('.auto-org-pattern').value.trim();
        if (acronyme && pattern) {
            etablissements_patterns[acronyme] = pattern;
        }
    });

    const data_elements_manuels = {};
    document.querySelectorAll('#auto-de-mappings > div').forEach(div => {
        const valeur = div.querySelector('.auto-de-valeur').value.trim();
        const section = div.querySelector('.auto-de-section').value.trim();
        const deName = div.querySelector('.auto-de-name').value.trim();
        if (valeur && section && deName) {
            data_elements_manuels[valeur] = [section, deName];
        }
    });

    if (Object.keys(etablissements_patterns).length === 0) {
        NotificationManager.error('Veuillez ajouter au moins un mapping établissement');
        return;
    }

    if (Object.keys(data_elements_manuels).length === 0) {
        NotificationManager.error('Veuillez ajouter au moins un mapping data element');
        return;
    }

    LoadingOverlay.show('Traitement en cours...');

    try {
        const response = await fetch('/calculator/api/auto/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tcd_sheet: sheetName,
                col_data_element: colDE,
                period: period,
                period: period,
                config: {
                    etablissements_patterns: etablissements_patterns,
                    data_elements_manuels: data_elements_manuels,
                    category_cols: category_cols
                }
            })
        });

        const data = await response.json();

        LoadingOverlay.hide();

        if (data.success) {
            // Afficher le rapport
            displayAutoReport(data);

            // Afficher étape 5
            document.getElementById('auto-step5').classList.remove('hidden');

            // Afficher la section download avec boutons d'action
            document.getElementById('download-section').classList.remove('hidden');
            document.getElementById('json-info').textContent =
                `Fichier: ${data.json_filename} (${data.total_values} valeurs)`;

            // Scroller vers le rapport
            document.getElementById('auto-step5').scrollIntoView({ behavior: 'smooth' });

            NotificationManager.success(`Traitement terminé: ${data.total_values} valeurs générées`);
        } else {
            NotificationManager.error('Erreur: ' + data.error);
            if (data.stats) {
                displayAutoReport(data);
                document.getElementById('auto-step5').classList.remove('hidden');
            }
        }
    } catch (error) {
        LoadingOverlay.hide();
        console.error('[Auto] Erreur traitement:', error);
        NotificationManager.error('Erreur lors du traitement');
    }
}

// Afficher rapport
function displayAutoReport(data) {
    const stats = data.stats;

    // Statistiques
    document.getElementById('auto-stat-lignes').textContent = stats.lignes_traitees || 0;
    document.getElementById('auto-stat-valeurs').textContent = stats.valeurs_inserees || 0;
    document.getElementById('auto-stat-org-nm').textContent = Object.keys(stats.etablissements_non_mappes || {}).length;
    document.getElementById('auto-stat-de-nm').textContent = Object.keys(stats.data_elements_non_mappes || {}).length;

    // Erreurs
    const hasErrors = (stats.etablissements_non_mappes && Object.keys(stats.etablissements_non_mappes).length > 0) ||
        (stats.data_elements_non_mappes && Object.keys(stats.data_elements_non_mappes).length > 0) ||
        (stats.combinaisons_non_trouvees && stats.combinaisons_non_trouvees.length > 0);

    if (hasErrors) {
        document.getElementById('auto-errors-container').classList.remove('hidden');

        // Orgs non mappées
        if (stats.etablissements_non_mappes && Object.keys(stats.etablissements_non_mappes).length > 0) {
            document.getElementById('auto-unmapped-orgs').classList.remove('hidden');
            const list = document.getElementById('auto-unmapped-orgs-list');
            list.innerHTML = '';
            for (const [org, count] of Object.entries(stats.etablissements_non_mappes)) {
                const p = document.createElement('p');
                p.textContent = `${org} (${count} valeurs perdues)`;
                list.appendChild(p);
            }
        }

        // DEs non mappés
        if (stats.data_elements_non_mappes && Object.keys(stats.data_elements_non_mappes).length > 0) {
            document.getElementById('auto-unmapped-des').classList.remove('hidden');
            const list = document.getElementById('auto-unmapped-des-list');
            list.innerHTML = '';
            for (const [de, count] of Object.entries(stats.data_elements_non_mappes)) {
                const p = document.createElement('p');
                p.textContent = `${de} (${count} valeurs perdues)`;
                list.appendChild(p);
            }
        }

        // Combinaisons non trouvées
        if (stats.combinaisons_non_trouvees && stats.combinaisons_non_trouvees.length > 0) {
            document.getElementById('auto-not-found').classList.remove('hidden');
            const list = document.getElementById('auto-not-found-list');
            list.innerHTML = '';
            stats.combinaisons_non_trouvees.forEach(item => {
                const div = document.createElement('div');
                div.className = 'bg-red-50 p-2 rounded border border-red-100 mb-2 text-xs';

                if (item.details) {
                    div.innerHTML = `
                            <div class="font-bold text-red-800 mb-1">
                                <i class="fas fa-times-circle mr-1"></i>
                                Combinaison Introuvable (Valeur: ${item.valeur})
                            </div>
                            <div class="grid grid-cols-2 gap-x-4 gap-y-1">
                                <div><span class="font-semibold">Organisation:</span> ${item.details.organisation}</div>
                                <div><span class="font-semibold">Data Element:</span> ${item.details.data_element}</div>
                                <div class="col-span-2 text-red-700 font-bold border-t border-red-200 mt-1 pt-1">
                                    <span class="font-semibold">Problème Catégorie:</span> "${item.details.coc_norm}" n'existe pas pour cet élément.
                                </div>
                            </div>
                        `;
                } else {
                    // Fallback pour compatibilité
                    div.textContent = `${item.cle} (valeur: ${item.valeur})`;
                }
                list.appendChild(div);
            });
        }
    }

    // Preview
    if (data.preview && data.preview.length > 0) {
        const tbody = document.getElementById('auto-preview-tbody');
        tbody.innerHTML = '';
        data.preview.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                    <td class="px-4 py-3 text-sm">${row.dataElement}</td>
                    <td class="px-4 py-3 text-sm">${row.orgUnit}</td>
                    <td class="px-4 py-3 text-sm">${row.categoryOptionCombo}</td>
                    <td class="px-4 py-3 text-sm">${row.period}</td>
                    <td class="px-4 py-3 text-sm font-bold">${row.value}</td>
                `;
            tbody.appendChild(tr);
        });
    }
}
