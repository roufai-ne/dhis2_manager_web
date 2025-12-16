# Guide de Dépannage - Interface Non Visible

## Problème : Les nouvelles fonctionnalités ne s'affichent pas

### ✅ Vérification 1 : Tous les fichiers sont en place

Exécutez le script de vérification :
```bash
python verify_simple.py
```

**Résultat attendu** : Tous les éléments devraient être `[OK]`

---

### ✅ Vérification 2 : Le serveur Flask est redémarré

1. **Arrêtez le serveur** : `Ctrl+C` dans le terminal où il tourne
2. **Relancez-le** : `python run.py`
3. **Vérifiez** qu'il démarre sans erreur

**Log attendu** :
```
* Running on http://127.0.0.1:5000
```

---

### ✅ Vérification 3 : Cache du navigateur vidé

Le problème le plus fréquent est le cache du navigateur qui sert l'ancienne version du HTML/CSS/JS.

#### Chrome / Edge
1. Ouvrez http://localhost:5000/calculator
2. Appuyez sur `Ctrl+Shift+R` (Windows) ou `Cmd+Shift+R` (Mac)
3. Ou : `F12` → Onglet "Network" → Cochez "Disable cache" → Rafraîchissez

#### Firefox
1. Ouvrez http://localhost:5000/calculator
2. Appuyez sur `Ctrl+Shift+R` (Windows) ou `Cmd+Shift+R` (Mac)
3. Ou : `F12` → Onglet "Réseau" → Cochez "Désactiver le cache" → Rafraîchissez

