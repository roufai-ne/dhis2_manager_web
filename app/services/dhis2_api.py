"""
Service de connexion et récupération de métadonnées DHIS2 via API
==================================================================
Permet de se connecter à une instance DHIS2 et télécharger les métadonnées

Auteur: Amadou Roufai
"""

import logging
import requests
from typing import Dict, Tuple, Optional
from requests.auth import HTTPBasicAuth
import json

logger = logging.getLogger(__name__)


class DHIS2ApiService:
    """Service de connexion et récupération DHIS2"""
    
    def __init__(self):
        """Initialise le service"""
        self.session = requests.Session()
        self.base_url = None
        self.username = None
        self.password = None
        
    def test_connection(
        self,
        base_url: str,
        username: str,
        password: str
    ) -> Tuple[bool, str]:
        """
        Teste la connexion à une instance DHIS2
        
        Args:
            base_url: URL de base DHIS2 (ex: https://play.dhis2.org/demo)
            username: Nom d'utilisateur
            password: Mot de passe
            
        Returns:
            Tuple (succès, message)
        """
        try:
            # Nettoyer l'URL
            base_url = base_url.rstrip('/')
            
            # Tester avec /api/me
            url = f"{base_url}/api/me"
            response = self.session.get(
                url,
                auth=HTTPBasicAuth(username, password),
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                user_name = user_info.get('displayName', username)
                logger.info(f"Connexion réussie: {user_name}")
                
                # Sauvegarder les credentials
                self.base_url = base_url
                self.username = username
                self.password = password
                
                return True, f"Connecté en tant que {user_name}"
            elif response.status_code == 401:
                return False, "Identifiants invalides"
            else:
                return False, f"Erreur de connexion: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Délai de connexion dépassé"
        except requests.exceptions.ConnectionError:
            return False, "Impossible de se connecter au serveur"
        except Exception as e:
            logger.error(f"Erreur test connexion: {e}", exc_info=True)
            return False, f"Erreur: {str(e)}"
    
    def fetch_metadata(
        self,
        fields: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Récupère les métadonnées DHIS2
        
        Args:
            fields: Champs à récupérer (filter DHIS2)
            
        Returns:
            Tuple (succès, données, message)
        """
        if not self.base_url or not self.username:
            return False, None, "Non connecté"
        
        try:
            # Construction de la requête metadata
            # On récupère: organisationUnits, dataSets, dataElements, 
            # categoryOptionCombos, categoryOptions, categoryCombos, categories
            
            params = {
                'organisationUnits': 'true',
                'dataSets': 'true',
                'dataElements': 'true',
                'categoryOptionCombos': 'true',
                'categoryOptions': 'true',
                'categoryCombos': 'true',
                'categories': 'true',
                'organisationUnitLevels': 'true',
                'organisationUnitGroups': 'true',
                'organisationUnitGroupSets': 'true',
                'dataElementGroups': 'true',
                'dataElementGroupSets': 'true',
                'sections': 'true'
            }
            
            logger.info("Récupération des métadonnées DHIS2...")
            
            url = f"{self.base_url}/api/metadata.json"
            response = self.session.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                params=params,
                timeout=120  # 2 minutes pour les gros téléchargements
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Statistiques
                stats = {
                    'organisationUnits': len(data.get('organisationUnits', [])),
                    'dataSets': len(data.get('dataSets', [])),
                    'dataElements': len(data.get('dataElements', [])),
                    'categoryOptionCombos': len(data.get('categoryOptionCombos', []))
                }
                
                logger.info(f"Métadonnées récupérées: {stats}")
                
                message = (
                    f"Métadonnées téléchargées: "
                    f"{stats['organisationUnits']} organisations, "
                    f"{stats['dataSets']} datasets, "
                    f"{stats['dataElements']} éléments"
                )
                
                return True, data, message
            
            elif response.status_code == 401:
                return False, None, "Session expirée, reconnectez-vous"
            else:
                return False, None, f"Erreur serveur: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, None, "Délai de téléchargement dépassé"
        except requests.exceptions.ConnectionError:
            return False, None, "Connexion perdue"
        except json.JSONDecodeError:
            return False, None, "Réponse invalide du serveur"
        except Exception as e:
            logger.error(f"Erreur récupération métadonnées: {e}", exc_info=True)
            return False, None, f"Erreur: {str(e)}"
    
    def fetch_metadata_incremental(
        self,
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Récupère les métadonnées par morceaux avec progression
        
        Args:
            progress_callback: Fonction appelée avec (pourcentage, message)
            
        Returns:
            Tuple (succès, données, message)
        """
        if not self.base_url or not self.username:
            return False, None, "Non connecté"
        
        try:
            result_data = {}
            
            # Liste des ressources à récupérer
            resources = [
                ('organisationUnits', 'Organisations', 20),
                ('dataSets', 'Datasets', 15),
                ('dataElements', 'Éléments de données', 25),
                ('categoryOptionCombos', 'Combinaisons catégories', 20),
                ('categoryOptions', 'Options catégories', 10),
                ('categoryCombos', 'Combos catégories', 5),
                ('categories', 'Catégories', 5)
            ]
            
            total_progress = 0
            auth = HTTPBasicAuth(self.username, self.password)
            
            for resource, label, weight in resources:
                if progress_callback:
                    progress_callback(total_progress, f"Téléchargement: {label}...")
                
                url = f"{self.base_url}/api/{resource}.json"
                params = {
                    'paging': 'false',
                    'fields': ':all'
                }
                
                response = self.session.get(url, auth=auth, params=params, timeout=60)
                
                if response.status_code == 200:
                    data = response.json()
                    result_data[resource] = data.get(resource, [])
                    logger.info(f"{resource}: {len(result_data[resource])} éléments")
                else:
                    logger.warning(f"Erreur pour {resource}: {response.status_code}")
                    result_data[resource] = []
                
                total_progress += weight
                if progress_callback:
                    progress_callback(total_progress, f"{label} téléchargé")
            
            # Compléter avec organisationUnitLevels et groups
            extras = [
                ('organisationUnitLevels', 'Niveaux UO'),
                ('organisationUnitGroups', 'Groupes UO'),
                ('dataElementGroups', 'Groupes éléments')
            ]
            
            for resource, label in extras:
                url = f"{self.base_url}/api/{resource}.json"
                params = {'paging': 'false', 'fields': ':all'}
                try:
                    response = self.session.get(url, auth=auth, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        result_data[resource] = data.get(resource, [])
                except:
                    result_data[resource] = []
            
            if progress_callback:
                progress_callback(100, "Téléchargement terminé")
            
            message = (
                f"Métadonnées téléchargées: "
                f"{len(result_data.get('organisationUnits', []))} organisations, "
                f"{len(result_data.get('dataSets', []))} datasets"
            )
            
            return True, result_data, message
            
        except Exception as e:
            logger.error(f"Erreur téléchargement incrémental: {e}", exc_info=True)
            return False, None, f"Erreur: {str(e)}"
    
    def disconnect(self):
        """Déconnexion et nettoyage"""
        self.session.close()
        self.base_url = None
        self.username = None
        self.password = None
        logger.info("Déconnexion DHIS2")
