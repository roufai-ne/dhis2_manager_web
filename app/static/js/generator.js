// app/static/js/generator.js

let selectedDataset = null;
let selectedOrgUnits = [];

document.addEventListener('DOMContentLoaded', function () {
    loadOrgTree();
    loadFilters();

    // Dataset Search
    document.getElementById('dataset-search').addEventListener('input', function (e) {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.dataset-card').forEach(card => {
            const name = card.dataset.name;
            if (name.includes(term)) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
    });

    document.querySelectorAll('.dataset-card').forEach(card => {
        card.addEventListener('click', function () { selectDataset(this); });
    });

    // Tree Controls
    document.getElementById('btn-select-all').addEventListener('click', () => $('#org-tree').jstree('check_all'));
    document.getElementById('btn-deselect-all').addEventListener('click', () => $('#org-tree').jstree('uncheck_all'));
    document.getElementById('btn-expand-all').addEventListener('click', () => $('#org-tree').jstree('open_all'));
    document.getElementById('btn-collapse-all').addEventListener('click', () => $('#org-tree').jstree('close_all'));

    // Filter Controls
    document.getElementById('btn-select-group').addEventListener('click', selectByGroup);
    document.getElementById('btn-deselect-group').addEventListener('click', deselectByGroup);
    document.getElementById('btn-select-level').addEventListener('click', selectByLevel);
    document.getElementById('btn-deselect-level').addEventListener('click', deselectByLevel);

    document.getElementById('org-group-select').addEventListener('change', function () {
        document.getElementById('btn-select-group').disabled = !this.value;
        document.getElementById('btn-deselect-group').disabled = !this.value;
    });
    document.getElementById('org-level-select').addEventListener('change', function () {
        document.getElementById('btn-select-level').disabled = !this.value;
        document.getElementById('btn-deselect-level').disabled = !this.value;
    });

    document.getElementById('btn-generate').addEventListener('click', generateTemplate);
    document.getElementById('btn-generate-csv-names').addEventListener('click', generateCsvNames);
    document.getElementById('period-input').addEventListener('change', validateForm);
});

function loadFilters() {
    // Load Groups
    fetch(window.GeneratorConfig.urls.orgUnitGroups)
        .then(r => r.json())
        .then(groups => {
            const select = document.getElementById('org-group-select');
            select.innerHTML = '<option value="">Choisir un groupe...</option>';
            groups.forEach(g => {
                select.innerHTML += `<option value="${g.id}">${g.name}</option>`;
            });
        })
        .catch(e => console.error('Erreur groupes:', e));

    // Load Levels
    fetch(window.GeneratorConfig.urls.orgUnitLevels)
        .then(r => r.json())
        .then(levels => {
            const select = document.getElementById('org-level-select');
            select.innerHTML = '<option value="">Choisir un niveau...</option>';
            levels.forEach(l => {
                select.innerHTML += `<option value="${l.level}">${l.name} (Niveau ${l.level})</option>`;
            });
        })
        .catch(e => console.error('Erreur niveaux:', e));
}

function filterIdsByScope(instance, ids) {
    const selectedNodes = instance.get_selected(true);
    if (selectedNodes.length === 0) return ids;

    const allowedIds = new Set();
    selectedNodes.forEach(node => {
        allowedIds.add(node.id);
        if (node.children_d) {
            node.children_d.forEach(childId => allowedIds.add(childId));
        }
    });

    const originalCount = ids.length;
    const filtered = ids.filter(id => allowedIds.has(id));

    if (filtered.length < originalCount) {
        NotificationManager.info(`Filtre appliqué à la sélection existante (${filtered.length}/${originalCount})`);
    }

    return filtered;
}

function selectByGroup() {
    const groupId = document.getElementById('org-group-select').value;
    if (!groupId) return;

    LoadingOverlay.show('Sélection du groupe...');
    const url = window.GeneratorConfig.urls.orgUnitsByGroup.replace('GROUP_ID_PLACEHOLDER', groupId);
    fetch(url)
        .then(r => r.json())
        .then(data => {
            const instance = $('#org-tree').jstree(true);
            const idsToSelect = filterIdsByScope(instance, data.ids);
            instance.check_node(idsToSelect);
            revealSelected(idsToSelect);
            NotificationManager.success(`${idsToSelect.length} unités sélectionnées`);
        })
        .catch(e => NotificationManager.error('Erreur de sélection'))
        .finally(() => LoadingOverlay.hide());
}

function selectByLevel() {
    const level = document.getElementById('org-level-select').value;
    if (!level) return;

    LoadingOverlay.show('Sélection du niveau...');
    const url = window.GeneratorConfig.urls.orgUnitsByLevel.replace('LEVEL_PLACEHOLDER', level);
    fetch(url)
        .then(r => r.json())
        .then(data => {
            const instance = $('#org-tree').jstree(true);
            const idsToSelect = filterIdsByScope(instance, data.ids);
            instance.check_node(idsToSelect);
            revealSelected(idsToSelect);
            NotificationManager.success(`${idsToSelect.length} unités sélectionnées`);
        })
        .catch(e => NotificationManager.error('Erreur de sélection'))
        .finally(() => LoadingOverlay.hide());
}

