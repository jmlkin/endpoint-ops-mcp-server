"""Vendored fleet-health engine — the deterministic core this MCP server speaks for.

This package is a verbatim copy of the engine from the sibling `fleet-triage-ai`
project, kept here so the server clones and runs standalone. It is intentionally
self-contained: pure Python, no network, no API key. The layer above it
(`endpoint_ops_mcp.server`) consumes `engine.analyze`; this core never imports `mcp`.

  load_fleet(...) -> FleetData            # read the synthetic inventory
  load_ruleset(...) -> Ruleset            # read the policy-as-config
  analyze(data, ruleset) -> FleetReport   # score, aggregate, cluster — the single seam
"""

__version__ = "0.1.0"

from .engine import analyze  # noqa: E402,F401
