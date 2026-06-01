"""Tests for the Endpoint Ops MCP server.

These call the underlying tool/resource functions directly (no live MCP host
needed), which proves the vendored engine seam survived the copy + path edits and
that every tool returns the shape the protocol layer advertises.
"""

from __future__ import annotations

import json

from endpoint_ops_mcp import server


def test_engine_loads_full_fleet():
    data, _, report, breakdowns, raw = server._state()
    assert len(data.endpoints) == 200
    assert report.total == 200
    assert len(breakdowns) == 200 == len(raw)
    assert 0 <= report.compliance_pct <= 100


def test_list_endpoints_filters_by_role_and_sorts_desc():
    rows = server.list_endpoints(role="recording-booth", min_risk=1)
    assert rows, "expected at least one at-risk recording-booth in the seeded fleet"
    assert all(r["role"] == "recording-booth" for r in rows)
    risks = [r["risk"] for r in rows]
    assert risks == sorted(risks, reverse=True)


def test_list_endpoints_compliant_filter():
    compliant = server.list_endpoints(compliant=True, limit=500)
    assert compliant and all(r["compliant"] is True for r in compliant)
    noncompliant = server.list_endpoints(compliant=False, limit=500)
    assert noncompliant and all(r["compliant"] is False for r in noncompliant)


def test_get_endpoint_raw_vs_compliance():
    raw = server.get_endpoint("FLT-0001")
    assert raw["device_id"] == "FLT-0001"
    assert "disk_encryption" in raw and "last_checkin" in raw  # raw inventory fields
    verdict = server.get_compliance("FLT-0001")
    assert {"risk", "band", "compliant", "factors"} <= verdict.keys()
    assert server.get_endpoint("NOPE")["error"]
    assert server.get_compliance("NOPE")["error"]


def test_clusters_present_with_runbook_keys():
    clusters = server.get_clusters()
    assert clusters, "seeded fleet plants correlated faults -> expect clusters"
    assert all(c["runbook_key"] for c in clusters)


def test_generate_runbook_markdown():
    key = server.get_clusters()[0]["runbook_key"]
    md = server.generate_runbook(cluster_key=key)
    assert "## Remediation steps" in md and "## Verification" in md
    assert server.generate_runbook(device_id="NOPE").startswith("Device 'NOPE' not found")


def test_suggest_remediation_paths():
    key = server.get_clusters()[0]["runbook_key"]
    by_cluster = server.suggest_remediation(cluster_key=key)
    assert by_cluster["steps"]
    # find any at-risk device to remediate by id
    dev = server.list_endpoints(min_risk=1, limit=1)[0]["device_id"]
    by_device = server.suggest_remediation(device_id=dev)
    assert by_device["steps"] and by_device["target"] == dev
    assert server.suggest_remediation()["error"]


def test_resources_return_nonempty_text():
    inv = server.inventory()
    assert json.loads(inv)["endpoints"]          # valid inventory JSON
    assert "compliance:" in server.policy()      # the YAML policy
    assert json.loads(server.health())["total"] == 200
