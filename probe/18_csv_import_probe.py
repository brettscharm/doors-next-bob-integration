"""Probe A — does this DNG server expose a REST endpoint for CSV import?

Three checks:
  1. Re-scan services.xml for any factory whose title contains
     csv / import / data / batch / ingester
  2. GET rootservices.xml to see if it advertises a non-OSLC import
     capability we missed
  3. Direct-probe likely URL patterns from IBM's RM REST docs and
     community-discovered endpoints. We use HEAD/GET so we don't
     trip any side effects on real endpoints.

If anything looks promising, we then attempt a real CSV POST against
the AI Hub sandbox.
"""
import sys, os, json, re, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from doors_client import DOORSNextClient

c = DOORSNextClient(os.environ.get("ELM_URL") or os.environ["DOORS_URL"],
                    os.environ.get("ELM_USERNAME") or os.environ["DOORS_USERNAME"],
                    os.environ.get("ELM_PASSWORD") or os.environ["DOORS_PASSWORD"])
c.authenticate()

# ── 1. Scan services.xml for import-related factories ─────────
print("=== [1] services.xml — all factories whose title hints at import ===\n")
with open(os.path.join(os.path.dirname(__file__), "services.xml")) as f:
    services_xml = f.read()

factories = re.findall(r'<oslc:CreationFactory>(.*?)</oslc:CreationFactory>',
                       services_xml, re.DOTALL)
hits = []
for fac in factories:
    title_m = re.search(r'<dcterms:title[^>]*>(.*?)</dcterms:title>', fac, re.DOTALL)
    creation_m = re.search(r'oslc:creation rdf:resource="([^"]+)"', fac)
    title = title_m.group(1).strip() if title_m else "?"
    creation = creation_m.group(1) if creation_m else "?"
    keywords = ['csv', 'import', 'data', 'batch', 'ingester', 'session',
                'feed', 'load', 'reqif', 'definition']
    if any(kw in title.lower() for kw in keywords):
        print(f"  • {title}")
        print(f"      → {creation}")
        hits.append({"title": title, "creation": creation})

print(f"\nFound {len(hits)} import-shaped factories in services.xml\n")

# ── 2. Rootservices for non-OSLC capability advertisements ────
print("=== [2] rootservices.xml ===\n")
r = c.session.get(
    f"{c.base_url}/rootservices",
    headers={"Accept": "application/rdf+xml"},
    timeout=20,
)
print(f"  status: {r.status_code} bytes: {len(r.content)}")
# Look for any property name containing 'import' or 'csv'
import_props = re.findall(r'<([a-zA-Z_]+:[a-zA-Z_]+)[^>]*(?:rdf:resource|rdf:about)="([^"]+)"',
                          r.text)
seen = set()
for prop, url in import_props:
    if any(kw in (prop + url).lower() for kw in ['import', 'csv', 'ingester']):
        key = (prop, url)
        if key not in seen:
            seen.add(key)
            print(f"  • {prop}  →  {url}")

# ── 3. Direct probe likely endpoints ──────────────────────────
print("\n=== [3] direct probe of plausible CSV/import endpoints ===\n")
endpoints_to_try = [
    # Common DNG/RM CSV-related guesses
    "/rm/import/csv",
    "/rm/csv/import",
    "/rm/csv_oslc/import",
    "/rm/import_oslc/import",
    "/rm/import-sessions",
    "/rm/import-session",
    "/rm/admin/import",
    "/rm/admin/csv",
    "/rm/admin/import-csv",
    # DNG private "ingester" endpoints
    "/rm/dataIngester",
    "/rm/ingest",
    "/rm/dataloader",
    # Some IBM-documented DNG admin URLs
    "/rm/admin/cmd",
    "/rm/_admin/csvImport",
    # Reportable REST family — sometimes accepts POSTs for ingestion
    "/rm/publish/csv",
    "/rm/publish/import",
    # IBM RM 7.0+ "Module Operations"
    "/rm/com.ibm.rdm.web/csvImport",
    "/rm/com.ibm.rdm.web/importCSV",
    # OSLC RM extension some servers expose
    "/rm/oslc/import",
    "/rm/oslc/csv",
    # The reqif factory — for comparison (we know this works)
    "/rm/reqif_oslc/import",
]
results = []
for path in endpoints_to_try:
    url = c.base_url.rstrip('/') + path[3:] if path.startswith('/rm') else c.server_root + path
    # Adjust: our endpoints already start with /rm. base_url already ends in /rm.
    full = c.server_root + path
    try:
        # Try HEAD first; some servers reject HEAD on POST endpoints, so fall
        # back to GET
        head = c.session.head(full, timeout=8, allow_redirects=False)
        status = head.status_code
        if status in (404, 405):
            r2 = c.session.get(full, timeout=8, allow_redirects=False)
            status = r2.status_code
            ct = r2.headers.get("content-type", "")
            length = len(r2.content)
        else:
            ct = head.headers.get("content-type", "")
            length = int(head.headers.get("content-length", 0) or 0)
        marker = "OK" if status == 200 else (
                 "405 (POST-only)" if status == 405 else
                 "401/403 (auth-gated, exists)" if status in (401, 403) else
                 f"{status}")
        if status not in (404, 0):
            print(f"  [{marker}] {path}  ct={ct[:30]} len={length}")
        results.append({"path": path, "status": status, "ct": ct, "length": length})
    except Exception as e:
        print(f"  [ERR] {path}: {e}")

# ── 4. Save raw results ───────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "csv_import_probe_results.json")
with open(out, "w") as f:
    json.dump({"factories_in_services": hits, "endpoint_results": results},
              f, indent=2)

# ── 5. Summary ────────────────────────────────────────────────
print("\n=== Summary ===")
print(f"Promising factories (services.xml):  {len([h for h in hits if 'csv' in h['title'].lower() or 'import' in h['title'].lower()])}")
non_404 = [r for r in results if r["status"] not in (404, 0)]
print(f"Non-404 endpoints (direct probe):    {len(non_404)}")
if non_404:
    print("Worth investigating further:")
    for r in non_404:
        print(f"  • {r['path']}  status={r['status']}")
print(f"\nFull dump: {out}")
