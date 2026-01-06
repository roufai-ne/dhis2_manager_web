# Guide des Méthodes d'Imputation

## Vue d'ensemble

Le module d'imputation propose **12 méthodes** allant des plus simples aux plus avancées utilisant le Machine Learning. Ce guide vous aide à choisir la méthode optimale selon vos données.

---

## 📊 Méthodes Statistiques de Base

### 1. **Moyenne (Mean)**
- **Quand l'utiliser** : Données numériques sans valeurs extrêmes
- **Avantages** : Simple, rapide, préserve la moyenne globale
- **Inconvénients** : Sensible aux outliers, réduit la variance
- **Exemple** : Températures moyennes, scores normalement distribués

### 2. **Médiane (Median)**
- **Quand l'utiliser** : Données numériques avec outliers possibles
- **Avantages** : Robuste aux valeurs extrêmes, préserve la distribution
- **Inconvénients** : Moins précise que la moyenne pour données normales
- **Exemple** : Revenus, prix immobiliers, notes d'examen

### 3. **Mode (Mode)**
- **Quand l'utiliser** : Données catégorielles ou discrètes
- **Avantages** : Préserve la catégorie la plus fréquente
- **Inconvénients** : Perd de l'information si plusieurs modes
- **Exemple** : Genres, régions, types de produits

---

## 👥 Méthodes par Groupe

### 4. **Moyenne par Groupe (Group Mean)**
- **Quand l'utiliser** : Données avec catégories distinctes
- **Avantages** : Respecte les sous-populations
- **Inconvénients** : Nécessite des groupes bien définis
- **Exemple** : Salaires par département, scores par école

### 5. **Médiane par Groupe (Group Median)**
- **Quand l'utiliser** : Groupes avec outliers possibles
- **Avantages** : Robuste + respect des catégories
- **Inconvénients** : Nécessite suffisamment de données par groupe
- **Exemple** : Prix par quartier, notes par classe

### 6. **Mode par Groupe (Group Mode)**
- **Quand l'utiliser** : Données catégorielles avec sous-groupes
- **Avantages** : Préserve les patterns catégoriels par groupe
- **Inconvénients** : Peut être instable si petits groupes
- **Exemple** : Préférences par âge, choix par région

---

## 🚀 Méthodes Avancées (Recommandées)

### 7. **KNN - K-Nearest Neighbors**
- **Précision** : ⭐⭐⭐⭐
- **Vitesse** : ⭐⭐⭐
- **Quand l'utiliser** : Données avec patterns de similarité
- **Principe** : Utilise les K voisins les plus proches pour prédire
- **Avantages** : 
  - Capture les relations non-linéaires
  - Fonctionne bien avec plusieurs variables corrélées
  - Pas d'hypothèse sur la distribution
- **Inconvénients** : 
  - Plus lent sur gros datasets
  - Sensible au choix de K
- **Paramètres** : 
  - `k` : nombre de voisins (recommandé : 3-10)
- **Exemple** : Données médicales, caractéristiques produits

### 8. **MICE - Multiple Imputation by Chained Equations** ⭐
- **Précision** : ⭐⭐⭐⭐⭐
- **Vitesse** : ⭐⭐
- **Quand l'utiliser** : Plusieurs colonnes manquantes, relations complexes
- **Principe** : Imputation itérative multivariée - chaque variable est modélisée par les autres
- **Avantages** :
  - **Meilleure méthode pour données multivariées**
  - Capture les dépendances entre variables
  - Itère jusqu'à convergence
  - Gold standard en statistiques
- **Inconvénients** : 
  - Plus lent (plusieurs itérations)
  - Nécessite plusieurs variables
- **Paramètres** :
  - `max_iter` : nombre d'itérations (défaut : 10)
- **Exemple** : Enquêtes avec données multidimensionnelles, données cliniques

### 9. **Random Forest** ⭐
- **Précision** : ⭐⭐⭐⭐⭐
- **Vitesse** : ⭐⭐
- **Quand l'utiliser** : Relations non-linéaires complexes, données hétérogènes
- **Principe** : Utilise un ensemble d'arbres de décision pour prédire
- **Avantages** :
  - **Excellent pour relations complexes**
  - Robuste aux outliers
  - Gère automatiquement les interactions
  - Fonctionne pour numérique ET catégoriel
- **Inconvénients** :
  - Plus lent
  - Moins interprétable
- **Paramètres** :
  - `n_estimators` : nombre d'arbres (défaut : 100)
- **Exemple** : Données mixtes complexes, prédictions produits

