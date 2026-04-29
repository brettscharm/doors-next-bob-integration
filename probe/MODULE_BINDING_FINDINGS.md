# Module-Binding Investigation — Findings

## TL;DR — RESOLVED 🎉

**`create_module` works.** Module artifacts are created via
`POST /rm/requirementFactory`.

**Adding requirements to a module's structure now also works** via DNG's
**Module Structure API** — a separate writable surface from the legacy
`oslc_rm:uses` view. We discovered this from a jazz.net forum post + IBM's
own ELM-Python-Client and verified end-to-end live:

```
client.add_to_module(module_url, [req1, req2, req3])
→ {'added': 3, 'module_url': '...'}
```

The MCP tool `create_requirements` with `module_name` now auto-binds: the
requirements appear inside the module immediately, no manual drag-bind in
DNG required.

The recipe is in `doors_client.py:add_to_module` and exercised in
`probe/20_module_structure_api.py`. Below is the full investigation that
got us here, kept for future maintainers (e.g. when porting to another
DNG version).

## What works

| Operation | Status |
|---|---|
| Create a new module | ✅ `create_module` (REST factory POST) |
| Bind existing requirements to an existing module | ✅ `add_to_module` (Structure API) |
| Auto-create + bind in one call (MCP tool) | ✅ `create_requirements` with `module_name` |
| Update module title/description | ✅ standard OSLC PUT works on the module URL |
| Update individual requirements (title, body, attrs) | ✅ unaffected by the binding lockdown |

## How the Structure API works (the working recipe)

```
1. GET <module_url>
     headers: DoorsRP-Request-Type: public 2.0
              vvc.configuration: <gcm_stream_url>
   → returns RDF with a `*:structure` predicate pointing at <module_url>/structure

2. GET <module_url>/structure
     same headers
   → returns the structure RDF + ETag
   → empty modules: childBindings = rdf:nil
   → populated modules: childBindings = Collection of <j.0:Binding> entries

3. Replace nil with Collection (or splice into existing Collection):
   <j.0:childBindings rdf:parseType="Collection">
     <j.0:Binding rdf:about="<structure_url>#1">
       <oslc_config:component rdf:resource="<gcm_component>"/>
       <j.0:boundArtifact rdf:resource="<req_url>"/>
       <j.0:module rdf:resource="<module_url>"/>
       <j.0:childBindings rdf:resource="...rdf-syntax-ns#nil"/>
     </j.0:Binding>
     ... more bindings ...
   </j.0:childBindings>

4. PUT <module_url>/structure
     headers: DoorsRP-Request-Type: public 2.0
              vvc.configuration: <gcm_stream_url>
              If-Match: <etag>
              Content-Type: application/rdf+xml
   → returns 202 + Location: <task_tracker_url>

5. Poll <task_tracker_url> until oslc_auto:state ≠ inProgress
   → success: oslc_auto:verdict = passed
   → failure: oslc_auto:verdict = error (with oslc:Error inside)
```

## Three non-obvious gotchas that broke earlier probes

1. **Header is `DoorsRP-Request-Type: public 2.0`** (camelCase, no hyphen
   between Doors and RP). The jazz.net forum post had the spelling slightly
   wrong as `DOORS-RP-Request-Type` — that variant returns the legacy
   read-only view. The correct form was confirmed against IBM's
   ELM-Python-Client `examples/dn_simple_modulestructure.py:191`.

2. **`OSLC-Core-Version` and `Configuration-Context` headers MUST be
   omitted.** They conflict with `vvc.configuration` on this endpoint. The
   IBM client explicitly nulls them out at every structure-API request.

3. **Each new Binding needs `rdf:about="<structure_url>#N"`.** Without it,
   the server returns `IllegalArgumentException: invalid UUID` because it
   can't generate a stable URI for the binding. Use sequential `#1, #2, ...`
   integers — DNG mints a real UUID and replaces them.

## What was tried before the breakthrough (kept for reference)

## What I tested (live, against `Gio (Brett) (Requirements)` sandbox)

| Variant | Result |
|---|---|
| PUT exact GET bytes (no-op) | **200** ✓ |
| PUT GET bytes + `<oslc_rm:uses>` inserted via regex | 400 |
| PUT GET bytes + `<oslc_rm:uses>` inserted via ElementTree | 400 |
| PUT with `Configuration-Context: <stream URL>` header added | 400 |
| PUT after stripping `dcterms:description` (the parseType=Literal field) | 400 |
| PUT with description replaced by empty literal | 400 |
| PATCH with same modified body | 200 — **but binding did not persist** (silent no-op) |
| POST `/requirementFactory?...&moduleURI=<module>` (create-in-module) | 201 — but module's `oslc_rm:uses` still empty |
| POST `/requirementFactory?...&parent=<module>` | 403 |
| POST `/requirementFactory` with `<nav:parent rdf:resource=<module>>` | 403 |
| GET `<module_url>/structure` | 404 (no separate structure resource) |
| GET `<module_url>?_structure=true` | 200 but returns same RDF as plain GET |

## What we know about the data model

A populated module (e.g. `Word Import.docx` in `Sandbox_Requirements`)
has a flat list of `<oslc_rm:uses rdf:resource="<BI_xxx>"/>` lines, each
pointing to a `BI_*`-prefixed artifact. The `BI_*` artifacts themselves
are full `oslc_rm:Requirement` resources with title, primaryText, etc.
There is no back-reference from the binding to the module (the
relationship is held entirely on the module side).

So the *intent* — add lines to the module's RDF — is correct. DNG just
doesn't accept it as a write-shape.

## Likely causes (in order of plausibility)

1. **DNG enforces an OSLC Resource Shape on PUT** that whitelists which
   predicates can be modified. `dcterms:title`, `dcterms:description`,
   etc. are editable, but `oslc_rm:uses` is not — it's managed only via
   internal UI flows or an undocumented private endpoint.
