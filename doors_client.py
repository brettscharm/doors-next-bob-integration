"""
DOORS Next Generation API Client
Connects to IBM DOORS Next via OSLC and Reportable REST APIs
"""

import os
import csv
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dotenv import load_dotenv
import requests


class DOORSNextClient:
    """Client for IBM DOORS Next Generation"""

    # Reportable REST API namespace variants (differ across DNG versions)
    _NS_VARIANTS = [
        {
            'ds': 'http://jazz.net/xmlns/prod/jazz/reporting/datasource/1.0/',
            'rrm': 'http://www.ibm.com/xmlns/rdm/reportablerest/',
        },
        {
            'ds': 'http://jazz.net/xmlns/alm/rm/datasource/v0.1',
            'rrm': 'http://www.ibm.com/xmlns/rrm/1.0/',
        },
    ]

    # OSLC namespaces (stable across versions)
    _NS_OSLC = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dcterms': 'http://purl.org/dc/terms/',
        'oslc': 'http://open-services.net/ns/core#',
        'oslc_rm': 'http://open-services.net/ns/rm#',
        'nav': 'http://jazz.net/ns/rm/navigation#',
    }

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._authenticated = False

    @classmethod
    def from_env(cls):
        """Create client from .env file"""
        load_dotenv()
        base_url = os.getenv('DOORS_URL')
        username = os.getenv('DOORS_USERNAME')
        password = os.getenv('DOORS_PASSWORD')
        if not all([base_url, username, password]):
            raise ValueError(
                "Missing environment variables. "
                "Set DOORS_URL, DOORS_USERNAME, and DOORS_PASSWORD in your .env file."
            )
        return cls(base_url, username, password)

    def authenticate(self) -> bool:
        """Authenticate with DOORS Next using Basic Auth"""
        try:
            self.session.auth = (self.username, self.password)
            self.session.headers.update({
                'X-Requested-With': 'XMLHttpRequest'  # Prevents OIDC redirect
            })
            resp = self.session.get(f"{self.base_url}/rootservices")
            if resp.status_code == 200:
                self._authenticated = True
                return True
            return False
        except Exception:
            return False

    def _ensure_auth(self):
        """Ensure authenticated before making requests"""
        if not self._authenticated:
            if not self.authenticate():
                raise ConnectionError("Failed to authenticate with DOORS Next")

    def _extract_project_area_id(self, service_provider_url: str) -> str:
        """Extract project area ID from service provider URL.

        Input:  https://server/rm/oslc_rm/_abc123/services.xml
        Output: _abc123
        """
        url = service_provider_url.replace('/services.xml', '')
        return url.split('/')[-1]

    # ── Projects ──────────────────────────────────────────────

    def list_projects(self) -> List[Dict]:
        """List all DNG projects from the OSLC catalog"""
        self._ensure_auth()
        try:
            resp = self.session.get(
                f"{self.base_url}/oslc_rm/catalog",
                headers={
                    'Accept': 'application/rdf+xml',
                    'OSLC-Core-Version': '2.0',
                }
            )
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.content)
            ns = self._NS_OSLC
            projects = []

            for sp in root.findall('.//oslc:ServiceProvider', ns):
                title_el = sp.find('dcterms:title', ns)
                about = sp.get(f'{{{ns["rdf"]}}}about')
                if title_el is not None and about:
                    projects.append({
                        'title': title_el.text,
                        'url': about,
                        'id': about.split('/')[-1] if '/' in about else about,
                    })

            return projects
        except Exception:
            return []

    # ── Modules ───────────────────────────────────────────────

    def get_modules(self, project_url: str) -> List[Dict]:
        """Get modules from a project.

        Tries the Reportable REST API first (returns actual DNG Modules),
        then falls back to OSLC folder query (returns all folders).
        """
        self._ensure_auth()
        project_area_id = self._extract_project_area_id(project_url)

        # Primary: Reportable REST API (returns real modules)
        modules = self._get_modules_reportable(project_area_id)
        if modules:
            return modules

        # Fallback: OSLC folder query
        return self._get_modules_oslc(project_url)

    def _get_modules_reportable(self, project_area_id: str) -> List[Dict]:
        """Get modules via the Reportable REST API (publish/modules endpoint)"""
        project_area_url = f"{self.base_url}/process/project-areas/{project_area_id}"

        # Try different parameter names (varies by DNG version)
        for param_name in ['projectURI', 'projectURL']:
            try:
                resp = self.session.get(
                    f"{self.base_url}/publish/modules",
                    params={param_name: project_area_url},
                    headers={
                        'Accept': 'application/xml',
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                )
                if resp.status_code != 200:
                    continue

                root = ET.fromstring(resp.content)

                # Try each namespace variant
                for ns_variant in self._NS_VARIANTS:
                    modules = self._parse_modules_xml(root, ns_variant)
                    if modules:
                        return modules

                # If we got a 200 but no modules parsed, try namespace-agnostic parsing
                modules = self._parse_modules_agnostic(root)
                if modules:
                    return modules

            except Exception:
                continue

        return []

    def _parse_modules_xml(self, root: ET.Element, ns: dict) -> List[Dict]:
        """Parse modules from Reportable REST API XML with specific namespaces"""
        modules = []
        for artifact in root.findall(f'.//{{{ns["ds"]}}}artifact'):
            fmt_el = artifact.find(f'{{{ns["rrm"]}}}format')
            fmt = fmt_el.text if fmt_el is not None else ''

            # Only include actual Modules (not other artifact types)
            if fmt == 'Module':
                title_el = artifact.find(f'{{{ns["rrm"]}}}title')
                id_el = artifact.find(f'{{{ns["rrm"]}}}identifier')
                url_el = artifact.find(f'{{{ns["rrm"]}}}url')
                mod_el = artifact.find(f'{{{ns["rrm"]}}}modified')

                modules.append({
                    'title': title_el.text if title_el is not None else 'Untitled',
                    'id': id_el.text if id_el is not None else '',
                    'url': url_el.text if url_el is not None else '',
                    'modified': mod_el.text if mod_el is not None else '',
                    'source': 'reportable_api',
                })

        return modules

    def _parse_modules_agnostic(self, root: ET.Element) -> List[Dict]:
        """Namespace-agnostic fallback: look for elements by local name"""
        modules = []
        for elem in root.iter():
            local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if local == 'artifact':
                fmt = ''
                title = 'Untitled'
                identifier = ''
                url = ''
                modified = ''

                for child in elem.iter():
                    child_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child_local == 'format' and child.text:
                        fmt = child.text
                    elif child_local == 'title' and child.text:
                        title = child.text
                    elif child_local == 'identifier' and child.text:
                        identifier = child.text
                    elif child_local == 'url' and child.text:
                        url = child.text
                    elif child_local == 'modified' and child.text:
                        modified = child.text

                if fmt == 'Module':
                    modules.append({
                        'title': title,
                        'id': identifier,
                        'url': url,
                        'modified': modified,
                        'source': 'reportable_api',
                    })

        return modules

    def _get_modules_oslc(self, project_url: str) -> List[Dict]:
        """Fallback: Get folders via OSLC folder query capability"""
        try:
            ns = self._NS_OSLC
            project_area_url = project_url.replace(
                '/oslc_rm/', '/process/project-areas/'
            ).replace('/services.xml', '')

            resp = self.session.get(
                f"{self.base_url}/folders",
                params={
                    'oslc.where': f'public_rm:parent={project_area_url}',
                    'oslc.select': '*',
                },
                headers={
                    'Accept': 'application/rdf+xml',
                    'OSLC-Core-Version': '2.0',
                }
            )
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.content)
            modules = []

            for item in root.findall(f'.//{{{ns["nav"]}}}folder'):
                title_el = item.find('dcterms:title', ns)
                about = item.get(f'{{{ns["rdf"]}}}about')
                id_el = item.find('dcterms:identifier', ns)

                if title_el is not None and about:
                    modules.append({
                        'title': title_el.text,
                        'url': about,
                        'id': id_el.text if id_el is not None else about.split('/')[-1],
                        'modified': '',
                        'source': 'oslc_folders',
                    })

                    # Get children recursively
                    children = self._get_child_folders(about, level=1)
                    modules.extend(children)

            return modules
        except Exception:
            return []

    def _get_child_folders(self, parent_url: str, level: int = 1) -> List[Dict]:
        """Recursively get child folders"""
        ns = self._NS_OSLC
        folders = []
        try:
            resp = self.session.get(
                f"{self.base_url}/folders",
                params={
                    'oslc.where': f'nav:parent={parent_url}',
                    'oslc.select': '*',
                    'oslc.pageSize': '100',
                },
                headers={
                    'Accept': 'application/rdf+xml',
                    'OSLC-Core-Version': '2.0',
                }
            )
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.content)
            for item in root.findall(f'.//{{{ns["nav"]}}}folder'):
                title_el = item.find('dcterms:title', ns)
                about = item.get(f'{{{ns["rdf"]}}}about')
                id_el = item.find('dcterms:identifier', ns)

                if title_el is not None and about:
                    folders.append({
                        'title': title_el.text,
                        'url': about,
                        'id': id_el.text if id_el is not None else about.split('/')[-1],
                        'modified': '',
                        'level': level,
                        'source': 'oslc_folders',
                    })
                    folders.extend(self._get_child_folders(about, level + 1))
        except Exception:
            pass
        return folders

    # ── Requirements ──────────────────────────────────────────

    def get_module_requirements(self, module_url: str) -> List[Dict]:
        """Get requirements from a specific module by its URL.

        Uses the Reportable REST API (publish/resources?moduleURI=...).
        Falls back to OSLC parsing if Reportable namespaces don't match.
        """
        self._ensure_auth()

        # Try both parameter names (varies by DNG version)
        for param_name in ['moduleURI', 'moduleURL']:
            try:
                resp = self.session.get(
                    f"{self.base_url}/publish/resources",
                    params={param_name: module_url},
                    headers={
                        'Accept': 'application/xml',
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                )
                if resp.status_code != 200:
                    continue

                root = ET.fromstring(resp.content)

                # Try Reportable REST API namespaces
                for ns_variant in self._NS_VARIANTS:
                    reqs = self._parse_reqs_reportable(root, ns_variant)
                    if reqs:
                        return reqs

                # Try namespace-agnostic parsing
                reqs = self._parse_reqs_agnostic(root)
                if reqs:
                    return reqs

                # Try OSLC namespaces as final fallback
                reqs = self._parse_reqs_oslc(root)
                if reqs:
                    return reqs

            except Exception:
                continue

        return []

    def _parse_reqs_reportable(self, root: ET.Element, ns: dict) -> List[Dict]:
        """Parse requirements from Reportable REST API XML"""
        reqs = []
        for artifact in root.findall(f'.//{{{ns["ds"]}}}artifact'):
            title_el = artifact.find(f'{{{ns["rrm"]}}}title')
            id_el = artifact.find(f'{{{ns["rrm"]}}}identifier')
            desc_el = artifact.find(f'{{{ns["rrm"]}}}description')
            about_el = artifact.find(f'{{{ns["rrm"]}}}about')
            fmt_el = artifact.find(f'{{{ns["rrm"]}}}format')
            modified_el = artifact.find(f'.//{{{ns["rrm"]}}}modified')
            created_el = artifact.find(f'.//{{{ns["rrm"]}}}created')

            reqs.append({
                'id': id_el.text if id_el is not None else '',
                'title': title_el.text if title_el is not None else 'Untitled',
                'description': desc_el.text if desc_el is not None else '',
                'url': about_el.text if about_el is not None else '',
                'format': fmt_el.text if fmt_el is not None else '',
                'modified': modified_el.text if modified_el is not None else '',
                'created': created_el.text if created_el is not None else '',
            })

        return reqs

    def _parse_reqs_agnostic(self, root: ET.Element) -> List[Dict]:
        """Namespace-agnostic fallback: look for artifact elements by local name"""
        reqs = []
        for elem in root.iter():
            local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if local == 'artifact':
                title = 'Untitled'
                identifier = ''
                description = ''
                about = ''
                fmt = ''
                modified = ''
                created = ''

                for child in elem.iter():
                    child_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    text = child.text or ''
                    if child_local == 'title' and text:
                        title = text
                    elif child_local == 'identifier' and text:
                        identifier = text
                    elif child_local == 'description' and text:
                        description = text
                    elif child_local == 'about' and text:
                        about = text
                    elif child_local == 'format' and text:
                        fmt = text
                    elif child_local == 'modified' and text:
                        modified = text
                    elif child_local == 'created' and text:
                        created = text

                if title != 'Untitled' or identifier:
                    reqs.append({
                        'id': identifier,
                        'title': title,
                        'description': description,
                        'url': about,
                        'format': fmt,
                        'modified': modified,
                        'created': created,
                    })

        return reqs

    def _parse_reqs_oslc(self, root: ET.Element) -> List[Dict]:
        """Fallback: Parse requirements using OSLC namespaces"""
        ns = self._NS_OSLC
        reqs = []
        for req_el in root.findall('.//oslc_rm:Requirement', ns):
            about = req_el.get(f'{{{ns["rdf"]}}}about', '')
            title_el = req_el.find('dcterms:title', ns)
            desc_el = req_el.find('dcterms:description', ns)
            id_el = req_el.find('dcterms:identifier', ns)
            status_el = req_el.find('oslc_rm:status', ns)
            type_el = req_el.find('dcterms:type', ns)

            reqs.append({
                'id': id_el.text if id_el is not None else (about.split('/')[-1] if about else ''),
                'title': title_el.text if title_el is not None else 'Untitled',
                'description': desc_el.text if desc_el is not None else '',
                'url': about,
                'format': type_el.text if type_el is not None else '',
                'modified': '',
                'created': '',
                'status': status_el.text if status_el is not None else '',
            })

        return reqs

    # ── Export ─────────────────────────────────────────────────

    def export_to_json(self, requirements: List[Dict], filepath: str):
        """Export requirements to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(requirements, f, indent=2)

    def export_to_csv(self, requirements: List[Dict], filepath: str):
        """Export requirements to CSV file"""
        if not requirements:
            return
        fields = ['id', 'title', 'description', 'url', 'format', 'modified', 'created']
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(requirements)

    def export_to_markdown(self, requirements: List[Dict], filepath: str):
        """Export requirements to Markdown file"""
        with open(filepath, 'w') as f:
            f.write("# Requirements\n\n")
            for req in requirements:
                f.write(f"## {req.get('id', 'N/A')}: {req.get('title', 'Untitled')}\n\n")
                if req.get('description'):
                    f.write(f"{req['description']}\n\n")
                if req.get('modified'):
                    f.write(f"*Last modified: {req['modified']}*\n\n")
                f.write("---\n\n")