### 10. **Régression Linéaire** ⭐
- **Précision** : ⭐⭐⭐⭐
- **Vitesse** : ⭐⭐⭐⭐
- **Quand l'utiliser** : Relations linéaires claires entre variables
- **Principe** : Modèle linéaire pour prédire à partir des autres colonnes
- **Avantages** :
  - Rapide et efficace
  - Interprétable
  - **Optimal si corrélations linéaires fortes**
- **Inconvénients** :
  - Assume linéarité
  - Ne fonctionne que pour numériques
- **Exemple** : Données économiques, mesures physiques corrélées

### 11. **Interpolation Linéaire**
- **Précision** : ⭐⭐⭐⭐
- **Vitesse** : ⭐⭐⭐⭐⭐
- **Quand l'utiliser** : Séries temporelles, données ordonnées
- **Principe** : Interpole entre valeurs adjacentes
- **Avantages** :
  - Très rapide
  - Préserve les tendances
  - **Idéal pour time series**
- **Inconvénients** :
  - Nécessite un ordre logique
  - Suppose continuité
- **Exemple** : Températures, prix journaliers, capteurs

### 12. **Propagation (Forward Fill)**
- **Précision** : ⭐⭐⭐
- **Vitesse** : ⭐⭐⭐⭐⭐
- **Quand l'utiliser** : Données séquentielles stables
- **Principe** : Propage la dernière valeur connue
- **Avantages** :
  - Très simple et rapide
  - Préserve les valeurs observées
- **Inconvénients** :
  - Ignore les tendances
  - Peut créer des plateaux
- **Exemple** : États binaires, statuts

---

## 🎯 Comment Choisir ?

### Arbre de Décision

```
Vos données sont-elles...

1. **Séries temporelles ?**
   → Interpolation linéaire ou Forward Fill

2. **Catégorielles ?**
   → Mode ou Mode par Groupe
   
3. **Avec des groupes clairs ?**
   → Méthodes par Groupe (Mean/Median/Mode)
   
4. **Plusieurs colonnes manquantes ?**
   → MICE ⭐ (meilleur choix)
   
5. **Relations complexes non-linéaires ?**
   → Random Forest ⭐
   
6. **Corrélations linéaires fortes ?**
   → Régression Linéaire ⭐
   
7. **Patterns de similarité ?**
   → KNN
   
8. **Simples sans outliers ?**
   → Moyenne
   
9. **Avec outliers possibles ?**
   → Médiane
```

---

## 📈 Comparaison de Performance

| Méthode | Précision | Vitesse | Complexité | Cas d'usage |
|---------|-----------|---------|------------|-------------|
| Moyenne | ⭐⭐ | ⭐⭐⭐⭐⭐ | Simple | Baseline |
| Médiane | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Simple | Outliers |
| KNN | ⭐⭐⭐⭐ | ⭐⭐⭐ | Moyen | Similarité |
| **MICE** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Élevé | **Multivarié** |
| **Random Forest** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Élevé | **Non-linéaire** |
| **Régression** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Moyen | **Linéaire** |
| Interpolation | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Simple | **Time series** |

---

## 💡 Recommandations Générales

### Pour la plupart des cas :
1. **Essayez d'abord MICE** - c'est le gold standard statistique
2. **Si trop lent** → Random Forest ou Régression
3. **Si données temporelles** → Interpolation
4. **Si très simple** → Médiane (robuste) ou Moyenne

### Bonnes pratiques :
- ✅ **Testez plusieurs méthodes** sur un échantillon
- ✅ **Validez les résultats** visuellement dans l'aperçu
- ✅ **Comparez** la qualité avec les indicateurs
- ✅ **Documentez** la méthode choisie

### À éviter :
- ❌ Ne pas toujours utiliser la moyenne (trop simpliste)
- ❌ Ne pas ignorer la nature des données (temporelles, groupées...)
- ❌ Ne pas imputer sans comprendre les patterns

---

## 🔬 Détails Techniques

### MICE (Iterative Imputer)
```python
# Utilise BayesianRidge par défaut
# Itère jusqu'à convergence (max 10 iterations)
# Modélise chaque variable par les autres
```

### Random Forest
```python
# Régression pour numériques : RandomForestRegressor
# Classification pour catégoriels : RandomForestClassifier  
# 100 arbres par défaut
# n_jobs=-1 pour parallélisation
```

### Régression
```python
# LinearRegression pour numériques
# LogisticRegression pour catégoriels
# Trouve les meilleurs coefficients linéaires
```

---

## 📚 Références

- Buuren & Groothuis-Oudshoorn (2011). "mice: Multivariate Imputation by Chained Equations in R"
- Breiman (2001). "Random Forests"
- Troyanskaya et al. (2001). "Missing value estimation methods for DNA microarrays"

---

**Version** : 4.3  
**Dernière mise à jour** : 2025  
**Module** : Imputation Automatique - DHIS2 Manager
