# Module-Binding Investigation — Findings

## TL;DR

**`create_module` works.** Creating a new module artifact (RequirementCollection)
via POST to `/rm/requirementFactory` succeeds and returns a valid `MD_*` URL.

**Programmatically adding requirements to a module's `oslc_rm:uses` does NOT
work on this DNG server.** Every variant of PUT/PATCH against the module
returned `400 CRRRS6401E "Error parsing content. Content must be valid rdf+xml"`
even though the body is valid RDF/XML by every parser I tried, AND a no-op
PUT (echoing the GET response back) returns `200 OK`.

This is a server-side restriction, not a client bug. DNG locks down
module-structure manipulation; the standard OSLC RM 2.0 PUT pattern that
works for `oslc_rm:Requirement` does not work for `oslc_rm:RequirementCollection`
when the only change is added `oslc_rm:uses` triples.

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

**Verdict: ReqIF import is the only documented programmatic bulk-load
path on this server.** The OSLC PUT/PATCH route, the DNG private "views"
endpoint, the in-flight `&moduleURI=` factory parameter, and the CSV
REST endpoint all return either lockdown responses or 404s.

## Open implementation paths (in increasing effort)

1. **Manual drag-bind in DNG UI** — works today. ~30 sec per module.
2. **Skeleton ReqIF** (~1 day) — minimal valid ReqIF that says "specification X has child binding to existing artifact Y." Skips datatype/type-system replication because the artifacts and types already exist (they were created by `requirementFactory`). Multipart upload of `.reqifz` to `/rm/reqif_oslc/import?componentURI=…`, then poll `/rm/reqif_oslc/imports/<id>` until done.
3. **Full ReqIF** (~1 week) — closes the gap robustly across server versions. Handles datatype/type-system replication, all DNG attribute types, async import status polling, error feedback. Worth doing if the MCP needs to support arbitrary ELM deployments, not just goblue.

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
