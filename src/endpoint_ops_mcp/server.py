"""Endpoint Ops — Model Context Protocol server ("talk to your fleet").

This exposes a deterministic endpoint-fleet engine to a Claude client as a full
MCP surface: **Tools** (query + remediate), **Resources** (the raw inventory and
the scoring policy), and **Prompts** (one-click triage workflows).

It needs **no API key**. The server only returns structured, ground-truth data;
the user's Claude client (Claude Code, Claude Desktop, ...) supplies the reasoning
and calls these tools instead of guessing about the fleet.

Run it:
    endpoint-ops-mcp                       # stdio server (what a Claude client launches)
    python -m endpoint_ops_mcp.server
    mcp dev src/endpoint_ops_mcp/server.py # MCP Inspector (great for screenshots)

Point it at custom data/policy with env vars:
    ENDPOINT_OPS_DATA=/path/fleet.json  ENDPOINT_OPS_RULESET=/path/ruleset.yaml
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .fleet.engine import analyze
from .fleet.loader import DEFAULT_DATA_PATH, load_fleet
from .fleet.ruleset import DEFAULT_RULESET_PATH, load_ruleset
from .fleet.runbooks import (
    runbook_for_cluster,
    runbook_for_device,
    suggest_remediation as _steps_for_control,
)

mcp = FastMCP("endpoint-ops")

_DATA_PATH = os.environ.get("ENDPOINT_OPS_DATA", str(DEFAULT_DATA_PATH))
_RULESET_PATH = os.environ.get("ENDPOINT_OPS_RULESET", str(DEFAULT_RULESET_PATH))


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@lru_cache(maxsize=1)
def _state():
    """Load + analyze once; every tool reads from this cached snapshot.

    Returns (data, ruleset, report, breakdowns-by-device-id, raw-by-device-id).
    """
    from .fleet.scoring import evaluate

    data = load_fleet(_DATA_PATH)
    rs = load_ruleset(_RULESET_PATH)
    report = analyze(data, rs)
    reference = _parse_iso(report.generated_at)
    breakdowns = {ep.device_id: evaluate(ep, rs, reference) for ep in data.endpoints}
    raw = {ep.device_id: ep for ep in data.endpoints}
    return data, rs, report, breakdowns, raw


# --------------------------------------------------------------------------- #
# Tools — what the model calls for ground truth.
# --------------------------------------------------------------------------- #

@mcp.tool()
def get_fleet_health() -> dict:
    """Return the overall fleet-health summary: totals, compliance %, severity
    counts, and compliance broken down by role and by location."""
    _, _, report, _, _ = _state()
    return {
        "generated_at": report.generated_at,
        "total": report.total,
        "compliant": report.compliant,
        "compliance_pct": report.compliance_pct,
        "severity_counts": report.severity_counts,
        "by_role": report.by_role,
        "by_location": report.by_location,
    }


@mcp.tool()
def list_endpoints(role: str | None = None, location: str | None = None,
                   compliant: bool | None = None, min_risk: int = 0,
                   limit: int = 25) -> list[dict]:
    """List endpoints, optionally filtered by role, location, compliance, and a
    minimum risk score. Returns a compact summary per device, highest risk first."""
    _, _, _, breakdowns, _ = _state()
    rows = []
    for b in breakdowns.values():
        if role and b.role != role:
            continue
        if location and b.location != location:
            continue
        if compliant is not None and b.compliant != compliant:
            continue
        if b.risk < min_risk:
            continue
        dom = b.dominant
        rows.append({
            "device_id": b.device_id, "hostname": b.hostname, "role": b.role,
            "location": b.location, "risk": b.risk, "band": b.band,
            "compliant": b.compliant, "top_issue": dom.detail if dom else None,
        })
    rows.sort(key=lambda r: r["risk"], reverse=True)
    return rows[:limit]


@mcp.tool()
def get_endpoint(device_id: str) -> dict:
    """Return the raw inventory record for one device exactly as it appears in the
    MDM export (OS, patch level, encryption, check-in time, owner, etc.)."""
    _, _, _, _, raw = _state()
    ep = raw.get(device_id)
    if ep is None:
        return {"error": f"device {device_id!r} not found"}
    return asdict(ep)


@mcp.tool()
def get_compliance(device_id: str) -> dict:
    """Return the full compliance breakdown for one device: its risk score,
    band, compliance verdict, and every failing control with point values."""
    _, _, _, breakdowns, _ = _state()
    b = breakdowns.get(device_id)
    if b is None:
        return {"error": f"device {device_id!r} not found"}
    return asdict(b)


@mcp.tool()
def get_clusters(min_count: int = 2) -> list[dict]:
    """Return root-cause clusters: groups of at-risk devices sharing a dominant
    fault, with the role/location they correlate to and a runbook key."""
    _, _, report, _, _ = _state()
    return [asdict(c) for c in report.clusters if c.affected_count >= min_count]


@mcp.tool()
def suggest_remediation(device_id: str | None = None, cluster_key: str | None = None) -> dict:
    """Suggest concrete remediation steps for a device (by id) or a cluster
    (by runbook key). Steps are deterministic and derived from the findings."""
    _, _, report, breakdowns, _ = _state()
    if device_id:
        b = breakdowns.get(device_id)
        if b is None:
            return {"error": f"device {device_id!r} not found"}
        controls = [f.control for f in sorted(b.factors, key=lambda x: x.points, reverse=True)]
        steps: list[str] = []
        for c in controls:
            steps += [s for s in _steps_for_control(c) if s not in steps]
        return {"target": device_id, "controls": controls, "steps": steps}
    if cluster_key:
        cl = next((c for c in report.clusters if c.runbook_key == cluster_key), None)
        if cl is None:
            return {"error": f"no cluster with key {cluster_key!r}",
                    "available": [c.runbook_key for c in report.clusters]}
        return {"target": cluster_key, "root_cause": cl.root_cause,
                "steps": _steps_for_control(cl.root_cause)}
    return {"error": "provide device_id or cluster_key"}


@mcp.tool()
def generate_runbook(cluster_key: str | None = None, device_id: str | None = None) -> str:
    """Generate a Confluence-style remediation runbook (markdown) for a cluster
    (by runbook key) or a single device (by id). The client's model can enrich
    the returned scaffold into a publish-ready page."""
    _, _, report, breakdowns, _ = _state()
    if cluster_key:
        cl = next((c for c in report.clusters if c.runbook_key == cluster_key), None)
        if cl is None:
            return f"No cluster with key '{cluster_key}'. Available: " + ", ".join(
                c.runbook_key for c in report.clusters)
        return runbook_for_cluster(cl, report)
    if device_id:
        b = breakdowns.get(device_id)
        if b is None:
            return f"Device '{device_id}' not found."
        return runbook_for_device(b)
    return "Provide cluster_key or device_id."


# --------------------------------------------------------------------------- #
# Resources — context the model can read directly (the fleet's source of truth).
# --------------------------------------------------------------------------- #

@mcp.resource("fleet://inventory", mime_type="application/json")
def inventory() -> str:
    """The raw synthetic fleet inventory (the MDM export the engine scores)."""
    return Path(_DATA_PATH).read_text(encoding="utf-8")


@mcp.resource("fleet://policy", mime_type="text/yaml")
def policy() -> str:
    """The compliance & risk policy (policy-as-config) the engine scores against.
    Reading this lets the model explain *why* a device is scored the way it is."""
    return Path(_RULESET_PATH).read_text(encoding="utf-8")


@mcp.resource("fleet://health", mime_type="application/json")
def health() -> str:
    """A JSON snapshot of the current full fleet report (same shape the tools
    return) — handy to pin into context at the start of a triage session."""
    _, _, report, _, _ = _state()
    return json.dumps(report.to_dict(), indent=2)


# --------------------------------------------------------------------------- #
# Prompts — one-click workflows that drive the tools above.
# --------------------------------------------------------------------------- #

@mcp.prompt(title="Triage the fleet")
def triage_fleet() -> str:
    """A guided fleet-triage workflow: summarize health, surface root causes, and
    recommend the single highest-leverage fix."""
    return (
        "You are an endpoint-engineering lead triaging a managed device fleet. "
        "Use the endpoint-ops MCP tools as your source of truth — do not invent "
        "device facts.\n\n"
        "1. Call `get_fleet_health` and give a 2-3 sentence executive summary "
        "(compliance %, where the risk concentrates).\n"
        "2. Call `get_clusters` and explain each root-cause cluster in plain "
        "language, including the role/location it correlates with.\n"
        "3. Recommend the single highest-leverage cluster to fix first and why.\n"
        "4. Offer to generate a remediation runbook for it with `generate_runbook`."
    )


@mcp.prompt(title="Remediate a cluster")
def remediate(cluster_key: str) -> str:
    """Turn a root-cause cluster into a publish-ready remediation page."""
    return (
        f"Generate a remediation runbook for the cluster '{cluster_key}' by calling "
        f"`generate_runbook(cluster_key='{cluster_key}')`. Then enrich the returned "
        "scaffold into a Confluence-ready page: tighten the summary, add a short "
        "risk/impact note and a rollback caveat, and keep the Verification steps. "
        "Preserve the section headings. If the cluster key is unknown, call "
        "`get_clusters` first and ask which one I meant."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
