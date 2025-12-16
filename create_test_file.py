"""
Script pour créer un fichier Excel de test multi-onglets
pour tester la fonctionnalité de sélection d'onglets et mode pivot
"""

import pandas as pd
from datetime import datetime

def create_test_file():
    """Crée un fichier Excel avec plusieurs onglets pour tester les deux modes"""

    # Onglet 1 : Données normales (mode template)
    print("📝 Création onglet 'Données' (mode normal)...")
    data_normal = {
        'Structure': ['Faculté A', 'Faculté B', 'Faculté C', 'Faculté A', 'Faculté B'],
        'Data Element': ['Inscrits', 'Inscrits', 'Inscrits', 'Diplômés', 'Diplômés'],
        'Période': ['2024', '2024', '2024', '2024', '2024'],
        'Catégorie': ['Licence', 'Licence', 'Licence', 'Master', 'Master'],
        'Valeur': [150, 200, 180, 45, 60]
    }
    df_normal = pd.DataFrame(data_normal)

    # Onglet 2 : Tableau croisé - Inscriptions
    print("📊 Création onglet 'Premier Cycle' (tableau croisé)...")
    data_pivot1 = {
        'Indicateur': ['Inscrits', 'Diplômés', 'Abandons', 'Redoublants'],
        'Faculté A': [150, 45, 10, 15],
        'Faculté B': [200, 60, 12, 20],
        'Faculté C': [180, 55, 8, 18],
        'Faculté D': [220, 70, 15, 25]
    }
    df_pivot1 = pd.DataFrame(data_pivot1)

    # Onglet 3 : Tableau croisé - Répartition par genre
    print("📊 Création onglet 'Deuxième Cycle' (tableau croisé)...")
    data_pivot2 = {
        'Indicateur': ['Garçons', 'Filles', 'Total', 'Non spécifié'],
        'Faculté A': [80, 70, 150, 0],
        'Faculté B': [110, 90, 200, 0],
        'Faculté C': [95, 85, 180, 0],
        'Faculté D': [115, 105, 220, 0]
    }
    df_pivot2 = pd.DataFrame(data_pivot2)

    # Onglet 4 : Tableau croisé - Données par niveau
    print("📊 Création onglet 'Troisième Cycle' (tableau croisé)...")
    data_pivot3 = {
        'Indicateur': ['Niveau 1', 'Niveau 2', 'Niveau 3', 'Niveau 4'],
        'Faculté A': [50, 40, 35, 25],
        'Faculté B': [65, 55, 45, 35],
        'Faculté C': [60, 50, 40, 30],
        'Faculté D': [70, 60, 50, 40]
    }
    df_pivot3 = pd.DataFrame(data_pivot3)

    # Générer nom de fichier avec date
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'TEST_MultiOnglets_{timestamp}.xlsx'

    # Sauvegarder
    print(f"\n💾 Enregistrement dans {filename}...")
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_normal.to_excel(writer, sheet_name='Données', index=False)
        df_pivot1.to_excel(writer, sheet_name='Premier Cycle', index=False)
        df_pivot2.to_excel(writer, sheet_name='Deuxième Cycle', index=False)
        df_pivot3.to_excel(writer, sheet_name='Troisième Cycle', index=False)

    print(f"\n✅ Fichier {filename} créé avec succès!")
    print("\n📋 Contenu du fichier:")
    print(f"   • Onglet 'Données' : {len(df_normal)} lignes (mode normal)")
    print(f"   • Onglet 'Premier Cycle' : {len(df_pivot1)} lignes x {len(df_pivot1.columns)} colonnes (tableau croisé)")
    print(f"   • Onglet 'Deuxième Cycle' : {len(df_pivot2)} lignes x {len(df_pivot2.columns)} colonnes (tableau croisé)")
    print(f"   • Onglet 'Troisième Cycle' : {len(df_pivot3)} lignes x {len(df_pivot3.columns)} colonnes (tableau croisé)")

    print("\n🧪 Prêt pour les tests!")
    print("\nScénarios de test suggérés:")
    print("1. Traiter 'Données' en mode normal")
    print("2. Traiter 'Premier Cycle' en mode tableau croisé")
    print("3. Traiter 'Deuxième Cycle' en mode tableau croisé")
    print("4. Traiter 'Troisième Cycle' en mode tableau croisé")

    return filename


def create_simple_test_file():
    """Crée un fichier simple avec UN SEUL onglet pour tester la rétrocompatibilité"""

    print("📝 Création fichier simple (un seul onglet)...")
    data = {
        'Structure': ['Faculté A', 'Faculté B', 'Faculté C'],
        'Data Element': ['Inscrits', 'Inscrits', 'Inscrits'],
        'Période': ['2024', '2024', '2024'],
        'Valeur': [150, 200, 180]
    }
    df = pd.DataFrame(data)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'TEST_Simple_{timestamp}.xlsx'

    print(f"💾 Enregistrement dans {filename}...")
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Données', index=False)

    print(f"✅ Fichier {filename} créé avec succès!")
    print(f"   • 1 seul onglet 'Données' avec {len(df)} lignes")
    print("\n🧪 Utilisez ce fichier pour tester la rétrocompatibilité")
    print("   → Le sélecteur d'onglets ne doit PAS apparaître")

    return filename


if __name__ == '__main__':
    import sys

    print("=" * 60)
    print("   GÉNÉRATEUR DE FICHIERS DE TEST")
    print("   Multi-Onglets & Tableaux Croisés")
    print("=" * 60)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == '--simple':
        # Fichier simple (rétrocompatibilité)
        create_simple_test_file()
    else:
        # Fichier multi-onglets (test complet)
        create_test_file()

        print("\n💡 Astuce: Pour créer un fichier simple (1 onglet), utilisez:")
        print("   python create_test_file.py --simple")

    print()
    print("=" * 60)
