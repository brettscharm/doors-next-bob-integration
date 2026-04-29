"""Try header variants until the /structure view turns on.

The forum says exactly `DOORS-RP-Request-Type: public 2.0` (lowercase
"public", space, "2.0"). Our first try got back the legacy oslc_rm:uses
view, suggesting the header didn't trigger the right code path.

Possibilities:
  1. Header name is case-sensitive (DoorsRP-Request-Type variants)
  2. Server requires Configuration-Context for GCM-enabled projects
  3. Server requires OSLC-Core-Version: 2.0 alongside
  4. The fresh empty module has no /structure yet — try a populated module
"""
import sys, os, json, re
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

# Use a known-populated module from Sandbox_Requirements (Word Import.docx, 255 children)
populated_mod = "https://goblue.clm.ibmcloud.com/rm/resources/MD_vRKmsA_cEeuxf_ZBvFABOw"

# Discover the GCM stream URL for that project's component
r = c.session.get(populated_mod, headers={"Accept": "application/rdf+xml"}, timeout=20)
comp = re.search(r'oslc_config:component\s+rdf:resource="([^"]+)"', r.text)
comp_url = comp.group(1) if comp else None
stream_url = None
if comp_url:
    cfg = c.session.get(f"{comp_url}/configurations",
                         headers={"Accept": "application/rdf+xml"}, timeout=20)
    s = re.search(r'rdfs:member\s+rdf:resource="([^"]+)"', cfg.text)
    if s:
        stream_url = s.group(1)
print(f"GCM component: {comp_url}")
print(f"GCM stream:    {stream_url}\n")

variants = [
    # 1. Forum's exact recipe
    ("forum exact", {"Accept": "application/rdf+xml",
                     "DOORS-RP-Request-Type": "public 2.0"}),
    # 2. Camelcase variant
    ("camel", {"Accept": "application/rdf+xml",
               "DoorsRP-Request-Type": "public 2.0"}),
    # 3. With OSLC-Core-Version
    ("forum + oslc", {"Accept": "application/rdf+xml",
                      "DOORS-RP-Request-Type": "public 2.0",
                      "OSLC-Core-Version": "2.0"}),
    # 4. With Configuration-Context (GCM)
    ("forum + config", {"Accept": "application/rdf+xml",
                        "DOORS-RP-Request-Type": "public 2.0",
                        "Configuration-Context": stream_url} if stream_url else None),
    # 5. With vvc.configuration query param
    ("forum + vvc", {"Accept": "application/rdf+xml",
                     "DOORS-RP-Request-Type": "public 2.0"},
     f"?vvc.configuration={stream_url}" if stream_url else ""),
    # 6. Header value variants
    ("public lowercase no version", {"Accept": "application/rdf+xml",
                                      "DOORS-RP-Request-Type": "public"}),
    ("public capital", {"Accept": "application/rdf+xml",
                        "DOORS-RP-Request-Type": "Public 2.0"}),
    # 7. Try the /structure URL directly (skipping discovery)
    ("direct /structure", {"Accept": "application/rdf+xml",
                            "DOORS-RP-Request-Type": "public 2.0"},
     "/structure"),
    # 8. Try /structure with OSLC-Core-Version
    ("/structure + oslc", {"Accept": "application/rdf+xml",
                            "DOORS-RP-Request-Type": "public 2.0",
                            "OSLC-Core-Version": "2.0"},
     "/structure"),
]

for v in variants:
    if v is None or v[1] is None:
        continue
    if len(v) == 3:
        label, headers, suffix = v
    else:
        label, headers = v
        suffix = ""
    url = populated_mod + suffix
    try:
        r = c.session.get(url, headers=headers, timeout=15, allow_redirects=False)
        text = r.text
        has_structure_ref = bool(re.search(r'(?:j\.\d+|module):structure', text)) or '/structure"' in text
        # Look for j.0 / j.1 namespace prefix declarations
        has_j_ns = bool(re.search(r'xmlns:j\.\d+="http://jazz\.net/ns/rm/dng/module', text))
        is_binding_view = '<j.0:Binding' in text or 'j.0:childBindings' in text
        marker = "★ STRUCTURE" if has_structure_ref or is_binding_view else (
                 "j.0 ns"     if has_j_ns else
                 "(legacy)"   if 'oslc_rm:uses' in text else
                 "?")
        print(f"  [{r.status_code}] {label:35s} {suffix or '(module url)':15s}  {marker}  bytes={len(text)}")
        # if structure-y, dump first 800
        if has_structure_ref or is_binding_view:
            print(f"      ↳ {text[:800]}")
            print()
    except Exception as e:
        print(f"  [ERR] {label}: {e}")

# Also: try POSTing OPTIONS to see what verbs the structure URL supports
print("\n--- OPTIONS on /structure ---")
try:
    r = c.session.options(populated_mod + "/structure",
                           headers={"DOORS-RP-Request-Type": "public 2.0"}, timeout=15)
    print(f"  status: {r.status_code}")
    print(f"  Allow: {r.headers.get('Allow')}")
    for h in ('accept-patch', 'oslc-core-version', 'www-authenticate'):
        v = r.headers.get(h)
        if v: print(f"  {h}: {v}")
except Exception as e:
    print(f"  ERR: {e}")
