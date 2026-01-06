# Guide d'utilisation du Module d'Imputation

## 🎯 Le module d'imputation est maintenant accessible dans le menu!

---

## 📍 Comment accéder au module

### Méthode 1 : Via le menu de navigation
1. Démarrez l'application : `venv\Scripts\python.exe run.py`
2. Ouvrez http://localhost:5000
3. Dans le menu de navigation, cliquez sur **"Imputation"** (icône baguette magique ✨)

### Méthode 2 : Depuis la page d'accueil
1. Démarrez l'application
2. Ouvrez http://localhost:5000
3. Cliquez sur la carte **"Imputation Automatique"** (carte orange)

### Méthode 3 : Accès direct
- URL directe : http://localhost:5000/imputation

---

## 🚀 Démarrage de l'application

```bash
# Se placer dans le répertoire
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web

# Démarrer avec l'environnement virtuel
venv\Scripts\python.exe run.py
```

L'application sera accessible à : **http://localhost:5000**

---

## 📋 Workflow complet - Étape par étape

### Étape 1 : Upload du fichier

**Ce que vous voyez :**
- Zone de drag & drop
- Bouton "Parcourir les fichiers"
- Formats acceptés : .xlsx, .xls, .csv
- Taille max : 50 Mo

**Actions :**
1. Glissez-déposez votre fichier dans la zone
   OU
2. Cliquez sur "Parcourir" et sélectionnez votre fichier
3. Attendez l'upload (barre de progression)

**Résultat :**
- Passage automatique à l'étape 2 "Analyse"
- Affichage du résumé de qualité

---

### Étape 2 : Analyse de la qualité

**Ce que vous voyez :**
- **Résumé global :**
  - Nombre de lignes
  - Nombre de colonnes
  - Valeurs manquantes totales
  - Score de qualité global

**Actions :**
1. Consultez le résumé
2. Cliquez sur "Voir analyse détaillée"

**Résultat affiché :**
- **Tableau détaillé par colonne :**
  - Nom de la colonne
  - Type détecté (numérique, catégoriel, etc.)
  - Nombre de valeurs manquantes (%)
  - Nombre de valeurs aberrantes
  - Score de qualité (barre colorée)

**Code couleur des scores :**
- 🟢 Vert (80-100) : Excellente qualité
- 🟡 Orange (60-79) : Qualité moyenne
- 🔴 Rouge (0-59) : Qualité faible

---

### Étape 3 : Configuration de l'imputation

**Ce que vous voyez :**
- Bouton "Obtenir les recommandations automatiques"

**Actions :**
1. Cliquez sur "Obtenir recommandations automatiques"
2. Attendez le calcul des corrélations (2-3 secondes)