2. **A separate "module structure" resource exists** but isn't exposed
   via the OSLC service catalog on this server version. (Some DNG
   versions expose `/rm/resources/MD_*?structureFormat=json`; this one
   doesn't.)
3. **Module bindings require ReqIF import.** The services.xml does
   advertise a `ReqIF Package Factory` — the supported path for bulk
   loading requirements *into* a module may be ReqIF, not OSLC RDF PUT.

## Pragmatic decision

Stop trying to crack the OSLC PUT. Two paths forward:

- **Short-term** (this PR): keep `create_module` exposed; have
  `create_requirements` put artifacts in a folder named after the
  requested module and tell the user to drag them into the module in
  DNG. The `add_to_module` client method stays in place but returns a
  clear "Module-structure writes are restricted on this DNG server"
  message instead of a confusing HTTP 400. Document the limitation in
  BOB.md.
- **Future-work**: implement a `import_requirements_via_reqif` tool
  that builds a minimal ReqIF package containing the requirements
  pre-bound to a module and POSTs it to the ReqIF import factory. ReqIF
  is the IBM-blessed bulk-load path and is the only documented way to
  create-and-bind in one shot.

## Final probe (B-stream): four more variants, all blocked

`probe/16_module_bind_final.py` ran four more attempts after the AI Hub
sandbox permissions were granted. None worked:

| Hypothesis | Endpoint | Result |
|---|---|---|
| H1 — DNG private UI insert action | `POST /rm/views?action=com.ibm.rdm.web.module.insertArtifact&module=…&boundArtifact=…` | **403 Forbidden** (all of POST/PUT/GET) |
| H2 — Delivery-session factory | `POST /rm/delivery-sessions` | **400** "Source or Target configuration missing" — this factory is for GCM stream-delivery, wrong tool |
| H3 — POST requirement with `nav:parent=<module URL>` | `POST /rm/requirementFactory?projectURL=…` with module as parent | **403 Forbidden** + "Content must be valid rdf+xml" |
| H4 — PUT with `vvc.configuration` query param + `Configuration-Context` header | `PUT <module-url>?vvc.configuration=<stream>` | **400** "Content must be valid rdf+xml" |

## Path A (CSV REST import) — also dead

`probe/18_csv_import_probe.py` and `probe/19_csv_endpoint_dig.py` ruled
out CSV-based REST import. Findings:

| Endpoint tested | Result |
|---|---|
| `/rm/import/csv` | **403** with `"CRRRS4142E ... requires a private header"` — first-party internal RPC endpoint, not an OSLC REST API. Same backing service the DNG UI's CSV import wizard uses, gated behind a `DoorsRP-Request-Type: private` header that only authenticated UI sessions hold. |
| `/rm/import-sessions` | 404 — no such endpoint |
| `/rm/type-import-sessions` | Exists, but accepts only type-system payloads (artifact type definitions, attribute schemas) — NOT requirement data |
| `/rm/publish/csv` and `/rm/publish/import` | 400 generic; legacy export endpoints, not import |
| `/rm/web/_amw/insert` | 200 but returns the DNG UI HTML page — it's a UI route, not an API |
| `/rm/dataIngester` and friends | 404 |

`services.xml` advertises **only ReqIF** as the import factory (no CSV
factory exists). Confirmed across 18 endpoint variants.

**Verdict: programmatic module-binding is not viable via DNG's
public REST surface on this server version (DNG 7.1.0 SR1).**
Every documented and undocumented avenue tested — OSLC PUT/PATCH,
DNG private `/rm/views` endpoint, in-flight `&moduleURI=` factory
param, CSV REST import — returns either a lockdown response or a
404. ReqIF was prototyped (probe agent attempt 2026-04-29) but the
DNG ReqIF importer responded with `"userMimeType property cannot
be found"` and a stack of additional DNG-specific shape
requirements; the round-trip update story is also messy (ReqIF
re-import doesn't merge into an existing module on standard DNG —
it creates a new Specification each time, leaving the user to
delete the old one). Net assessment: ReqIF closes the *create*
case but opens new churn around updates.

## What we ship instead

The MCP exposes `create_module` (which creates the module artifact
correctly) and `create_requirements` (which creates artifacts in a
folder). The user binds them in the DNG UI in ~30 seconds:

1. Open the module created by `create_module`.
2. Click the "+" / "Insert" button.
3. Choose "Existing artifacts" and pick from the folder created by
   `create_requirements`.
4. Confirm.

This is a one-time UI step per module. Subsequent in-place edits
(title, primary text, attributes, links) all work via the OSLC
write tools — only the *children list* of a module is locked.

## Probes that produced these findings

- `probe/02_inspect_module.py` — original module RDF + `_structure=true` etc.
- `probe/03_inspect_binding_and_factory.py` — binding artifact + services.xml
- `probe/09_diag_400_put.py` — PUT with regex injection (400)
- `probe/10_diag_400_xml_proper.py` — PUT with ElementTree (400)
- `probe/11_diag_put_roundtrip.py` — confirmed no-op PUT works (200)
- `probe/12_diag_minimal_edit.py` — five PUT variants + PATCH (PATCH 200, no persist)
- `probe/13_create_in_module.py` — `&moduleURI=` factory param (created req, no binding)
- `probe/14_diag_strip_description.py` — strip Literal description (still 400)
- `probe/16_module_bind_final.py` — H1/H2/H3/H4 above (all blocked)
- `probe/18_csv_import_probe.py` — surveyed services.xml + 21 candidate URLs for CSV import
- `probe/19_csv_endpoint_dig.py` — deep-probed the 4 promising endpoints (all dead-ended)
