"""Probe the documented DNG Module Structure API (jazz.net forum 272284).

Recipe:
  1. GET <module>/structure with DOORS-RP-Request-Type: public 2.0
  2. Modify structure (add/remove j.0:Binding entries)
  3. PUT back with If-Match: <etag>
  4. Server returns 202 + task tracker URL
  5. Poll task tracker until oslc_auto:state != inProgress

If this works, we close the module-binding gap end-to-end without
any of the ReqIF mess.
"""
import sys, os, json, time, re
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

# Headers per IBM's ELM-Python-Client examples/dn_simple_modulestructure.py
# (Critical: remove OSLC-Core-Version and Configuration-Context — they
# conflict with vvc.configuration on the structure endpoint.)
def structure_headers(stream_url, *, with_etag=None, content_type=None):
    h = {
        "Accept": "application/rdf+xml",
        "DoorsRP-Request-Type": "public 2.0",
        "vvc.configuration": stream_url,
    }
    if with_etag:
        h["If-Match"] = with_etag
    if content_type:
        h["Content-Type"] = content_type
    return h

# Discover the GCM stream URL up front
def _discover_stream(client, project_url):
    r = client.session.get(project_url, headers={"Accept": "application/rdf+xml"}, timeout=20)
    comp = re.search(r'oslc_config:component\s+rdf:resource="([^"]+)"', r.text)
    # services.xml may not have it — fetch one module to discover
    return comp.group(1) if comp else None

# Override: we'll set HEADERS_GET inline below once we have the stream URL

# ── Setup: fresh module + 3 reqs (as before) ──────────────────
run = time.strftime("%H%M%S")
mod = c.create_module(project_url, f"StructAPI-{run}")
mod_url = mod["url"]
print(f"Module:  {mod_url}")

# Discover GCM stream by reading the freshly-created module's component
mod_rdf = c.session.get(mod_url, headers={"Accept": "application/rdf+xml"}, timeout=20).text
comp_match = re.search(r'oslc_config:component\s+rdf:resource="([^"]+)"', mod_rdf)
component_url = comp_match.group(1) if comp_match else None
cfg = c.session.get(f"{component_url}/configurations",
                     headers={"Accept": "application/rdf+xml"}, timeout=20)
stream_match = re.search(r'rdfs:member\s+rdf:resource="([^"]+)"', cfg.text)
stream_url = stream_match.group(1) if stream_match else None
print(f"Component: {component_url}")
print(f"Stream:    {stream_url}\n")
HEADERS_GET = structure_headers(stream_url)
shapes = c.get_artifact_shapes(project_url)
shape = next(s["url"] for s in shapes if s["name"].lower() == "system requirement")
folder = c.find_folder(project_url, "Struct API Probe") or c.create_folder(project_url, "Struct API Probe")
req_urls = []
for i in range(1, 4):
    r = c.create_requirement(
        project_url=project_url,
        title=f"Struct API Req {i} ({run})",
        content=f"Body of structure-API requirement {i}.",
        shape_url=shape, folder_url=folder["url"],
    )
    req_urls.append(r["url"])
    print(f"Req {i}:   {r['url']}")

# ── 1. GET module with the magic header ───────────────────────
print(f"\n[1] GET module URL with DOORS-RP-Request-Type header")
r = c.session.get(mod_url, headers=HEADERS_GET, timeout=20)
print(f"  status: {r.status_code}, bytes: {len(r.content)}")
# Look for any "*:structure" reference (namespace prefix is generated, not fixed)
struct_match = re.search(r'(?:j\.\d+|module|jazz_rm):structure\s+rdf:resource="([^"]+)"', r.text)
if not struct_match:
    # Fall back to plain `/structure"` URL match
    alt = re.search(r'rdf:resource="(https://[^"]+/structure)"', r.text)
    if alt:
        struct_match = alt
if not struct_match:
    print("  NO :structure reference found — header may not have triggered the new view.")
    print(f"  First 1000 chars:")
    print(r.text[:1000])
    # Try alternative: look for any /structure reference
    alt = re.search(r'rdf:resource="(https://[^"]+/structure)"', r.text)
    if alt:
        struct_url = alt.group(1)
        print(f"  Found /structure URL via alt regex: {struct_url}")
    else:
        print("  No /structure reference at all — header probably ineffective on this server.")
        sys.exit(1)
else:
    struct_url = struct_match.group(1)
    print(f"  structure URL: {struct_url}")

# ── 2. GET the structure resource ─────────────────────────────
print(f"\n[2] GET structure URL")
r2 = c.session.get(struct_url, headers=HEADERS_GET, timeout=20)
etag = r2.headers.get("ETag")
print(f"  status: {r2.status_code}, bytes: {len(r2.content)}, ETag: {etag!r}")
print(f"\n--- structure RDF (first 1500 chars) ---")
print(r2.text[:1500])
print(f"\n--- structure RDF (last 500 chars) ---")
print(r2.text[-500:])

# ── 3. Discover the GCM component (we need it for new bindings) ─
comp_match = re.search(r'oslc_config:component\s+rdf:resource="([^"]+)"', r2.text)
component_url = comp_match.group(1) if comp_match else None
print(f"\n  GCM component: {component_url}")

