# MCP Inspector walkthrough

The [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) is the fastest way to *see* this server's full protocol surface without a Claude client — ideal for screenshots.

## Run it

```bash
pip install -e .
mcp dev src/endpoint_ops_mcp/server.py
```

This launches the Inspector web UI (it prints a local URL) with the server connected over stdio.

## What you'll see

- **Tools (7):** `get_fleet_health`, `list_endpoints`, `get_endpoint`, `get_compliance`, `get_clusters`, `suggest_remediation`, `generate_runbook`. Each is callable from the UI with a form for its arguments.
- **Resources (3):** `fleet://inventory`, `fleet://policy`, `fleet://health`. Click to read the raw inventory, the scoring policy, and a live JSON report.
- **Prompts (2):** `triage_fleet`, `remediate`. Expand to see the workflow message each one injects.

## A 30-second demo path

1. **Resources → `fleet://health`** — read the live fleet report (200 devices, 78% compliant).
2. **Tools → `list_endpoints`** — set `role = recording-booth`, `compliant = false`, run. Seven devices come back, highest risk first.
3. **Tools → `generate_runbook`** — set `cluster_key = stale-checkin-booths`, run. A full markdown runbook renders.

> _Screenshot placeholder:_ capture the Tools list and one `list_endpoints` result for the README / LinkedIn post.
