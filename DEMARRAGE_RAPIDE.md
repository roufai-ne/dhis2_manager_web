# Démarrage Rapide - Module d'Imputation

## ✅ Le module est installé et opérationnel!

---

## 🚀 Comment démarrer l'application

### Option 1 : Avec l'environnement virtuel (RECOMMANDÉ)

```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web

# Activer le venv
venv\Scripts\activate

# Démarrer l'application
python run.py
```

### Option 2 : Directement avec le Python du venv

```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web

# Démarrer sans activer le venv
venv\Scripts\python.exe run.py
```

---

## 🌐 Accès au module d'imputation

Une fois l'application démarrée :

1. **Page d'accueil** : http://localhost:5000
   - Cliquez sur la carte "Imputation Automatique" (icône orange)

2. **Accès direct** : http://localhost:5000/imputation

---

## ✨ Test rapide

Pour vérifier que tout fonctionne :

```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web

# Avec le venv
venv\Scripts\python.exe test_imputation_module.py
```

Vous devriez voir :
```
[OK] Tous les tests sont passés avec succès!
```

---

## 📊 Workflow en 4 étapes

### 1. Upload
- Glissez-déposez votre fichier Excel ou CSV
- Taille max : 50 MB
- Formats : `.xlsx`, `.xls`, `.csv`

### 2. Analyse
- Consultez le score de qualité global
- Visualisez les détails par colonne
- Identifiez les valeurs manquantes et aberrantes

### 3. Configuration
- Cliquez sur "Obtenir recommandations automatiques"
- Le système choisit la meilleure méthode pour chaque colonne
- Examinez les variables prédictives

### 4. Résultats
- Cliquez sur "Exécuter l'imputation"
- Téléchargez votre fichier Excel corrigé
- Consultez le rapport détaillé

---

## 🛠️ Dépannage

### Erreur : "Module not found: scipy"

**Solution :**
```bash
cd c:\Users\PAES\Desktop\Devs\dhis2_manager\dhis2_manager_web
venv\Scripts\python.exe -m pip install scipy>=1.11.0 scikit-learn>=1.3.0
```

### Erreur : "ModuleNotFoundError"

**Cause :** Mauvais environnement Python utilisé

**Solution :** Toujours utiliser le Python du venv :
```bash
venv\Scripts\python.exe run.py
```

Ou activer le venv d'abord :
```bash
venv\Scripts\activate
python run.py
```

### L'interface ne s'affiche pas

1. Videz le cache du navigateur (Ctrl+F5)
2. Vérifiez la console JavaScript (F12)
3. Redémarrez l'application

---

## 📁 Fichiers créés par le module

**Services Backend :**
- `app/services/column_analyzer.py` - Analyse des données
- `app/services/correlation_engine.py` - Calcul des corrélations
- `app/services/imputation_engine.py` - Imputation automatique

**API :**
- `app/routes/imputation.py` - 10 endpoints REST

**Interface :**
- `app/templates/imputation.html` - Interface utilisateur

**Documentation :**
- `README_IMPUTATION.md` - Doc technique complète
- `INSTALLATION_IMPUTATION.md` - Guide d'installation
- `MODULE_IMPUTATION_RESUME.md` - Résumé de l'intégration
- `DEMARRAGE_RAPIDE.md` - Ce fichier
- `test_imputation_module.py` - Tests automatisés

---

## 💡 Exemples de fichiers à tester

### Créer un fichier de test

```python
import pandas as pd
import numpy as np

# Données avec valeurs manquantes
data = {
    'Nom': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank'],
    'Age': [25, np.nan, 30, np.nan, 28, 35],
    'Sexe': ['F', 'M', 'M', 'M', 'F', np.nan],
    'Salaire': [50000, 55000, np.nan, 60000, 52000, np.nan],
    'Diplome': ['Licence', 'Master', 'Master', np.nan, 'Licence', 'Doctorat']
}

df = pd.DataFrame(data)
df.to_excel('test_imputation.xlsx', index=False)
print("Fichier créé : test_imputation.xlsx")
```

### Utiliser avec le module

1. Démarrez l'application
2. Allez sur http://localhost:5000/imputation
3. Uploadez `test_imputation.xlsx`
4. Suivez le workflow
5. Téléchargez le fichier complété

---

## 📞 Support

**Documentation complète :**
- [README_IMPUTATION.md](README_IMPUTATION.md)

**Tests :**
```bash
venv\Scripts\python.exe test_imputation_module.py
```

**Logs de l'application :**
```bash
tail -f logs/app.log
```

---

## ✅ Checklist de vérification

- [ ] Dépendances installées (`scipy`, `scikit-learn`)
- [ ] Tests passent avec succès
- [ ] Application démarre sans erreur
- [ ] Module accessible via http://localhost:5000/imputation
- [ ] Upload de fichier fonctionne
- [ ] Analyse s'affiche correctement
- [ ] Téléchargement du fichier imputé fonctionne

---

**C'est prêt! Bon travail avec le module d'imputation automatique! 🎉**