# ── 4. Build a modified structure adding our 3 requirements ───
# Strategy: take the existing structure body verbatim and inject
# new <j.0:Binding> children inside the <j.0:childBindings> Collection
# of the root binding (the one whose rdf:about == structure URL).
ns_decl = ' xmlns:j.0="http://jazz.net/ns/rm/dng/module#"'

new_bindings_xml = ""
for i, req_url in enumerate(req_urls, start=1):
    # Critical: each Binding needs rdf:about="<structure_url>#N" — the
    # server uses this fragment ID to generate a stable binding URI.
    # Pattern from IBM ELM-Python-Client examples/dn_simple_modulestructure.py:261.
    binding_id = f"{struct_url}#{i}"
    new_bindings_xml += f'''    <j.0:Binding rdf:about="{binding_id}">
      <oslc_config:component rdf:resource="{component_url}"/>
      <j.0:boundArtifact rdf:resource="{req_url}"/>
      <j.0:module rdf:resource="{mod_url}"/>
      <j.0:childBindings rdf:resource="http://www.w3.org/1999/02/22-rdf-syntax-ns#nil"/>
    </j.0:Binding>
'''

body = r2.text
# Two cases:
#   A) Empty module: <j.0:childBindings rdf:resource=".../#nil"/> — self-closing nil
#   B) Populated module: <j.0:childBindings rdf:parseType="Collection">…</j.0:childBindings>
nil_pat = re.compile(r'<j\.0:childBindings\s+rdf:resource="[^"]*#nil"\s*/>', re.DOTALL)
collection_open = '<j.0:childBindings rdf:parseType="Collection">'

if nil_pat.search(body):
    # Replace the nil-self-closing with a populated Collection
    replacement = (collection_open + "\n"
                   + new_bindings_xml
                   + "  </j.0:childBindings>")
    new_body = nil_pat.sub(replacement, body, count=1)
elif '</j.0:childBindings>' in body:
    # Insert into an existing Collection
    new_body = body.replace('</j.0:childBindings>',
                            new_bindings_xml + '</j.0:childBindings>',
                            1)
else:
    print("\n  ERROR: could not find childBindings (neither nil nor Collection)")
    sys.exit(1)

print(f"\n  --- Modified structure body (first 1500 chars) ---")
print(new_body[:1500])

# ── 5. PUT the structure back ─────────────────────────────────
print(f"\n[3] PUT modified structure with If-Match")
put_headers = structure_headers(stream_url, with_etag=etag,
                                 content_type="application/rdf+xml")
put_resp = c.session.put(struct_url,
                          data=new_body.encode("utf-8"),
                          headers=put_headers,
                          timeout=30,
                          allow_redirects=False)
print(f"  status: {put_resp.status_code}")
location = put_resp.headers.get("Location")
print(f"  Location: {location}")
if put_resp.status_code != 202:
    print(f"  body: {put_resp.text[:1500]}")
    sys.exit(1)

# ── 6. Poll the task tracker ──────────────────────────────────
print(f"\n[4] Poll task tracker {location}")
poll_headers = {"Accept": "application/rdf+xml"}
deadline = time.time() + 30
verdict = None
while time.time() < deadline:
    pr = c.session.get(location, headers=poll_headers, timeout=15)
    state_match = re.search(r'oslc_auto:state\s+rdf:resource="([^"]+)"', pr.text)
    verdict_match = re.search(r'oslc_auto:verdict\s+rdf:resource="([^"]+)"', pr.text)
    state = state_match.group(1) if state_match else None
    verdict = verdict_match.group(1) if verdict_match else None
    print(f"  state={state}  verdict={verdict}")
    if state and 'inProgress' not in state and verdict and 'unavailable' not in verdict:
        break
    time.sleep(1.5)

# ── 7. Verify by re-fetching module with old (uses-style) header ─
print(f"\n[5] Verify — re-fetch module with default Accept and look for our reqs")
verify = c.session.get(mod_url,
                        headers={"Accept": "application/rdf+xml", "OSLC-Core-Version": "2.0"},
                        timeout=20)
uses_in_module = re.findall(r'oslc_rm:uses\s+rdf:resource="([^"]+)"', verify.text)
print(f"  module now has {len(uses_in_module)} oslc_rm:uses entries")
# Are our reqs referenced (possibly indirectly via Binding)?
# The module's oslc_rm:uses points to BI_ binding artifacts. The bindings'
# boundArtifact points back to our TX_ reqs. So the TX URLs may not appear
# in the module's RDF directly — re-fetch the structure to confirm.
verify_struct = c.session.get(struct_url, headers=HEADERS_GET, timeout=20)
bindings_in_struct = re.findall(r'j\.0:boundArtifact\s+rdf:resource="([^"]+)"', verify_struct.text)
print(f"  structure has {len(bindings_in_struct)} boundArtifact entries")
ok = all(u in bindings_in_struct for u in req_urls)
print(f"  All {len(req_urls)} requested reqs bound: {ok}")
if ok:
    print(f"\nSUCCESS — module {mod_url} now contains all {len(req_urls)} requirements.")
else:
    print(f"\nMissed: {[u for u in req_urls if u not in bindings_in_struct]}")
print(f"\nView in DNG: {mod_url}")