#### Méthode radicale (tous navigateurs)
1. `F12` pour ouvrir les DevTools
2. Clic droit sur le bouton de rafraîchissement (à gauche de la barre d'adresse)
3. Sélectionnez "Vider le cache et actualiser de force"

---

### ✅ Vérification 4 : Console JavaScript

Ouvrez la console du navigateur pour voir s'il y a des erreurs :

1. Appuyez sur `F12`
2. Onglet "Console"
3. Rechargez la page (`Ctrl+R`)

**Erreurs possibles** :
- `Uncaught ReferenceError` → Le JavaScript n'est pas chargé
- `404 Not Found` → Un fichier est manquant
- `SyntaxError` → Erreur de syntaxe dans le code

**Pas d'erreur ?** → Bon signe ! Passez à la vérification suivante.

---

### ✅ Vérification 5 : Éléments HTML présents

Dans la console du navigateur, tapez :
```javascript
document.getElementById('sheet-selection')
document.getElementById('data-type-selection')
document.getElementById('pivot-options')
```

**Résultat attendu** :
- Chaque commande devrait retourner un élément HTML (pas `null`)
- Si `null` → L'élément n'est pas dans le DOM → Cache navigateur

---

### ✅ Vérification 6 : Upload d'un fichier

Les nouveautés apparaissent après l'upload d'un fichier Excel :

1. **Uploadez un fichier** via la dropzone
2. **Attendez** le message "Fichier chargé avec succès"
3. **Vérifiez** que la section verte apparaît (avec le nom du fichier)

**Dans cette section verte, vous devriez voir** :
- Si fichier multi-onglets : Un dropdown "Sélectionnez l'onglet"
- Toujours : Deux cartes "Mode Normal" et "Tableau Croisé"

---

## 📋 Checklist de dépannage

Cochez au fur et à mesure :

- [ ] Script `verify_simple.py` exécuté → Tous `[OK]`
- [ ] Serveur Flask redémarré
- [ ] Cache navigateur vidé (`Ctrl+Shift+R`)
- [ ] Console JavaScript sans erreur
- [ ] Éléments HTML présents dans le DOM
- [ ] Fichier Excel uploadé
- [ ] Section verte avec nom du fichier visible

---

## 🔍 Diagnostic selon les symptômes

### Symptôme 1 : Rien ne change après vidage cache
**Solution** : Vérifiez que le serveur Flask a bien redémarré avec la nouvelle version

### Symptôme 2 : Erreur JavaScript dans la console
**Solution** : Copiez l'erreur et cherchez le fichier/ligne indiqué

### Symptôme 3 : Les éléments HTML sont `null`
**Solution** : Le template n'est pas chargé. Redémarrez Flask ET videz le cache

### Symptôme 4 : La section verte ne s'affiche pas après upload
**Solution** : Problème côté upload. Vérifiez les logs Flask :
```bash
tail -f logs/app.log
```

### Symptôme 5 : Les cartes de sélection ne sont pas stylisées
**Solution** : CSS non chargé. Videz le cache et rechargez

---

## 🧪 Test de présence des éléments (Console JavaScript)

Ouvrez la console (`F12`) et collez ce code :

```javascript
console.log("=== VERIFICATION ELEMENTS ===");
console.log("Sheet selection:", document.getElementById('sheet-selection') ? "OK" : "MANQUANT");
console.log("Data type selection:", document.getElementById('data-type-selection') ? "OK" : "MANQUANT");
console.log("Pivot options:", document.getElementById('pivot-options') ? "OK" : "MANQUANT");
console.log("Select sheet:", document.getElementById('select-sheet') ? "OK" : "MANQUANT");
console.log("Pivot DE:", document.getElementById('pivot-data-element') ? "OK" : "MANQUANT");

console.log("\n=== VERIFICATION FONCTIONS ===");
console.log("loadExcelSheets:", typeof loadExcelSheets === 'function' ? "OK" : "MANQUANT");
console.log("loadDataElements:", typeof loadDataElements === 'function' ? "OK" : "MANQUANT");

console.log("\n=== VERIFICATION STYLES ===");
const dataTypeCard = document.querySelector('.data-type-card');
console.log("Classe .data-type-card:", dataTypeCard ? "OK" : "MANQUANT");
```

**Résultat attendu** :
```
=== VERIFICATION ELEMENTS ===
Sheet selection: OK
Data type selection: OK
Pivot options: OK
Select sheet: OK
Pivot DE: OK

=== VERIFICATION FONCTIONS ===
loadExcelSheets: OK
loadDataElements: OK

=== VERIFICATION STYLES ===
Classe .data-type-card: OK
```

Si tout est "OK" mais vous ne voyez rien → C'est un problème de visibilité CSS. Vérifiez :
```javascript
const dataTypeSelection = document.getElementById('data-type-selection');
console.log("Display:", window.getComputedStyle(dataTypeSelection).display);
console.log("Visibility:", window.getComputedStyle(dataTypeSelection).visibility);
```

**Résultat attendu** :
- `Display: block` (pas `none`)
- `Visibility: visible` (pas `hidden`)

---

## 🆘 Si rien ne fonctionne

### Option 1 : Navigation privée

Testez dans une fenêtre de navigation privée :
- Chrome : `Ctrl+Shift+N`
- Firefox : `Ctrl+Shift+P`

Cela garantit un cache vide.

### Option 2 : Autre navigateur

Testez dans un autre navigateur pour éliminer les problèmes spécifiques.

### Option 3 : Vérification manuelle du template

1. Ouvrez `app/templates/calculator.html`
2. Cherchez `id="data-type-selection"`
3. Vérifiez que cette ligne existe : ligne 372 environ

Si elle n'existe pas → Le fichier n'a pas été sauvegardé correctement

### Option 4 : Forcer le rechargement du template Flask

Flask met en cache les templates. Pour forcer le rechargement :

1. Arrêtez Flask
2. Supprimez le dossier `__pycache__` s'il existe
3. Relancez Flask avec :
```bash
python run.py
```

---

## 📞 Dernier recours

Si après toutes ces étapes rien ne fonctionne :

1. Copiez le contenu de la console JavaScript (F12)
2. Copiez les dernières lignes de `logs/app.log`
3. Faites une capture d'écran de la page
4. Envoyez ces informations pour diagnostic

---

**Auteur** : Amadou Roufai
**Date** : Décembre 2025
**Version** : 2.0