**Résultat affiché :**
Pour chaque colonne avec valeurs manquantes :
- **Nom de la colonne**
- **Nombre de valeurs manquantes** (avec % et badge coloré)
- **Méthode recommandée** (ex: "group_mean", "knn", "median")
- **Variables prédictives** (colonnes utilisées pour l'imputation)

**Exemple de recommandation :**
```
DATE_NAISSANCE
├─ 5791 manquants (41.3%)
├─ Méthode: group_mean
└─ Variables: SEXE, DIPLOME, STATUT
```

**Actions supplémentaires :**
- Vérifiez les recommandations
- Les méthodes sont automatiquement sélectionnées selon :
  - Type de données
  - % de valeurs manquantes
  - Force des corrélations

---

### Étape 4 : Exécution de l'imputation

**Actions :**
1. Cliquez sur **"Exécuter l'imputation"**
2. Attendez le traitement (quelques secondes)

**Pendant le traitement :**
- Bouton désactivé avec texte "Traitement en cours..."
- Pas de rechargement de page nécessaire

**Résultat :**
- Passage automatique à l'étape 4 "Résultats"
- Affichage du rapport de succès

---

### Étape 5 : Résultats et téléchargement

**Ce que vous voyez :**
- ✅ Message de succès : "Imputation terminée avec succès!"
- Badge vert avec le nombre total de corrections
- **Détail par colonne :**
  - Nom de la colonne
  - Méthode utilisée
  - Nombre de corrections effectuées

**Actions :**
1. **Télécharger le fichier corrigé :**
   - Cliquez sur "Télécharger le fichier corrigé"
   - Fichier Excel avec nom préfixé "imputed_"
   - Toutes les valeurs manquantes sont remplies

2. **Traiter un nouveau fichier :**
   - Cliquez sur "Nouveau fichier"
   - Retour à l'étape 1

---

## 💡 Exemples de méthodes d'imputation

### Méthodes simples
- **mean** : Moyenne des valeurs existantes
- **median** : Médiane (robuste aux outliers)
- **mode** : Valeur la plus fréquente

### Méthodes par groupe
- **group_mean** : Moyenne par groupe de variables corrélées
  - Exemple : Moyenne de l'âge par (SEXE, DIPLOME)
- **group_median** : Médiane par groupe
- **group_mode** : Mode par groupe

### Méthodes avancées
- **knn** : K plus proches voisins
  - Utilise les 5 lignes les plus similaires

---

## 🎨 Interface visuelle

### Indicateurs de progression
```
Étape 1 ━━━━━━━━━━━━━━━━━━━━━ Étape 2 ─────── Étape 3 ─────── Étape 4
[✓ Upload]     [○ Analyse]    [○ Config]    [○ Résultats]

Au fur et à mesure, les étapes se colorent en bleu
```

### Badges de qualité
```
Colonne          Type        Manquants    Score
─────────────────────────────────────────────────
AGE              numeric     10 (10%)     [████████░] 90%
STATUT           categorical 10 (10%)     [████████░] 88%
REVENU           numeric     5 (5%)       [█████████] 95%
```

---

## 📊 Exemple complet d'utilisation

### Fichier d'entrée : `donnees_incompletes.xlsx`
```
Nom      | Age | Sexe | Salaire | Diplome
─────────|────|──────|──────────|─────────
Alice    | 25  | F    | 50000   | Licence
Bob      | ?   | M    | 55000   | Master
Charlie  | 30  | M    | ?       | Master
David    | ?   | M    | 60000   | ?
Eve      | 28  | F    | 52000   | Licence
```

### Après analyse
```
AGE      : 2 manquants (40%) → Méthode: group_median (par SEXE, DIPLOME)
SALAIRE  : 1 manquant (20%)  → Méthode: median
DIPLOME  : 1 manquant (20%)  → Méthode: mode
```

### Fichier de sortie : `imputed_donnees_incompletes.xlsx`
```
Nom      | Age | Sexe | Salaire | Diplome
─────────|────|──────|──────────|─────────
Alice    | 25  | F    | 50000   | Licence
Bob      | 30  | M    | 55000   | Master    ← Age imputé
Charlie  | 30  | M    | 54000   | Master    ← Salaire imputé
David    | 30  | M    | 60000   | Master    ← Age + Diplome imputés
Eve      | 28  | F    | 52000   | Licence
```

---

## ⚠️ Points d'attention

### Qualité de l'imputation
- ✅ **< 10% manquants** : Excellente fiabilité
- ⚠️ **10-30% manquants** : Bonne fiabilité
- ⚠️ **30-50% manquants** : Fiabilité moyenne (avertissement affiché)
- ❌ **> 50% manquants** : Faible fiabilité

### Types de fichiers
- ✅ Excel (.xlsx, .xls) : Multi-feuilles supporté
- ✅ CSV : Détection auto de l'encodage et du séparateur
- ❌ Autres formats : Non supportés

### Taille des fichiers
- Limite : 50 MB
- Recommandé : < 10 MB pour performance optimale

---

## 🔧 Dépannage

### Le module n'apparaît pas dans le menu
**Solution :** Videz le cache du navigateur (Ctrl+F5)

### Erreur lors de l'upload
1. Vérifiez le format du fichier (.xlsx, .xls, .csv)
2. Vérifiez la taille (< 50 MB)
3. Assurez-vous que le fichier n'est pas corrompu

### Erreur "Module not found"
```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web
venv\Scripts\python.exe -m pip install scipy scikit-learn
```

### L'analyse ne s'affiche pas
1. Vérifiez la console JavaScript (F12)
2. Redémarrez l'application
3. Testez avec un fichier plus petit

---

## 📚 Documentation complète

Pour plus de détails techniques :
- **[README_IMPUTATION.md](README_IMPUTATION.md)** - Documentation technique
- **[DEMARRAGE_RAPIDE.md](DEMARRAGE_RAPIDE.md)** - Guide de démarrage
- **[MODULE_IMPUTATION_RESUME.md](MODULE_IMPUTATION_RESUME.md)** - Résumé de l'intégration

---

## ✅ Checklist avant utilisation

- [ ] Application démarrée (`venv\Scripts\python.exe run.py`)
- [ ] Menu "Imputation" visible dans la navigation
- [ ] Fichier à traiter prêt (.xlsx, .xls ou .csv)
- [ ] Taille du fichier < 50 MB
- [ ] Navigateur moderne (Chrome, Firefox, Edge)

---

**Le module est prêt! Bonne utilisation! 🎉**
