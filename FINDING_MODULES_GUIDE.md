# Guide: Finding Modules in DOORS Next Projects

## Overview
This guide documents the process for finding all modules/folders in a DOORS Next project using the OSLC API.

## Method: OSLC Folder Query Capability

### Key Discovery
The successful approach uses the **OSLC Folder Query Capability** which is available in the service provider document for each project.

### API Endpoint
```
GET https://{server}/rm/folders
```

### Query Parameters
- `oslc.where`: Filter expression to find folders
- `oslc.select`: Fields to return (use `*` for all)
- `oslc.pageSize`: Number of results per page (optional)

### Process Steps

#### 1. Get Project Information
First, list all projects to find the target project:

```python
from doors_client import DOORSNextClient

client = DOORSNextClient.from_env()
client.authenticate()

projects = client.list_projects()
# Find your project (e.g., "Project Bob - Brett (Requirements)")
```

#### 2. Convert Service Provider URL to Project Area URL
The project URL from `list_projects()` is a service provider URL that needs conversion:

**From:**
```
https://your-doors-server.com/rm/oslc_rm/_gtcOgCR9EfG2I_bh4PQ0Og/services.xml
```

**To:**
```
https://your-doors-server.com/rm/process/project-areas/_gtcOgCR9EfG2I_bh4PQ0Og
```

**Conversion logic:**
```python
project_area_url = project_url.replace('/oslc_rm/', '/process/project-areas/').replace('/services.xml', '')
```

#### 3. Query for Root Folders
Query the folders endpoint with the project area as the parent:

```python
query_url = f"{base_url}/folders"
params = {
    'oslc.where': f'public_rm:parent={project_area_url}',
    'oslc.select': '*'
}
headers = {
    'Accept': 'application/rdf+xml',
    'OSLC-Core-Version': '2.0'
}

response = session.get(query_url, params=params, headers=headers)
```

#### 4. Parse XML Response
The response is in RDF/XML format. Parse it to extract folder information:

```python
import xml.etree.ElementTree as ET

root = ET.fromstring(response.content)

namespaces = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dcterms': 'http://purl.org/dc/terms/',
    'nav': 'http://jazz.net/ns/rm/navigation#'
}

for item in root.findall('.//{http://jazz.net/ns/rm/navigation#}folder', namespaces):
    title = item.find('dcterms:title', namespaces).text
    url = item.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
    identifier = item.find('dcterms:identifier', namespaces).text
    # ... extract other fields
```

#### 5. Recursively Get Child Folders (Optional)
To get nested folders, query again using each folder's URL as the parent:

```python
params = {
    'oslc.where': f'nav:parent={folder_url}',
    'oslc.select': '*',
    'oslc.pageSize': '100'
}
```

## Using the Updated `doors_client.py`

The `get_modules()` method has been updated to implement this process:

```python
from doors_client import DOORSNextClient

# Initialize client
client = DOORSNextClient.from_env()
client.authenticate()

# List projects
projects = client.list_projects()

# Find your project (e.g., project 7 is at index 6)
project = projects[6]  # "Project Bob - Brett (Requirements)"

# Get all modules (recursive by default)
modules = client.get_modules(project['url'])

# Get only top-level modules (non-recursive)
modules = client.get_modules(project['url'], recursive=False)

# Display results
for module in modules:
    indent = "  " * module['level']
    print(f"{indent}- {module['title']} (ID: {module['id']})")
```

## Module Data Structure

Each module dictionary contains:

```python
{
    'title': 'Module Name',           # Display name
    'id': 'FR_gy59UCR9EfG2I_bh4PQ0Og', # Unique identifier
    'url': 'https://...',              # Full resource URL
    'created': '2024-01-15T10:30:00Z', # Creation timestamp (if available)
    'modified': '2024-03-20T14:45:00Z',# Last modified (if available)
    'level': 0                         # Nesting level (0 = root)
}
```

## Example: Project 7 (Project Bob - Brett)

For "Project Bob - Brett (Requirements)" project:

```python
# Result from get_modules()
[
    {
        'title': 'root',
        'id': 'FR_gy59UCR9EfG2I_bh4PQ0Og',
        'url': 'https://your-doors-server.com/rm/folders/FR_gy59UCR9EfG2I_bh4PQ0Og',
        'level': 0
    }
    # ... any child folders would appear here with level > 0
]
```

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check authentication and project permissions
2. **400 Bad Request**: Verify the project URL format and query parameters
3. **Empty Results**: Project may have no modules, or they're organized differently

### Alternative Endpoints (Less Reliable)

These endpoints were tested but are less reliable:
- `/publish/modules?projectURL=...` - Returns 400 for some projects
- `/folders?projectURL=...` - Returns 403 (permission issues)
- `/views?projectURL=...` - Returns 403

### Known Working Module IDs

For Project Bob - Brett:
- Root folder: `FR_gy59UCR9EfG2I_bh4PQ0Og`
- Module 985621: Known to exist (from previous tests)

## References

- OSLC RM Specification: https://open-services.net/ns/rm/
- Jazz.net Navigation Namespace: http://jazz.net/ns/rm/navigation#
- DOORS Next API Documentation: IBM Jazz.net

## Script Examples

See these files for working examples:
- `find_bob_modules_oslc.py` - OSLC query approach (successful)
- `find_all_bob_modules_recursive.py` - Recursive folder traversal
- `test_bob_project.py` - Basic project access

## Summary

**The key to finding modules in DOORS Next:**
1. Use the OSLC Folder Query Capability (`/folders` endpoint)
2. Convert service provider URL to project area URL
3. Query with `oslc.where=public_rm:parent={project_area_url}`
4. Parse RDF/XML response for folder elements
5. Recursively query child folders using `nav:parent={folder_url}`

This approach is now implemented in the `get_modules()` method of `doors_client.py` for reusable access.