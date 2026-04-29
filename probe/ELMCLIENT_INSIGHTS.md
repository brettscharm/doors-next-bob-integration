# IBM elmclient — Insights for the doors-next-ai-agent MCP Server

Source: `/tmp/elm-pyc/elmclient/` (IBM ELM Python Client, MIT-licensed). Focus: things our 35-tool MCP server does not yet do, captured with literal file:line references.

---

## 1. "Magic header" requirements beyond `DoorsRP-Request-Type: public 2.0`

The DoorsRP header is the most exotic one — it is *only* used in `examples/dn_simple_modulestructure.py:191,229,234,273,282,341,354,387,396` and tells DNG to serve the `/structure` endpoint with the public Module API instead of the legacy internal one. But the elmclient quietly relies on a small zoo of other header tricks:

- **`net.jazz.jfs.owning-context`** — required on most requests against an app *unless* a config is set. Computed in `_project.py:179-187`. When a local or global config is active the client *deletes* the owning-context header and replaces it with `Configuration-Context`. Forgetting either (or sending both) produces a 400 "GCM not installed" or "ambiguous context" error.
- **`Configuration-Context` vs `vvc.configuration` vs `oslc_config.context`** — `httpops.py:487-492` `chooseconfigheader()` picks `vvc.configuration` if the URL contains `/cm/stream/`, `/cm/baseline/`, or `/cm/changeset/`, else `oslc_config.context`. The reason: when GCM isn't installed, RM throws an error if you use `oslc_config.context`.
- **`Configuration.Context` (with a dot, not a hyphen)** — used specifically when reloading a configuration-specific `services.xml` (`_rm.py:1038`, `_qm.py:337`, `_gcm.py:136`). This is *not* a typo — DNG accepts both forms in some places but the dot form is what works for the services document.
- **`X-Jazz-CSRF-Prevent: <JSESSIONID>`** — required for QM/ETM POSTs (`examples/etm_simple_updatetestresult.py:251,328`). Read JSESSIONID from session cookies and echo it as this header. Without it, ETM rejects writes.
- **`Referer`** — sometimes required, sometimes must be `None` (`examples/dn_simple_modulestructure.py:191`). For ETM writes it must be the app baseurl; for the module-structure GET it has to be removed entirely.
- **`OSLC-Core-Version: 2.0`** — default on RDF/XML calls (`httpops.py:254`); but for Module Structure and Reportable REST calls you have to set it to `None` to *suppress* it.
- **`X-Requested-With: XMLHttpRequest`** — set on the global app `_get_headers` (`_app.py:65`).

**We should add (M)** a small `headers_for(operation, config_uri)` helper that knows the recipe per operation, and pass `None`-valued headers all the way through to the wire (i.e., remove them from the final `requests.Request`). Today our server pays for missing/extra headers in 400s.

---

## 2. Configuration-Context / GCM handling

The elmclient treats configs as first-class state on the project/component object: `self.local_config` and `self.global_config` (`_project.py:35,266-267`). `set_local_config()` (`_project.py:246-271`) does three things: it resolves a name to a URI; it caches the URI on the component; and it re-fetches the services.xml *under that config* so type-system queries are correct. Discovery of the active stream uses `load_components_and_configurations()` (`_rm.py:496`) which walks `oslc:details` -> components -> configurations and stores them in `self._components[compu]['configurations']`. Switching context is purely a parameter/header swap — `Configuration-Context: <streamuri>` for OSLC writes, or the param `vvc.configuration=<streamuri>` for module-structure and OSLC Query when GCM is not installed (`httpops.py:756-765` actively *copies* the header into the param so cached URLs are config-specific).

Streams created in a component appear under `oslc_config:streams` on the configuration RDF; baselines under `oslc_config:baselines` (`_rm.py:1572,1657,1723`). The "initial stream name" convention (`<component> Initial Stream`) is hardcoded in `_rm.py:2052,2214`. There is no per-session caching of the resolved stream URL beyond the in-memory dict; subsequent runs re-discover.

**We should add (M)** a `set_active_config(component, name_or_uri)` MCP tool that mirrors this lifecycle and persists the resolved URL in our session, plus emit it in every dependent request. Today we appear to recompute it every call.

---

## 3. Pagination

`oslcqueryapi.py:569-724` is the canonical implementation. Key moves:

