"""
DOORS Next Client for IBM Bob Integration
Connects to IBM DOORS Next and pulls requirements
"""

import os
import requests
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv
import xml.etree.ElementTree as ET


class DOORSNextClient:
    """Client for interacting with IBM DOORS Next (DNG) API"""
    
    def __init__(self, base_url: str, username: str, password: str, project: str):
        """
        Initialize DOORS Next client
        
        Args:
            base_url: DOORS Next server URL (e.g., https://your-doors-server.com/rm)
            username: Your DOORS Next username
            password: Your DOORS Next password
            project: Project area name
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.project = project
        self.session = requests.Session()
        self._authenticated = False
        
    @classmethod
    def from_env(cls):
        """Create client from environment variables"""
        load_dotenv()
        
        base_url = os.getenv('DOORS_URL')
        username = os.getenv('DOORS_USERNAME')
        password = os.getenv('DOORS_PASSWORD')
        project = os.getenv('DOORS_PROJECT')
        
        if not all([base_url, username, password, project]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set DOORS_URL, DOORS_USERNAME, DOORS_PASSWORD, and DOORS_PROJECT in .env file"
            )
        
        return cls(base_url, username, password, project)
    
    def authenticate(self) -> bool:
        """
        Authenticate with DOORS Next using basic authentication
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Use basic authentication
            self.session.auth = (self.username, self.password)
            
            # Add required header to prevent OIDC redirect
            self.session.headers.update({
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            # Test authentication by accessing rootservices
            response = self.session.get(f"{self.base_url}/rootservices")
            
            if response.status_code == 200:
                self._authenticated = True
                print("✅ Successfully authenticated with DOORS Next")
                return True
            else:
                print(f"❌ Authentication failed (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False
    
    def _ensure_authenticated(self):
        """Ensure we're authenticated before making requests"""
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Failed to authenticate with DOORS Next")
    
    def list_projects(self) -> List[Dict]:
        """
        List all DOORS Next RM projects from the OSLC catalog
        
        Returns:
            List of project dictionaries with 'title', 'id', and 'url'
        """
        self._ensure_authenticated()
        
        try:
            # Query the OSLC RM service provider catalog
            url = f"{self.base_url}/oslc_rm/catalog"
            headers = {
                'Accept': 'application/rdf+xml',
                'OSLC-Core-Version': '2.0'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                
                # Define namespaces
                namespaces = {
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'dcterms': 'http://purl.org/dc/terms/',
                    'oslc': 'http://open-services.net/ns/core#'
                }
                
                projects = []
                # Find all ServiceProvider entries
                for sp in root.findall('.//oslc:ServiceProvider', namespaces):
                    title_elem = sp.find('dcterms:title', namespaces)
                    about_attr = sp.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
                    
                    if title_elem is not None and about_attr:
                        project = {
                            'title': title_elem.text,
                            'url': about_attr,
                            'id': about_attr.split('/')[-1] if '/' in about_attr else about_attr
                        }
                        projects.append(project)
                
                print(f"✅ Found {len(projects)} projects")
                return projects
            else:
                print(f"❌ Failed to list projects: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error listing projects: {str(e)}")
            return []
    
    def get_modules(self, project_url: str, recursive: bool = True) -> List[Dict]:
        """
        Get modules/folders from a specific project using OSLC Folder Query Capability
        
        This method uses the OSLC folder query capability to find all modules and folders
        in a DOORS Next project. It can optionally retrieve nested folders recursively.
        
        Args:
            project_url: The project's service provider URL (e.g., from list_projects())
            recursive: If True, recursively fetch all nested folders (default: True)
            
        Returns:
            List of module dictionaries with 'title', 'id', 'url', 'level', 'created', 'modified'
            
        Example:
            projects = client.list_projects()
            bob_project = projects[6]  # Project 7 (0-indexed)
            modules = client.get_modules(bob_project['url'])
        """
        self._ensure_authenticated()
        
        try:
            # Define namespaces for XML parsing
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dcterms': 'http://purl.org/dc/terms/',
                'oslc': 'http://open-services.net/ns/core#',
                'nav': 'http://jazz.net/ns/rm/navigation#',
                'rm': 'http://www.ibm.com/xmlns/rdm/rdf/'
            }
            
            headers = {
                'Accept': 'application/rdf+xml',
                'OSLC-Core-Version': '2.0'
            }
            
            # Convert service provider URL to project area URL
            # From: https://.../rm/oslc_rm/_gtcOgCR9EfG2I_bh4PQ0Og/services.xml
            # To:   https://.../rm/process/project-areas/_gtcOgCR9EfG2I_bh4PQ0Og
            project_area_url = project_url.replace('/oslc_rm/', '/process/project-areas/').replace('/services.xml', '')
            
            # Query for root folder using OSLC Folder Query Capability
            query_url = f"{self.base_url}/folders"
            params = {
                'oslc.where': f'public_rm:parent={project_area_url}',
                'oslc.select': '*'
            }
            
            response = self.session.get(query_url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get modules: {response.status_code}")
                return []
            
            all_modules = []
            root = ET.fromstring(response.content)
            
            # Find root folder(s)
            for item in root.findall('.//{http://jazz.net/ns/rm/navigation#}folder', namespaces):
                title_elem = item.find('dcterms:title', namespaces)
                about_attr = item.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
                identifier_elem = item.find('dcterms:identifier', namespaces)
                created_elem = item.find('dcterms:created', namespaces)
                modified_elem = item.find('dcterms:modified', namespaces)
                
                if title_elem is not None and about_attr:
                    module = {
                        'title': title_elem.text,
                        'url': about_attr,
                        'id': identifier_elem.text if identifier_elem is not None else about_attr.split('/')[-1],
                        'created': created_elem.text if created_elem is not None else '',
                        'modified': modified_elem.text if modified_elem is not None else '',
                        'level': 0
                    }
                    all_modules.append(module)
                    
                    # Recursively get child folders if requested
                    if recursive:
                        children = self._get_child_folders(about_attr, namespaces, level=1)
                        all_modules.extend(children)
            
            print(f"✅ Found {len(all_modules)} modules/folders")
            return all_modules
            
        except Exception as e:
            print(f"❌ Error getting modules: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_child_folders(self, parent_url: str, namespaces: dict, level: int = 1) -> List[Dict]:
        """
        Recursively get all child folders of a parent folder
        
        Args:
            parent_url: URL of the parent folder
            namespaces: XML namespaces for parsing
            level: Current nesting level (for display purposes)
            
        Returns:
            List of child folder dictionaries
        """
        folders = []
        
        try:
            query_url = f"{self.base_url}/folders"
            params = {
                'oslc.where': f'nav:parent={parent_url}',
                'oslc.select': '*',
                'oslc.pageSize': '100'
            }
            
            headers = {
                'Accept': 'application/rdf+xml',
                'OSLC-Core-Version': '2.0'
            }
            
            response = self.session.get(query_url, params=params, headers=headers)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                for item in root.findall('.//{http://jazz.net/ns/rm/navigation#}folder', namespaces):
                    title_elem = item.find('dcterms:title', namespaces)
                    about_attr = item.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
                    identifier_elem = item.find('dcterms:identifier', namespaces)
                    created_elem = item.find('dcterms:created', namespaces)
                    modified_elem = item.find('dcterms:modified', namespaces)
                    
                    if title_elem is not None and about_attr:
                        folder = {
                            'title': title_elem.text,
                            'url': about_attr,
                            'id': identifier_elem.text if identifier_elem is not None else about_attr.split('/')[-1],
                            'created': created_elem.text if created_elem is not None else '',
                            'modified': modified_elem.text if modified_elem is not None else '',
                            'level': level
                        }
                        folders.append(folder)
                        
                        # Recursively get children
                        children = self._get_child_folders(about_attr, namespaces, level + 1)
                        folders.extend(children)
        
        except Exception as e:
            # Silently continue if we can't get children
            pass
        
        return folders
    def get_requirements_from_project(self, project_url: str) -> List[Dict]:
        """
        Get requirements from a specific project using the Reportable API
        
        Args:
            project_url: The project's service provider URL
            
        Returns:
            List of requirement dictionaries with 'id', 'title', 'description', 'status'
        """
        self._ensure_authenticated()
        
        try:
            # Try the publish/resources endpoint without resourceType first
            url = f"{self.base_url}/publish/resources"
            params = {
                'projectURL': project_url
            }
            
            headers = {
                'Accept': 'application/xml',
                'OSLC-Core-Version': '2.0'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get requirements (attempt 1): {response.status_code}")
                
                # Try with resourceType parameter
                params['resourceType'] = 'Requirement'
                response = self.session.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    print(f"❌ Failed to get requirements (attempt 2): {response.status_code}")
                    
                    # Try with oslc.where filter instead
                    params = {
                        'projectURL': project_url,
                        'oslc.where': 'rdf:type=<http://open-services.net/ns/rm#Requirement>'
                    }
                    response = self.session.get(url, params=params, headers=headers)
                    
                    if response.status_code != 200:
                        print(f"❌ Failed to get requirements (attempt 3): {response.status_code}")
                        print(f"Response: {response.text[:200]}")
                        return []
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dcterms': 'http://purl.org/dc/terms/',
                'oslc': 'http://open-services.net/ns/core#',
                'rm': 'http://www.ibm.com/xmlns/rdm/rdf/',
                'oslc_rm': 'http://open-services.net/ns/rm#'
            }
            
            requirements = []
            
            # Find all requirement entries
            for req_elem in root.findall('.//oslc_rm:Requirement', namespaces):
                # Extract requirement details
                req_id = req_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
                
                # Get title
                title_elem = req_elem.find('dcterms:title', namespaces)
                title = title_elem.text if title_elem is not None and title_elem.text else 'Untitled'
                
                # Get description
                desc_elem = req_elem.find('dcterms:description', namespaces)
                description = desc_elem.text if desc_elem is not None and desc_elem.text else ''
                
                # Get identifier (requirement ID like REQ-123)
                identifier_elem = req_elem.find('dcterms:identifier', namespaces)
                identifier = identifier_elem.text if identifier_elem is not None and identifier_elem.text else ''
                
                # Get status
                status_elem = req_elem.find('oslc_rm:status', namespaces)
                status = status_elem.text if status_elem is not None and status_elem.text else 'Unknown'
                
                # Get type
                type_elem = req_elem.find('dcterms:type', namespaces)
                req_type = type_elem.text if type_elem is not None and type_elem.text else 'Requirement'
                
                requirement = {
                    'id': identifier or req_id.split('/')[-1] if req_id else 'N/A',
                    'title': title,
                    'description': description,
                    'status': status,
                    'type': req_type,
                    'url': req_id
                }
                
                requirements.append(requirement)
            
            print(f"✅ Found {len(requirements)} requirements")
            return requirements
            
        except Exception as e:
            print(f"❌ Error getting requirements: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_requirements_from_module(self, module_id: str) -> List[Dict]:
        """
        Get requirements from a specific module using the Reportable API
        
        Args:
            module_id: The module's ID (e.g., '985621')
            
        Returns:
            List of requirement dictionaries with 'id', 'title', 'description', 'status'
        """
        self._ensure_authenticated()
        
        try:
            # Use the Reportable API to get resources from a specific module
            url = f"{self.base_url}/publish/resources"
            params = {
                'moduleURI': f"{self.base_url}/resources/{module_id}",
                'resourceType': 'Requirement'
            }
            
            headers = {
                'Accept': 'application/xml',
                'OSLC-Core-Version': '2.0'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get requirements from module: {response.status_code}")
                # Try without resourceType
                params = {
                    'moduleURI': f"{self.base_url}/resources/{module_id}"
                }
                response = self.session.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    print(f"❌ Failed again: {response.status_code}")
                    print(f"Response: {response.text[:300]}")
                    return []
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dcterms': 'http://purl.org/dc/terms/',
                'oslc': 'http://open-services.net/ns/core#',
                'rm': 'http://www.ibm.com/xmlns/rdm/rdf/',
                'oslc_rm': 'http://open-services.net/ns/rm#'
            }
            
            requirements = []
            
            # Find all requirement entries
            for req_elem in root.findall('.//oslc_rm:Requirement', namespaces):
                # Extract requirement details
                req_id = req_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
                
                # Get title
                title_elem = req_elem.find('dcterms:title', namespaces)
                title = title_elem.text if title_elem is not None and title_elem.text else 'Untitled'
                
                # Get description
                desc_elem = req_elem.find('dcterms:description', namespaces)
                description = desc_elem.text if desc_elem is not None and desc_elem.text else ''
                
                # Get identifier (requirement ID like REQ-123)
                identifier_elem = req_elem.find('dcterms:identifier', namespaces)
                identifier = identifier_elem.text if identifier_elem is not None and identifier_elem.text else ''
                
                # Get status
                status_elem = req_elem.find('oslc_rm:status', namespaces)
                status = status_elem.text if status_elem is not None and status_elem.text else 'Unknown'
                
                # Get type
                type_elem = req_elem.find('dcterms:type', namespaces)
                req_type = type_elem.text if type_elem is not None and type_elem.text else 'Requirement'
                
                requirement = {
                    'id': identifier or req_id.split('/')[-1] if req_id else 'N/A',
                    'title': title,
                    'description': description,
                    'status': status,
                    'type': req_type,
                    'url': req_id
                }
                
                requirements.append(requirement)
            
            print(f"✅ Found {len(requirements)} requirements in module")
            return requirements
            
        except Exception as e:
            print(f"❌ Error getting requirements from module: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def count_artifacts_in_module(self, module_id: str) -> int:
        """
        Count the number of artifacts (requirements) in a specific module
        
        Args:
            module_id: The module's ID (e.g., 'FR_gy59UCR9EfG2I_bh4PQ0Og')
            
        Returns:
            Count of artifacts in the module
        """
        self._ensure_authenticated()
        
        try:
            # Use the Reportable API to count resources in a module
            url = f"{self.base_url}/publish/resources"
            params = {
                'moduleURI': f"{self.base_url}/resources/{module_id}"
            }
            
            headers = {
                'Accept': 'application/xml',
                'OSLC-Core-Version': '2.0'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"⚠️ Could not count artifacts in module {module_id}: {response.status_code}")
                return 0
            
            # Parse XML response to count requirements
            root = ET.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dcterms': 'http://purl.org/dc/terms/',
                'oslc': 'http://open-services.net/ns/core#',
                'rm': 'http://www.ibm.com/xmlns/rdm/rdf/',
                'oslc_rm': 'http://open-services.net/ns/rm#'
            }
            
            # Count all requirement entries
            requirements = root.findall('.//oslc_rm:Requirement', namespaces)
            count = len(requirements)
            
            return count
            
        except Exception as e:
            print(f"⚠️ Error counting artifacts in module: {str(e)}")
            return 0
    
    def get_module_with_artifact_count(self, module_url: str) -> Dict:
        """
        Get module information including artifact count
        
        Args:
            module_url: The module's URL
            
        Returns:
            Dictionary with module info including artifact count
        """
        self._ensure_authenticated()
        
        try:
            headers = {
                'Accept': 'application/rdf+xml',
                'OSLC-Core-Version': '2.0'
            }
            
            response = self.session.get(module_url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            # Parse module metadata
            root = ET.fromstring(response.content)
            
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dcterms': 'http://purl.org/dc/terms/',
                'nav': 'http://jazz.net/ns/rm/navigation#'
            }
            
            folder = root.find('.//{http://jazz.net/ns/rm/navigation#}folder', namespaces)
            
            if folder is None:
                return None
            
            # Extract module info
            title_elem = folder.find('dcterms:title', namespaces)
            desc_elem = folder.find('dcterms:description', namespaces)
            about_attr = folder.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
            
            module_id = about_attr.split('/')[-1] if about_attr else None
            
            if not module_id:
                return None
            
            # Get artifact count
            artifact_count = self.count_artifacts_in_module(module_id)
            
            module_info = {
                'title': title_elem.text if title_elem is not None else 'Untitled',
                'description': desc_elem.text if desc_elem is not None else '',
                'url': about_attr,
                'id': module_id,
                'artifact_count': artifact_count
            }
            
            return module_info
            
        except Exception as e:
            print(f"⚠️ Error getting module with artifact count: {str(e)}")
            return None
    
    def get_project_info(self) -> Dict:
        """
        Get information about the project
        
        Returns:
            Dictionary with project information
        """
        self._ensure_authenticated()
        
        try:
            # Get project areas
            url = f"{self.base_url}/process/project-areas"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'message': 'Connected to DOORS Next',
                    'project': self.project
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Failed to get project info: {response.status_code}'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error: {str(e)}'
            }
    
    def get_requirements(self, 
                        status: Optional[str] = None,
                        req_type: Optional[str] = None,
                        limit: int = 100) -> List[Dict]:
        """
        Get requirements from DOORS Next
        
        Args:
            status: Filter by status (e.g., 'Approved', 'In Progress')
            req_type: Filter by type (e.g., 'Functional', 'Non-Functional')
            limit: Maximum number of requirements to return
            
        Returns:
            List of requirement dictionaries
        """
        self._ensure_authenticated()
        
        try:
            # Build OSLC query
            url = f"{self.base_url}/oslc_rm/query"
            
            # Basic query parameters
            params = {
                'oslc.select': '*',
                'oslc.pageSize': limit
            }
            
            # Add filters if specified
            where_clauses = []
            if status:
                where_clauses.append(f'dcterms:status="{status}"')
            if req_type:
                where_clauses.append(f'dcterms:type="{req_type}"')
            
            if where_clauses:
                params['oslc.where'] = ' and '.join(where_clauses)
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                # Parse response (could be JSON or XML depending on Accept header)
                requirements = self._parse_requirements_response(response.text)
                print(f"✅ Retrieved {len(requirements)} requirements")
                return requirements
            else:
                print(f"❌ Failed to get requirements: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting requirements: {str(e)}")
            return []
    
    def get_requirement_by_id(self, req_id: str) -> Optional[Dict]:
        """
        Get a specific requirement by ID
        
        Args:
            req_id: Requirement ID (e.g., 'REQ-1234')
            
        Returns:
            Requirement dictionary or None if not found
        """
        self._ensure_authenticated()
        
        try:
            url = f"{self.base_url}/resources/{req_id}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                requirement = self._parse_requirement(response.text)
                print(f"✅ Retrieved requirement {req_id}")
                return requirement
            else:
                print(f"❌ Requirement {req_id} not found")
                return None
                
        except Exception as e:
            print(f"❌ Error getting requirement: {str(e)}")
            return None
    
    def update_requirement_status(self, req_id: str, status: str, comment: str = "") -> bool:
        """
        Update the status of a requirement
        
        Args:
            req_id: Requirement ID
            status: New status (e.g., 'In Progress', 'Implemented')
            comment: Optional comment about the change
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_authenticated()
        
        try:
            url = f"{self.base_url}/resources/{req_id}"
            
            data = {
                'status': status,
                'comment': comment
            }
            
            response = self.session.put(url, json=data)
            
            if response.status_code in [200, 204]:
                print(f"✅ Updated {req_id} status to '{status}'")
                return True
            else:
                print(f"❌ Failed to update status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating status: {str(e)}")
            return False
    
    def _parse_requirements_response(self, response_text: str) -> List[Dict]:
        """Parse requirements from API response"""
        # This is a simplified parser - actual implementation depends on response format
        requirements = []
        
        try:
            # Try parsing as JSON first
            data = json.loads(response_text)
            if isinstance(data, list):
                requirements = data
            elif isinstance(data, dict) and 'results' in data:
                requirements = data['results']
        except json.JSONDecodeError:
            # If not JSON, might be XML - parse accordingly
            try:
                root = ET.fromstring(response_text)
                # Parse XML structure (simplified)
                for item in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    req = self._parse_xml_requirement(item)
                    if req:
                        requirements.append(req)
            except ET.ParseError:
                print("⚠️ Could not parse response format")
        
        return requirements
    
    def _parse_requirement(self, response_text: str) -> Optional[Dict]:
        """Parse a single requirement from API response"""
        try:
            # Try JSON first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try XML
            try:
                root = ET.fromstring(response_text)
                return self._parse_xml_requirement(root)
            except ET.ParseError:
                return None
    
    def _parse_xml_requirement(self, element: ET.Element) -> Dict:
        """Parse requirement from XML element"""
        # Simplified XML parsing - adjust based on actual DOORS Next XML structure
        req = {
            'id': element.findtext('.//{http://purl.org/dc/terms/}identifier', ''),
            'title': element.findtext('.//{http://purl.org/dc/terms/}title', ''),
            'description': element.findtext('.//{http://purl.org/dc/terms/}description', ''),
            'status': element.findtext('.//{http://purl.org/dc/terms/}status', ''),
            'type': element.findtext('.//{http://purl.org/dc/terms/}type', ''),
        }
        return req
    
    def export_to_json(self, requirements: List[Dict], filename: str = "requirements.json"):
        """Export requirements to JSON file"""
        with open(filename, 'w') as f:
            json.dump(requirements, f, indent=2)
        print(f"✅ Exported {len(requirements)} requirements to {filename}")
    
    def export_to_markdown(self, requirements: List[Dict], filename: str = "requirements.md"):
        """Export requirements to Markdown file"""
        with open(filename, 'w') as f:
            f.write("# Requirements from DOORS Next\n\n")
            for req in requirements:
                f.write(f"## {req.get('id', 'N/A')}: {req.get('title', 'Untitled')}\n\n")
                f.write(f"**Status:** {req.get('status', 'N/A')}\n\n")
                f.write(f"**Type:** {req.get('type', 'N/A')}\n\n")
                f.write(f"**Description:**\n{req.get('description', 'No description')}\n\n")
                
                if 'acceptance_criteria' in req:
                    f.write("**Acceptance Criteria:**\n")
                    for criterion in req['acceptance_criteria']:
                        f.write(f"- {criterion}\n")
                    f.write("\n")
                
                f.write("---\n\n")
        
        print(f"✅ Exported {len(requirements)} requirements to {filename}")
    
    def get_modules_reportable_api(self, project_area_id: str) -> List[Dict]:
        """
        Get modules from a project using the Reportable REST API
        
        Args:
            project_area_id: The project area ID (e.g., '_gtcOgCR9EfG2I_bh4PQ0Og')
            
        Returns:
            List of module dictionaries with 'title', 'id', 'url', 'format'
        """
        self._ensure_authenticated()
        
        try:
            # Build project area URL
            project_area_url = f"{self.base_url}/process/project-areas/{project_area_id}"
            
            # Use Reportable REST API to get modules
            url = f"{self.base_url}/publish/modules"
            params = {
                'projectURI': project_area_url
            }
            
            headers = {
                'Accept': 'application/xml',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get modules: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Define namespaces for Reportable REST API
            namespaces = {
                'ds': 'http://jazz.net/xmlns/prod/jazz/reporting/datasource/1.0/',
                'rrm': 'http://www.ibm.com/xmlns/rdm/reportablerest/',
                'attribute': 'http://jazz.net/xmlns/prod/jazz/reporting/attribute/1.0/'
            }
            
            modules = []
            
            # Find all artifacts
            for artifact in root.findall('.//ds:artifact', namespaces):
                # Get format to identify modules
                format_elem = artifact.find('rrm:format', namespaces)
                format_value = format_elem.text if format_elem is not None else ''
                
                # Only include modules (format="Module")
                if format_value == 'Module':
                    # Get title
                    title_elem = artifact.find('rrm:title', namespaces)
                    title = title_elem.text if title_elem is not None else 'Untitled'
                    
                    # Get identifier
                    identifier_elem = artifact.find('rrm:identifier', namespaces)
                    identifier = identifier_elem.text if identifier_elem is not None else ''
                    
                    # Get URL
                    url_elem = artifact.find('rrm:url', namespaces)
                    module_url = url_elem.text if url_elem is not None else ''
                    
                    # Get modified date
                    modified_elem = artifact.find('rrm:modified', namespaces)
                    modified = modified_elem.text if modified_elem is not None else ''
                    
                    module = {
                        'title': title,
                        'id': identifier,
                        'url': module_url,
                        'format': format_value,
                        'modified': modified
                    }
                    modules.append(module)
            
            print(f"✅ Found {len(modules)} modules using Reportable REST API")
            return modules
            
        except Exception as e:
            print(f"❌ Error getting modules: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_requirements_reportable_api(self, module_url: str) -> List[Dict]:
        """
        Get requirements from a module using the Reportable REST API
        
        Args:
            module_url: The module's URL
            
        Returns:
            List of requirement dictionaries with all attributes including custom ones
        """
        self._ensure_authenticated()
        
        try:
            # Use Reportable REST API to get resources from module
            url = f"{self.base_url}/publish/resources"
            params = {
                'moduleURI': module_url
            }
            
            headers = {
                'Accept': 'application/xml',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get requirements: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Define namespaces for Reportable REST API (actual response format)
            namespaces = {
                'ds': 'http://jazz.net/xmlns/alm/rm/datasource/v0.1',
                'rrm': 'http://www.ibm.com/xmlns/rrm/1.0/',
                'attribute': 'http://jazz.net/xmlns/alm/rm/attribute/v0.1'
            }
            
            requirements = []
            
            # Find all artifacts
            for artifact in root.findall('.//ds:artifact', namespaces):
                # Get basic attributes
                title_elem = artifact.find('rrm:title', namespaces)
                title = title_elem.text if title_elem is not None else 'Untitled'
                
                identifier_elem = artifact.find('rrm:identifier', namespaces)
                identifier = identifier_elem.text if identifier_elem is not None else ''
                
                description_elem = artifact.find('rrm:description', namespaces)
                description = description_elem.text if description_elem is not None else ''
                
                about_elem = artifact.find('rrm:about', namespaces)
                req_url = about_elem.text if about_elem is not None else ''
                
                format_elem = artifact.find('rrm:format', namespaces)
                format_value = format_elem.text if format_elem is not None else ''
                
                # Get modified date from collaboration section
                modified_elem = artifact.find('.//rrm:modified', namespaces)
                modified = modified_elem.text if modified_elem is not None else ''
                
                # Get created date
                created_elem = artifact.find('.//rrm:created', namespaces)
                created = created_elem.text if created_elem is not None else ''
                
                # Get creator
                creator_elem = artifact.find('.//rrm:creator/rrm:title', namespaces)
                creator = creator_elem.text if creator_elem is not None else ''
                
                # Extract custom attributes from objectType
                custom_attributes = {}
                object_type_elem = artifact.find('.//attribute:objectType', namespaces)
                if object_type_elem is not None:
                    custom_attributes['objectType'] = object_type_elem.get('{http://jazz.net/xmlns/alm/rm/attribute/v0.1}name', '')
                
                # Look for other custom attributes
                for attr in artifact.findall('.//attribute:attribute', namespaces):
                    attr_name = attr.get('{http://jazz.net/xmlns/alm/rm/attribute/v0.1}name', '')
                    attr_value = attr.text if attr.text else ''
                    if attr_name:
                        custom_attributes[attr_name] = attr_value
                
                requirement = {
                    'id': identifier,
                    'title': title,
                    'description': description,
                    'url': req_url,
                    'format': format_value,
                    'modified': modified,
                    'created': created,
                    'creator': creator,
                    'custom_attributes': custom_attributes
                }
                
                requirements.append(requirement)
            
            print(f"✅ Found {len(requirements)} requirements in module")
            return requirements
            
        except Exception as e:
            print(f"❌ Error getting requirements: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_requirements_from_project(self, project_area_id: str) -> Dict:
        """
        Get all requirements from all modules in a project using Reportable REST API
        
        Args:
            project_area_id: The project area ID (e.g., '_gtcOgCR9EfG2I_bh4PQ0Og')
            
        Returns:
            Dictionary with modules and their requirements
        """
        self._ensure_authenticated()
        
        try:
            # Get all modules
            print(f"\n📁 Fetching modules from project {project_area_id}...")
            modules = self.get_modules_reportable_api(project_area_id)
            
            if not modules:
                print("❌ No modules found")
                return {'modules': [], 'total_requirements': 0}
            
            print(f"\n📋 Found {len(modules)} modules. Fetching requirements...\n")
            
            result = {
                'project_area_id': project_area_id,
                'modules': [],
                'total_requirements': 0
            }
            
            # Get requirements from each module
            for i, module in enumerate(modules, 1):
                print(f"[{i}/{len(modules)}] Processing: {module['title']}")
                
                requirements = self.get_requirements_reportable_api(module['url'])
                
                module_data = {
                    'title': module['title'],
                    'id': module['id'],
                    'url': module['url'],
                    'modified': module['modified'],
                    'requirement_count': len(requirements),
                    'requirements': requirements
                }
                
                result['modules'].append(module_data)
                result['total_requirements'] += len(requirements)
                
                print(f"   ✓ {len(requirements)} requirements found\n")
            
            print(f"\n✅ Complete! Total: {result['total_requirements']} requirements from {len(modules)} modules")
            return result
            
        except Exception as e:
            print(f"❌ Error getting all requirements: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'modules': [], 'total_requirements': 0}


if __name__ == "__main__":
    # Example usage
    print("DOORS Next Client - Example Usage\n")
    
    try:
        # Create client from environment variables
        client = DOORSNextClient.from_env()
        
        # Test connection
        print("Testing connection...")
        info = client.get_project_info()
        print(f"Status: {info['status']}")
        print(f"Message: {info['message']}\n")
        
        # Get requirements
        print("Fetching requirements...")
        requirements = client.get_requirements(status="Approved", limit=10)
        
        if requirements:
            print(f"\nFound {len(requirements)} requirements:")
            for req in requirements[:5]:  # Show first 5
                print(f"  - {req.get('id', 'N/A')}: {req.get('title', 'Untitled')}")
            
            # Export to files
            client.export_to_json(requirements)
            client.export_to_markdown(requirements)
        else:
            print("No requirements found or unable to retrieve them")
            print("\nThis might be because:")
            print("1. The API endpoints need adjustment for your DOORS Next version")
            print("2. You need different authentication")
            print("3. The project name is incorrect")
            print("\nPlease check with your DOORS Next administrator")
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease create a .env file with:")
        print("DOORS_URL=https://your-doors-server.com/rm")
        print("DOORS_USERNAME=your_username")
        print("DOORS_PASSWORD=your_password")
        print("DOORS_PROJECT=YourProject")
    except Exception as e:
        print(f"❌ Error: {e}")

# Made with Bob
