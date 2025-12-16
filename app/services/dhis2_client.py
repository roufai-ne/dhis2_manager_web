import requests
import logging
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class DHIS2Client:
    """
    Client for interacting with DHIS2 API.
    Supports Basic Auth and Personal Access Token (PAT).
    """

    def __init__(self, url: str, username: Optional[str] = None, password: Optional[str] = None, token: Optional[str] = None):
        self.url = url.rstrip('/') + '/api/'
        self.session = requests.Session()
        
        if token:
            self.session.headers.update({'Authorization': f'ApiToken {token}'})
        elif username and password:
            self.session.auth = (username, password)
        else:
            raise ValueError("Either (username, password) or token must be provided")
            
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'DHIS2Manager/5.0'
        })

    def validate_connection(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validates the connection to DHIS2.
        Returns: (success, message, system_info)
        """
        try:
            response = self.session.get(urljoin(self.url, 'system/info'))
            
            if response.status_code == 200:
                return True, "Connection successful", response.json()
            elif response.status_code == 401:
                return False, "Authentication failed. Please check your credentials.", None
            else:
                return False, f"Connection failed with status code: {response.status_code}", None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error: {e}")
            return False, f"Connection error: {str(e)}", None

    def fetch_metadata(self) -> Tuple[bool, Dict, Optional[str]]:
        """
        Fetches all required metadata from DHIS2.
        Returns: (success, metadata_dict, error_message)
        """
        metadata = {
            'organisationUnits': [],
            'dataSets': [],
            'dataElements': [],
            'categoryOptionCombos': [],
            'categories': [],
            'categoryCombos': [],
            'categoryOptions': []
        }
        
        # Endpoints to fetch with their fields
        # Endpoints to fetch with their fields
        endpoints = {
            'organisationUnits': 'id,name,code,shortName,parent,level,path,openingDate,closedDate,comment,geometry',
            'organisationUnitLevels': 'id,name,level',
            'organisationUnitGroups': 'id,name,code,shortName,organisationUnits[id]',
            'organisationUnitGroupSets': 'id,name,code,shortName,organisationUnitGroups[id]',
            'dataSets': 'id,name,code,periodType,dataSetElements[dataElement[id]],organisationUnits[id]',
            'dataElements': 'id,name,code,shortName,description,valueType,aggregationType,domainType,zeroIsSignificant,categoryCombo[id,name,categories[id,name,categoryOptions[id,name]]]',
            'dataElementGroups': 'id,name,code,shortName,dataElements[id]',
            'dataElementGroupSets': 'id,name,code,shortName,dataElementGroups[id]',
            'categoryOptionCombos': 'id,name,code,categoryOptions[id]',
            'categories': 'id,name,code,dataDimensionType,categoryOptions[id,name,code]',
            'categoryCombos': 'id,name,code,categories[id]',
            'categoryOptions': 'id,name,code,startDate,endDate'
        }
        
        try:
            for resource, fields in endpoints.items():
                logger.info(f"Fetching {resource}...")
                
                # Pagination handling could be added here if needed, 
                # but for metadata usually paging=false is used for smaller instances 
                # or we iterate pages. For simplicity and speed on typical metadata, 
                # we'll try paging=false first.
                
                params = {
                    'fields': fields,
                    'paging': 'false'
                }
                
                response = self.session.get(urljoin(self.url, resource), params=params)
                response.raise_for_status()
                
                data = response.json()
                if resource in data:
                    metadata[resource] = data[resource]
                else:
                    logger.warning(f"Resource {resource} not found in response")
            
            return True, metadata, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching metadata: {e}")
            return False, {}, str(e)

    def push_data_values(self, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
        """
        Sends data values to DHIS2.
        Args:
            payload: The data payload (must contain 'dataValues' list)
        Returns:
            (success, response_json, error_message)
        """
        try:
            # Check if payload has dataValues
            if 'dataValues' not in payload:
                return False, {}, "Payload must contain 'dataValues'"
                
            # Use dataValueSets endpoint
            url = urljoin(self.url, 'dataValueSets')
            
            logger.info(f"Pushing {len(payload['dataValues'])} data values to {url}")
            
            response = self.session.post(url, json=payload)
            
            # DHIS2 returns 200 even for partial imports, so we check the response body
            # But 4xx/5xx are definite errors
            if response.status_code >= 400:
                logger.error(f"DHIS2 push failed: {response.status_code} - {response.text}")
                return False, {}, f"HTTP {response.status_code}: {response.text}"
                
            response_data = response.json()
            
            # Check import summary
            status = response_data.get('status')
            if status == 'ERROR':
                return False, response_data, "Import returned ERROR status"
                
            return True, response_data, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error pushing data: {e}")
            return False, {}, str(e)