```python
query_params['oslc.paging']  = 'true'
query_params['oslc.pageSize'] = str(pagesize)            # default 200
...
if rdfxml.xml_find_element(this_result_xml, ".//oslc:nextPage") is None:
    break                                                # last page
params = None                                            # do NOT resend
query_url = rdfxml.xmlrdf_get_resource_uri(this_result_xml, ".//oslc:nextPage")
...
headers = {'Configuration-Context': None}                # suppress on page 2+
```

Three subtleties:

1. After page 1, **drop all params** — the `oslc:nextPage` URL already has them. Re-adding them double-encodes config and breaks the request (`oslcqueryapi.py:654-655,720-723`, with a link to GitHub discussion #44).
2. Suppress `Configuration-Context` on page 2+ — DNG otherwise appends it to every nextpage URL, which grows unboundedly until the URL exceeds server limits (`oslcqueryapi.py:720-724`).
3. Total-count parsing is version-sensitive: `oslc:totalCount` for newer servers, falling back to a regex on `oslc:ResponseInfo/dcterms:title` like `"Query Results: 40220"` for 6.x (`oslcqueryapi.py:666-679`). 7.x uses `_startIndex=`, older uses `page=`/`pageNum=`.

The HTTP-level helper `execute_get_rdf_xml(... merge_linked_pages=True)` (`httpops.py:251-289`) handles RFC 5988 `Link: rel="next"` pagination for non-OSLC reads (used by Reportable REST).

**We should add (M)** an explicit `paginated_oslc_query` helper in our MCP server with these three behaviors codified, plus expose `pagesize` and `max_results`. Bonus: keypress-cancel mid-query (`oslcqueryapi.py:706-716`) — probably not relevant for MCP, but interesting.

---

## 4. Reportable REST usage

`_rm.py:1894-1914` declares 15 supported `artifact_formats`: `collections, comments, comparison, linktypes, modules, processes, resources, reviews, revisions, screenflows, storyboards, terms, text, uisketches, usecasediagrams, views`. The base URL is `<rmcontext>/publish` (`_rm.py:1895`). The CLI processor `process_represt_arguments()` (`_rm.py:2082-2334`) shows what each is for and what params they accept. Highlights that we don't expose:

- `publish/comparison` (7.0.2+) — diff between two configs. Requires `sourceConfigUri` and `targetConfigUri` and crucially *no* `vvc.configuration`/`oslc_config.context` param (`_rm.py:2222-2227`).
- `publish/views?viewUri=<uri>` — render a saved view's results.
- `publish/text?coverpage=true` / `signaturepage=true` — for document export workflows.
- `publish/resources/*?modifiedSince=<ISO8601>` — incremental sync (DCC-only flag, `_rm.py:2310-2320`).
- `publish/linktypes` — bulk export of link types in a project.
- `publish/modules?moduleUri=<uuid>` — full hierarchical export of a module *including all binding metadata* in one call. This is far cheaper than walking `/structure` and GETting each artifact, which is what our current tools do.
- `publish/text?expandEmbeddedArtifacts=true` — flattens "Insert artifact" embeds.

The header trick: Reportable REST calls send `remove_headers=['net.jazz.jfs.owning-context']` (`examples/dn_simple_represt.py:74`).

QM uses `service/com.ibm.rqm.integration.service.IIntegrationService/...` (`_qm.py:561`) and EWM uses `rpt/repository/...` (`_ccm.py:304`). Different base URL, same idea.

**We should add (L)** an MCP tool `reportable_rest(format, project, component, config, **filters)` that accepts the 15 formats and returns rows. This is the single biggest missing capability — with one call you can get all artifacts in a module hierarchically. Currently our code probably issues N OSLC queries per module export.

---

## 5. JSON variants of OSLC endpoints

The Module Structure API is the cleanest example — both RDF/XML and JSON work (`examples/dn_simple_modulestructure.py:339-396`). Compare the JSON binding:

```python
newbinding = {
    "uri":           tempbinding_u,
    "component":     comp_u,
    "type":          "dng_module:Binding",
    "module":        themodule_u,
    "boundArtifact": toinsert_u,
    "childBindings": []
}
modstructure_j[0]["childBindings"].append(tempbinding_u)
modstructure_j.append(newbinding)
response = c.execute_post_json(structure_u, data=modstructure_j, put=True, ...)
```

This is dramatically simpler than our RDF/XML approach in `probe/20_module_structure_api.py`. Other JSON-friendly endpoints used in the client:

- **Tracker polling** (`httpops.py:413-462`) — `wait_for_tracker(useJson=True)` reads the task tracker as JSON (`status="InProgress"` poll loop). Used after every async POST (changeset/baseline/stream creation).
- **GC contributions** — `gcsdk-api/flatListOfContributionsForGcHierarchy` returns JSON natively (`_project.py:228`).
- **`execute_get_json_soap`** (`httpops.py:343-372`) — for SOAP-wrapped JSON responses (used by some EWM endpoints).
- The `execute_get_json`/`execute_post_json` helpers (`httpops.py:312-341`) default to `Accept: text/json`, `Content-Type: application/json`. Module-structure JSON requires the same magic-header recipe as the XML form (`DoorsRP-Request-Type: public 2.0`, kill `OSLC-Core-Version` and `Configuration-Context`).

**We should add (S)** a JSON path on our `module_structure_*` tools — much less RDF wrangling, and it's the same wire protocol the IBM client already proves works. **We should add (S)** a `wait_for_tracker(useJson=True)` helper for any async write so we don't return before the change actually lands.

---

## 6. Module operations beyond binding

The skeleton `BindingResource` class in `_rm.py:47-73` declares the canonical operations even though the IBM authors only stubbed them:

```python
class BindingResource(resource.Resource):
    def addBelow(self, coreid_or_coreresource_or_artifacttype): ...
    def addAfter(self, coreid_or_coreresource_or_artifacttype): ...
    def moveAfter(self, binding): ...
    def moveBelow(self, binding): ...
    def delete(self): ...
```

The actual recipe is in `examples/dn_simple_modulestructure.py:256-273` (XML) and `:374-387` (JSON). The pattern is uniform: **mutate the structure document client-side, PUT it back with `If-Match: <etag>`, wait_for_tracker on the 202.** Specifically:

- **Create section heading** — append a `Binding` object with `"isHeading": true` (`isHeading` field in JSON; `<rm_modules:isHeading>true</rm_modules:isHeading>` in XML, `examples/dn_simple_modulestructure.py:241`).
- **Reorder** — change order of URIs in a parent's `childBindings` array.
- **Move (re-parent)** — remove URI from old parent's `childBindings`, append to new parent's. Atomic on the PUT.
- **Delete a binding** — remove its URI from any parent's `childBindings`, and remove its entry from the top-level structure list.
- **Tree as hierarchy** — `examples/dn_simple_modulestructure.py:408-427` `json_structure_walk()` recursively yields `start/startChildren/endChildren/end` events. Adapt this and you have a tree view in three lines.

**We should add (M)** five MCP tools: `module_create_heading`, `module_reorder_bindings`, `module_reparent_binding`, `module_delete_binding`, `module_get_tree`. All five are the same PUT — the only difference is what the structure list looks like before we PUT it. Once `probe/20_module_structure_api.py` is generalized, these come almost for free.

---

## 7. Component / stream / baseline creation

`_rm.py:1548-1692` has the full lifecycle. Highlights:

- **Create baseline** (`_rm.py:1548-1607`): GET the current stream, find its `oslc_config:baselines` URL, POST a tiny RDF/XML body:

  ```xml
  <oslc_config:Configuration rdf:about="https://.../something">
    <oslc_config:component rdf:resource="{comp_u}"/>
    <dcterms:title rdf:parseType="Literal">{baselinename}</dcterms:title>
  </oslc_config:Configuration>
  ```
  
  202 + Location -> `wait_for_tracker(...)` -> the tracker's `dcterms:references` is the new baseline URI. Note the trailing `/something` in `rdf:about` is a literal placeholder; DNG ignores it.

- **Create stream** (`_rm.py:1611-1692`): rule is "you can only create a stream from a baseline." So the client *first* creates a baseline if you're in a stream, then POSTs to that baseline's `oslc_config:streams` URL with the same body shape.

- **Create changeset** (`_rm.py:1694-1755`): POST to the stream's `rm_config:changesets` URL.

- **Deliver changeset** (`_rm.py:1768-1875`): two-phase. POST a delivery session to the factory; then PUT it back with `rm_config:deliverySessionState` set to `rm_config:delivered` to actually start the delivery. Wait for the tracker. Stream-to-stream delivery is also supported.

- **Discard changeset**: not implemented in elmclient (`_rm.py:1757-1758`).

GCM stream/component creation is *not* in `_gcm.py` — IBM hasn't published that yet either.

**We should add (L)** four tools: `create_baseline`, `create_stream`, `create_changeset`, `deliver_changeset`. Pre-condition checks (in-stream vs in-changeset) need to be ported. Body templates are tiny.

---

## 8. Changesets are required for writes when the project is opt-in

`_rm.py:1697-1702` enforces "Can't create a changeset in an opt-out project" / "Can't create CS if not in stream". Conversely, `set_local_config` lets you target a changeset URI directly, after which all subsequent OSLC writes route into that changeset (the `Configuration-Context: <changeset-uri>` does the work).

The user-visible rule: if a DNG project has CM-enabled and is in opt-in mode, **edits to artifacts in a *stream* fail unless a changeset is open and active**. The MCP server today (per the codebase docs) writes against streams directly; on opt-in projects this will silently 400 or get routed wrong. The elmclient pattern is:

1. `c.set_local_config(stream_uri)`
2. `cs_uri = c.create_changeset(name="MCP edit session")`
3. `c.set_local_config(cs_uri)` — now writes go into the changeset
4. ...edits...
5. `c.deliver(targetstream_u=stream_uri)` — delivery uses the tracker

**We should add (M)** a `with_changeset(component, stream, name)` context-manager-style tool, plus auto-detect "opt-in stream + write request" and warn the AI to wrap it.

---

## 9. Authentication options

`httpops.py` supports four flows:

- **Basic auth** (default) — the username/password constructor.
- **Jazz Form authorization** (`_jazz_form_authorize`, `httpops.py:212-235` form parser, `:725-727`) — the legacy WAS/Tomcat j_security_check flow. Triggered by header `X-com-ibm-team-repository-web-auth-msg: authrequired`.
- **Jazz Authorization Server / JSA** (`_jsa_login`, `httpops.py:955+`) — the modern flow. Triggered by 401 + `X-JSA-AUTHORIZATION-REDIRECT` header. `WWW-Authenticate` must contain `JSA`. Supports OIDC- and SAML-backed JAS via redirect-following with cookie capture.
- **Application passwords** (`AP_PREFIX = "ap:"`, `httpops.py:112,511-535`). Password is encoded as `ap:rm:rmpassword,gc:gcpassword,defaultpassword`. The `get_app_password(url)` method matches the URL's context root against the prefix list. When an app password is in use the User-Agent gets `app-password-enabled` appended (`httpops.py:742,798`). This is what IBM recommends over basic auth for non-interactive scripts.

There's also pickle-based cookie persistence (`httpops.py:744-754`) so re-runs skip re-auth.

OAuth/JWT/PAT in the modern bearer-token sense are not supported — JSA *can* be backed by OIDC but the client speaks the legacy redirect-cookie flow.

**We should add (S)** application-password support — the URL-prefix-routed password format is a clean way to give the agent app-scoped creds without storing the user's actual password. **We should add (M)** JSA flow detection — if the server returns `X-JSA-AUTHORIZATION-REDIRECT` we currently fail; the elmclient code at `httpops.py:839-861` is straightforward to port.

---

## 10. Errors / retries

`HttpRequest._execute_request` (`httpops.py:540-557`) retries with a fixed schedule `[2, 5, 10, 0]` (last `0` = "give up"):

```python
for wait_dur in [2, 5, 10, 0]:
    try:
        return self._execute_one_request_with_login(...)
    except requests.RequestException as e:
        if wait_dur == 0 or not self._is_retryable_error(e, result): raise
        time.sleep(wait_dur)
```

`_is_retryable_error` (`:711-721`) treats only `REQUEST_TIMEOUT (408)`, `LOCKED (423)`, `SERVICE_UNAVAILABLE (503)` as retryable. Notably: 500 and 400 are *not* retried; rate-limit 429 is *not* in the list. The login layer (`_execute_one_request_with_login`, `:733-925`) handles a different class of "errors" (auth redirects) which are essentially silent retries after authentication — the caller never sees the 401.

CSRF rejection: `httpops.py:881-887` recognizes 403/409 with `X-Jazz-CSRF-Prevent` in the body as a CSRF-prevention failure (you forgot to send the JSESSIONID echo header). Useful to special-case.

**We should add (S)** the same retry decorator over our HTTP layer with 408/423/429/503 as retryable, exponential or linear backoff, and 5 attempts. **We should add (S)** detect-and-explain logic for 403 + `X-Jazz-CSRF-Prevent` → tell the AI the missing header, instead of bubbling a generic 403.

---

## 11. Type-system discovery

`_rm.py:1028-1135` `_load_types` walks `services.xml` for every `oslc:resourceShape`, GETs each, and registers:

- the **shape name** (`dcterms:title` or `rdfs:label`),
- its **RDF URI** (`owl:sameAs`),
- its **shape formats** (e.g. `Module`, `Collection`, `Text` — derived from `oslc:describes` URIs, `_rm.py:1078`),
- and every **property/attribute** with name + range/valueType + multivalued flag (`_rm.py:1106-1135`).

For each property of type enum, a follow-up GET expands the enum's allowed values. The result is a `_typesystem.TypeSystem` keyed by the config URI (`_rm.py:840`), so each baseline/changeset has its own loaded copy. There's also a Types API client at `_rmtypesapi.py` (`/types` endpoint, `https://jazz.net/wiki/bin/view/Main/DNGTypeAPI`) that supports *creating* attribute types (`createSimpleAttributeType`, `createEnumAttributeType` at `_rmtypesapi.py:63,127`).

Link types are discovered as a side effect of loading shapes — they appear as properties whose `oslc:range` is an artifact type. `c.get_linktype_uri(linktypename)` (`examples/dn_simple_modifylink.py:161`) is the lookup.

**We should add (M)** to our `get_attribute_definitions`:

- include enum values inline (today we appear to require a follow-up call),
- include shape formats so the caller can filter "module-only types",
- include link-type properties (today these may be mixed with regular attributes or filtered out).

**We should add (L)** an `attribute_type_create` tool wrapping `_rmtypesapi.py` for projects where the AI needs to extend the schema.

---

## 12. Linking patterns

`examples/dn_simple_modifylink.py:236-272` is the literal recipe for adding a same-component link:

```python
fromartifact_x, etag = c.execute_get_rdf_xml(fromartifact_u, return_etag=True, ...)
thenode_x = rdfxml.xml_find_element(fromartifact_x, ".//rdf:Description[@rdf:about]")
# add (or remove) a child element whose tag is the link-type URI
ET.SubElement(thenode_x, rdfxml.uri_to_tag(lt_u),
              {'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': toartifact_u})
c.execute_post_rdf_xml(fromartifact_u, data=fromartifact_x, put=True,
                       cacheable=False, headers={'If-Match': etag}, ...)
```

Subtleties our `create_link` is likely missing:

1. **Identify the *core* artifact, not the binding.** OSLC Query for `dcterms:identifier=X` returns *both* the core artifact and its module bindings; the example filters by "has `rm_nav:parent`" (`examples/dn_simple_modifylink.py:189-198`). Linking from a binding rather than the core artifact creates a binding-scoped link, which is rarely what the user wants.
2. **Cross-domain backlinks (RM ↔ QM/EWM/AM).** The `OSLC_LINK_TYPES` table at `examples/dn_simple_modifylink.py:51-60` lists the eight predefined cross-domain types. Crucially, **the link is always created on the *target* side**: a "Validates" backlink lives on the QM TestCase, not on the RM Requirement. `oslc_qm:reportsOnTestCase` and friends in `examples/etm_simple_updatetestresult.py:316-318` show the QM-side encoding. If our `create_link` only knows how to write on the RM side, half of cross-domain linking is impossible.
3. **`X-Jazz-CSRF-Prevent: <JSESSIONID>` is required for QM/CCM POSTs**, plus `Referer` set to the app baseurl, and `remove_parameters=['oslc_config.context']` because QM's POST endpoint rejects the param (`examples/etm_simple_updatetestresult.py:251,328`).
4. **Custom link types** must be defined in *both* components and pinned to a stable RDF URI; otherwise cross-component linking silently fails (per the comment at `examples/dn_simple_modifylink.py:30-31`).
5. **Existence check before add** (`examples/dn_simple_modifylink.py:251-257`) — DNG happily stores duplicates if you don't check.

**We should add (M)** to `create_link`: side-aware (write on FROM or TO based on link-type direction), JSESSIONID/CSRF support for QM/CCM targets, core-artifact filtering, and idempotency. **We should add (S)** a `delete_link` mirror.

---

## Top 10 prioritized adoptions

| # | Adoption | Effort | Impact | Depends on |
|---|---|---|---|---|
| 1 | `paginated_oslc_query` w/ drop-params + suppress-config-header on page 2+, total-count regex fallback | M | High — fixes silent truncation past 200 results | — |
| 2 | Reportable REST tool (`publish/<format>`) — modules/resources/text/comparison/views | L | Very high — single call for hierarchical exports | Removing `net.jazz.jfs.owning-context` |
| 3 | `wait_for_tracker(useJson=True)` after every async write (202 + Location) | S | High — eliminates "PUT returned but change not persisted" race | — |
| 4 | Five module-binding tools (create-heading, reorder, reparent, delete, get-tree) on top of working structure PUT | M | High — completes Module Structure API surface | #3 |
| 5 | Changeset lifecycle (`create_changeset`, `deliver_changeset`) + `with_changeset` wrapper | M | High — required for writes on opt-in CM-enabled projects | #3 |
| 6 | Stream/baseline creation tools | L | Medium — needed for release workflows | #3, #5 |
| 7 | Header recipe per operation + null-header propagation through `requests` | M | High — quietly fixes a class of 400s across all tools | — |
| 8 | Side-aware `create_link` + JSESSIONID/CSRF for QM/CCM, core-artifact filter, idempotency, `delete_link` | M | High — unlocks proper cross-domain traceability | — |
| 9 | Retry decorator (408/423/429/503 with backoff) + 403/CSRF detect-and-explain | S | Medium — robustness on flaky networks and helpful errors | — |
| 10 | Application-password auth (`ap:rm:xxx,gc:yyy`) + JSA-redirect flow detect | M | Medium — modern auth without storing primary password | #9 (shared HTTP layer) |

Honorable mentions deferred from the top 10: enriched type-system discovery (#11 above) — useful but our current `get_artifact_types` covers the common case; types-API write (`_rmtypesapi.py`) — niche; SAVE-cookies pickle persistence — small win.

---

## Specific snippets worth keeping handy

The "pick the right config param" rule, copied verbatim from `httpops.py:487-492`:

```python
def chooseconfigheader(configurl):
    # for rm if its a local config must use vvc.configuration because when GCM
    # isn't installed using oslc_config.context throws an error that GCM isn't installed
    if "/cm/stream/" in configurl or "/cm/baseline/" in configurl or "/cm/changeset/" in configurl:
        return "vvc.configuration"
    return "oslc_config.context"
```

The page-2-and-beyond pagination recipe from `oslcqueryapi.py:629-724`:

```python
while True:
    this_result_xml = self.execute_get_rdf_xml(query_url, params=params, headers=headers, ...)
    if rdfxml.xml_find_element(this_result_xml, ".//oslc:nextPage") is None:
        break
    params  = None                                # CRITICAL: don't resend
    headers = {'Configuration-Context': None}     # CRITICAL: don't resend
    query_url = rdfxml.xmlrdf_get_resource_uri(this_result_xml, ".//oslc:nextPage")
```

The two-line module-structure JSON write (`examples/dn_simple_modulestructure.py:384-387`):

```python
modstructure_j[0]["childBindings"].append(tempbinding_u)
modstructure_j.append(newbinding)
response = c.execute_post_json(structure_u, data=modstructure_j, put=True,
        cacheable=False, headers={'If-Match': etag, 'vvc.configuration': config_u,
        'DoorsRP-Request-Type':'public 2.0', 'OSLC-Core-Version': None,
        'Configuration-Context': None})
```

The deliver-changeset two-phase pattern (`_rm.py:1832-1859`):

```python
# 1) POST to delivery-session factory -> get session URI
response = self.execute_post_rdf_xml(ds_f_u, data=body, ...)
ds_u, ds_x = ...   # parse Location and follow it
# 2) PUT the session back with state = rm_config:delivered
state_x.set('{...rdf...}resource', 'http://.../config#delivered')
response = self.execute_post_rdf_xml(ds_u, data=ds_x, headers=..., put=True)
# 3) wait
self.wait_for_tracker(response.headers['Location'], progressbar=True, ...)
```