function revealSelected(ids) {
    const instance = $('#org-tree').jstree(true);
    let parentsToOpen = new Set();

    ids.forEach(id => {
        let parent = instance.get_parent(id);
        while (parent && parent !== '#') {
            parentsToOpen.add(parent);
            parent = instance.get_parent(parent);
        }
    });

    if (parentsToOpen.size > 0) {
        instance.open_node(Array.from(parentsToOpen));
    }
}

function loadOrgTree() {
    fetch(window.GeneratorConfig.urls.orgTree)
        .then(r => r.json())
        .then(data => {
            $('#org-tree').jstree({
                'core': {
                    'data': data,
                    'themes': {
                        'name': 'default',
                        'responsive': true
                    }
                },
                'checkbox': { 'keep_selected_style': false, 'three_state': false },
                'plugins': ['checkbox', 'search', 'types', 'contextmenu'],
                'contextmenu': {
                    'items': function (node) {
                        return {
                            'select_children': {
                                'label': 'Sélectionner les enfants',
                                'action': function (data) {
                                    var inst = $.jstree.reference(data.reference);
                                    var obj = inst.get_node(data.reference);
                                    inst.check_node(obj);
                                    inst.check_node(obj.children_d);
                                }
                            },
                            'deselect_children': {
                                'label': 'Désélectionner les enfants',
                                'action': function (data) {
                                    var inst = $.jstree.reference(data.reference);
                                    var obj = inst.get_node(data.reference);
                                    inst.uncheck_node(obj);
                                    inst.uncheck_node(obj.children_d);
                                }
                            }
                        };
                    }
                }
            }).on('changed.jstree', function (e, data) {
                selectedOrgUnits = data.selected;
                document.getElementById('selected-count').textContent = selectedOrgUnits.length;
                validateForm();
            });
        })
        .catch(e => console.error('Erreur:', e));
}

function selectDataset(card) {
    document.querySelectorAll('.dataset-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');

    selectedDataset = {
        id: card.dataset.id,
        periodType: card.dataset.periodType,
        name: card.dataset.name // Captured for filename
    };
    document.getElementById('period-type-display').value = selectedDataset.periodType;

    const url = window.GeneratorConfig.urls.datasetInfo.replace('DATASET_ID_PLACEHOLDER', selectedDataset.id);
    fetch(url)
        .then(r => r.json())
        .then(info => {
            let html = `<p class="mb-1"><strong>${info.num_elements}</strong> éléments de données</p>`;
            if (info.categories && info.categories.length > 0) {
                html += `<p class="text-gray-600">Catégories: ${info.categories.join(', ')}</p>`;
            }
            document.getElementById('dataset-details').innerHTML = html;
            document.getElementById('dataset-info').classList.remove('hidden');
        });

    const periodUrl = window.GeneratorConfig.urls.periodExamples.replace('PERIOD_TYPE_PLACEHOLDER', selectedDataset.periodType);
    fetch(periodUrl)
        .then(r => r.json())
        .then(data => {
            // Keep the hint for reference but rely on dropdown
            // document.getElementById('period-hint').innerHTML = ...
        });

    updatePeriodOptions(selectedDataset.periodType);
    validateForm();
}

function updatePeriodOptions(periodType) {
    const select = document.getElementById('period-input');
    select.innerHTML = '<option value="">-- Sélectionner une période --</option>';
    select.disabled = false;

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
            // Capitalize first letter
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
            // S1: Jan-Jun
            options.push({ value: `${y}S1`, label: `${y} - Semestre 1 (Jan-Juin)`, sort: parseInt(`${y}1`) });
            // S2: Jul-Dec
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
        // Fallback for others (Weekly, etc - just give recent years as base or generic)
        select.innerHTML = '<option value="">Type de période non géré automatiquement</option>';
        // Ideally revert to text input here, but for now just show years
        for (let y = currentYear - 5; y <= currentYear + 2; y++) {
            options.push({ value: `${y}`, label: `${y}`, sort: y });
        }
    }

    // Sort descending (newest first)
    options.sort((a, b) => b.sort - a.sort);

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        select.appendChild(option);
    });
}

function validateForm() {
    const isValid = selectedDataset && selectedOrgUnits.length > 0 && document.getElementById('period-input').value.trim();
    document.getElementById('btn-generate').disabled = !isValid;
    document.getElementById('btn-generate-csv-names').disabled = !isValid;
}

function formatDatasetName(text) {
    if (!text) return 'Dataset';
    // Remove common generic words but keep the rest readable
    let clean = text.replace(/Données|Data|Formulaire|Rapport|Mensuel|Trimestriel|Annuel/gi, '');
    clean = clean.replace(/[^a-zA-Z0-9 ]/g, '');
    clean = clean.trim();
    // Replace spaces with underscores, limit length but don't acronymize
    return clean.replace(/\s+/g, '_').substring(0, 40);
}

