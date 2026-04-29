"""Dig into the four promising endpoints from probe 18:
  /rm/import/csv         (403 — exists)
  /rm/import-sessions    (untried)
  /rm/type-import-sessions (factory advertised)
  /rm/publish/csv        (400 — real error)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from doors_client import DOORSNextClient

c = DOORSNextClient(
    os.environ.get("ELM_URL") or os.environ["DOORS_URL"],
    os.environ.get("ELM_USERNAME") or os.environ["DOORS_USERNAME"],
    os.environ.get("ELM_PASSWORD") or os.environ["DOORS_PASSWORD"],
)
c.authenticate()

with open(os.path.join(os.path.dirname(__file__), "SANDBOX_PROJECTS.json")) as f:
    sandbox = json.load(f)
project_url = sandbox["dng"]["services_url"]
project_area_id = sandbox["dng"]["project_area_id"]
project_area_url = f"{c.server_root}/rm/process/project-areas/{project_area_id}"

def probe(label, method, url, **kwargs):
    print(f"\n--- {label} ---")
    print(f"  {method} {url}")
    fn = getattr(c.session, method.lower())
    try:
        r = fn(url, allow_redirects=False, timeout=15, **kwargs)
        print(f"  status: {r.status_code}")
        print(f"  content-type: {r.headers.get('content-type', '')}")
        for h in ('location', 'allow', 'accept-post', 'oslc-core-version', 'www-authenticate'):
            v = r.headers.get(h)
            if v:
                print(f"  {h}: {v}")
        body = r.text[:1500]
        if body.strip():
            print(f"  body: {body}")
    except Exception as e:
        print(f"  ERR: {e}")

# Endpoint 1: /rm/import/csv with various params
probe("1a /rm/import/csv  GET no params", "GET",
      f"{c.server_root}/rm/import/csv")
probe("1b /rm/import/csv  GET with projectURL", "GET",
      f"{c.server_root}/rm/import/csv?projectURL={project_area_url}")
probe("1c /rm/import/csv  OPTIONS", "OPTIONS",
      f"{c.server_root}/rm/import/csv")

# Endpoint 2: /rm/import-sessions
probe("2 /rm/import-sessions  GET", "GET",
      f"{c.server_root}/rm/import-sessions")
probe("2b /rm/import-sessions  POST empty", "POST",
      f"{c.server_root}/rm/import-sessions",
      data=b'',
      headers={"Content-Type": "application/rdf+xml",
               "Accept": "application/rdf+xml",
               "OSLC-Core-Version": "2.0"})

# Endpoint 3: type-import-sessions (factory)
probe("3 /rm/type-import-sessions  POST empty", "POST",
      f"{c.server_root}/rm/type-import-sessions",
      data=b'',
      headers={"Content-Type": "application/rdf+xml",
               "Accept": "application/rdf+xml",
               "OSLC-Core-Version": "2.0"})

# Endpoint 4: /rm/publish/csv
probe("4a /rm/publish/csv  no params (we saw 400)", "GET",
      f"{c.server_root}/rm/publish/csv")
probe("4b /rm/publish/csv  with projectURI", "GET",
      f"{c.server_root}/rm/publish/csv?projectURI={project_area_url}")
probe("4c /rm/publish/csv  with projectURL", "GET",
      f"{c.server_root}/rm/publish/csv?projectURL={project_area_url}")

# Bonus: try /rm/publish/import and /rm/import sessions discovery
probe("5a /rm/publish/import  with projectURI", "GET",
      f"{c.server_root}/rm/publish/import?projectURI={project_area_url}")
probe("5b /rm/dataIngester  GET", "GET",
      f"{c.server_root}/rm/dataIngester")
probe("5c /rm/web/_amw/insert  GET", "GET",
      f"{c.server_root}/rm/web/_amw/insert")
