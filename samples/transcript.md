# Sample transcript — "talk to your fleet"

A real session against the bundled synthetic fleet (200 devices, seed `1337`). Tool calls are shown inline; every number below is what the server actually returns.

---

**you ▸** Give me a health read on the fleet.

> `[tool] get_fleet_health()`

**Claude ▸** **156 / 200 endpoints are compliant (78.0%).** Severity skews healthy (102 healthy, 58 low, 36 medium) but there are **4 critical** devices that need attention now. The non-compliance isn't random — it concentrates in a few device classes. Want the root causes?

---

**you ▸** Yes — what are the root causes?

> `[tool] get_clusters()`

**Claude ▸** Four root-cause clusters explain almost all the risk:

| Cluster | Count | Correlates with |
| --- | --- | --- |
| `patch-drift-render-nodes` | 18 | role=render-node (18/18), location=SEA |
| `encryption-off-edit-bays` | 9 | role=edit-bay (9/9), location=ATX |
| `mdm-unenrolled-laptops` | ~10 | unmanaged ring, not enrolled |
| `stale-checkin-booths` | 6 | role=recording-booth (6/6), location=NYC (3/6) |

Each is a *systemic* source (a stalled patch ring, a shared gold image, an offline device class), not scattered one-offs.

---

**you ▸** Which recording booths are non-compliant?

> `[tool] list_endpoints(role="recording-booth", compliant=false)`

**Claude ▸** 7 of 30 recording booths are non-compliant, all from stale MDM check-ins:

- **`FLT-0156`** recording-booth-sea-156 — **risk 88 (critical)**, 32 days dark, also not MDM-enrolled
- `FLT-0151` (SEA, 49 days), `FLT-0153` / `FLT-0154` (NYC, ~30–34 days), `FLT-0152` / `FLT-0155` (~37–48 days), `FLT-0175` (LON, not enrolled)

The worst is **FLT-0156**. Want the per-device detail or a remediation runbook for the whole cluster?

---

**you ▸** Why is FLT-0156 scored so high?

> `[tool] get_compliance("FLT-0156")`

**Claude ▸** Risk **88 (critical)**, three stacked failing controls:

| Control | Points | Detail |
| --- | --- | --- |
| `stale_checkin` | 40 | 32 days since last check-in |
| `mdm_unenrolled` | 25 | not enrolled in MDM |
| `unmanaged_ring` | 15 | device is on the unmanaged patch ring |

It's effectively unmanaged *and* gone dark — the booth fell off the MDM entirely.

---

**you ▸** Draft a runbook for the stale-checkin cluster.

> `[tool] generate_runbook(cluster_key="stale-checkin-booths")`

**Claude ▸** Done — a Confluence-style runbook with **Summary / Scope (6 devices) / Root cause / Remediation steps / Verification / Rollback**. First steps: determine intentional-offline vs. lost, document exceptions for air-gapped booths, re-establish MDM check-in within 24h, and add a stale-check-in alert so this is caught proactively. Want me to enrich it into a publish-ready page? *(That's the `remediate` prompt.)*