function formatOUName(text) {
    if (!text) return 'OrgUnit';
    // Remove administrative prefixes to keep it clean but readable
    let clean = text.replace(/District Sanitaire de|District Sanitaire|Centre de Santé de Référence|Centre de Santé|Region de|Hôpital|Général/gi, '');
    clean = clean.replace(/[^a-zA-Z0-9 ]/g, '');
    clean = clean.trim();
    // Keep full name, just sanitized
    return clean.replace(/\s+/g, '_');
}

function getParentOUName() {
    const instance = $('#org-tree').jstree(true);
    // Priority 1: Highlighted Node
    const selectedNodes = instance.get_selected(true);
    if (selectedNodes.length > 0) {
        return selectedNodes[0].text;
    }

    // Priority 2: If only one checkbox checked, use that
    const checked = instance.get_checked(true);
    if (checked.length === 1) {
        return checked[0].text;
    }

    // Priority 3: Common Parent? (Too complex for now)
    return "Multi";
}

function generateTemplate() {
    const period = document.getElementById('period-input').value.trim();
    if (!selectedDataset || !selectedOrgUnits.length || !period) return;

    LoadingOverlay.show('Génération du template Excel...');

    fetch(window.GeneratorConfig.urls.generate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            dataset_id: selectedDataset.id,
            org_unit_ids: selectedOrgUnits,
            period: period,
            period_type: selectedDataset.periodType
        })
    })
        .then(async response => {
            if (!response.ok) {
                const error = await response.json();
                throw error;
            }
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // Construct Filename
            const ouPart = formatOUName(getParentOUName());
            const dsPart = formatDatasetName(selectedDataset.name); // Using stored name
            a.download = `${ouPart}_${dsPart}_${period}.xlsx`;

            a.click();
            URL.revokeObjectURL(url);
            NotificationManager.success('Template généré avec succès !');
        })
        .catch(error => {
            const message = error.error || error.message || 'Erreur lors de la génération';
            NotificationManager.error(message);
            if (error.details && Array.isArray(error.details)) {
                displayValidationErrors(error.details);
            }
        })
        .finally(() => {
            LoadingOverlay.hide();
        });
}

function generateCsvNames() {
    const period = document.getElementById('period-input').value.trim();
    if (!selectedDataset || !selectedOrgUnits.length || !period) return;

    LoadingOverlay.show('Génération du CSV (noms)...');

    fetch(window.GeneratorConfig.urls.generateCsvNames, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            dataset_id: selectedDataset.id,
            org_unit_ids: selectedOrgUnits,
            period: period,
            period_type: selectedDataset.periodType
        })
    })
        .then(async response => {
            if (!response.ok) {
                const error = await response.json();
                throw error;
            }
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dataValueSets_${period}_names.csv`;
            a.click();
            URL.revokeObjectURL(url);
            NotificationManager.success('CSV (noms) généré avec succès !');
        })
        .catch(error => {
            const message = error.error || error.message || 'Erreur lors de la génération du CSV';
            NotificationManager.error(message);
            if (error.details && Array.isArray(error.details)) {
                displayValidationErrors(error.details);
            }
        })
        .finally(() => {
            LoadingOverlay.hide();
        });
}

function deselectByGroup() {
    const groupId = document.getElementById('org-group-select').value;
    if (!groupId) return;

    LoadingOverlay.show('Désélection du groupe...');
    const url = window.GeneratorConfig.urls.orgUnitsByGroup.replace('GROUP_ID_PLACEHOLDER', groupId);
    fetch(url)
        .then(r => r.json())
        .then(data => {
            const instance = $('#org-tree').jstree(true);
            const idsToDeselect = filterIdsByScope(instance, data.ids);
            instance.uncheck_node(idsToDeselect);
            NotificationManager.success(`${idsToDeselect.length} unités désélectionnées`);
        })
        .catch(e => NotificationManager.error('Erreur de désélection'))
        .finally(() => LoadingOverlay.hide());
}

function deselectByLevel() {
    const level = document.getElementById('org-level-select').value;
    if (!level) return;

    LoadingOverlay.show('Désélection du niveau...');
    const url = window.GeneratorConfig.urls.orgUnitsByLevel.replace('LEVEL_PLACEHOLDER', level);
    fetch(url)
        .then(r => r.json())
        .then(data => {
            const instance = $('#org-tree').jstree(true);
            const idsToDeselect = filterIdsByScope(instance, data.ids);
            instance.uncheck_node(idsToDeselect);
            NotificationManager.success(`${idsToDeselect.length} unités désélectionnées`);
        })
        .catch(e => NotificationManager.error('Erreur de désélection'))
        .finally(() => LoadingOverlay.hide());
}
