"""Render the README screenshots as SVG (no GUI needed).

Uses Rich's offline SVG export so the visuals are reproducible, crisp at any zoom,
and version-controlled. Run from the repo root:

    python scripts/make_screenshots.py

Outputs:
    docs/screenshots/talk-to-fleet.svg   # the "talk to your fleet" transcript
    docs/screenshots/protocol-surface.svg # tools / resources / prompts at a glance

Numbers are the real values the server returns for the bundled synthetic fleet
(seed 1337); see samples/transcript.md.
"""

from __future__ import annotations

import io
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def _line(role: str, role_style: str, text: str, text_style: str = "") -> Text:
    t = Text()
    t.append(f"{role} ", style=role_style)
    t.append(text, style=text_style)
    return t


def talk_to_fleet() -> None:
    console = Console(record=True, width=92, file=io.StringIO(), legacy_windows=False)

    you = "bold cyan"
    tool = "yellow"
    claude = "bold magenta"

    blocks = [
        _line("you   ▸", you, "which recording booths are non-compliant?"),
        _line("      ⚙", tool, 'list_endpoints(role="recording-booth", compliant=false)', "dim"),
        _line("claude ▸", claude,
              "7 of 30 recording booths are non-compliant — all from stale MDM", "white"),
        Text("         check-ins. Worst: FLT-0156 (SEA, 32 days dark, risk 88).", style="white"),
        Text("         They share one root cause: stale-checkin-booths.", style="white"),
        Text(),
        _line("you   ▸", you, "why is FLT-0156 scored so high?"),
        _line("      ⚙", tool, 'get_compliance("FLT-0156")', "dim"),
        _line("claude ▸", claude, "risk 88 (critical): stale_checkin +40, mdm_unenrolled", "white"),
        Text("         +25, unmanaged_ring +15. It fell off MDM entirely.", style="white"),
        Text(),
        _line("you   ▸", you, "draft a runbook for the cluster."),
        _line("      ⚙", tool, 'generate_runbook(cluster_key="stale-checkin-booths")', "dim"),
        _line("claude ▸", claude, "Done — Summary / Scope (6 devices) / Root cause /", "white"),
        Text("         Remediation steps / Verification / Rollback.", style="white"),
    ]

    body = Group(*blocks)
    console.print(Panel(
        body,
        title="[bold]endpoint-ops MCP[/bold]  ·  talk to your fleet",
        subtitle="[dim]no API key · 100% synthetic data[/dim]",
        border_style="magenta",
        padding=(1, 2),
    ))
    console.save_svg(str(OUT / "talk-to-fleet.svg"), title="endpoint-ops-mcp-server")


def protocol_surface() -> None:
    console = Console(record=True, width=92, file=io.StringIO(), legacy_windows=False)

    def section(title: str, rows: list[tuple[str, str]], header_style: str) -> Table:
        t = Table(show_header=False, expand=True, box=None, padding=(0, 1))
        t.add_column(style=header_style, no_wrap=True, ratio=2)
        t.add_column(style="white", ratio=5)
        for name, desc in rows:
            t.add_row(name, desc)
        return t

    tools = section("tools", [
        ("get_fleet_health", "totals, compliance %, severity, by role & location"),
        ("list_endpoints", "filter by role / location / compliance / min-risk"),
        ("get_endpoint", "raw inventory record for one device"),
        ("get_compliance", "risk score, band, failing controls + points"),
        ("get_clusters", "root-cause groups + the role/location they correlate to"),
        ("suggest_remediation", "deterministic steps for a device or cluster"),
        ("generate_runbook", "full Confluence-style remediation markdown"),
    ], "bold yellow")

    resources = section("resources", [
        ("fleet://inventory", "the raw synthetic MDM export"),
        ("fleet://policy", "the compliance & risk policy (as config)"),
        ("fleet://health", "live JSON snapshot of the full report"),
    ], "bold green")

    prompts = section("prompts", [
        ("triage_fleet", "guided triage → root causes → top fix"),
        ("remediate(cluster_key)", "turn a cluster into a publish-ready page"),
    ], "bold cyan")

    group = Group(
        Text("🔧 TOOLS  (7)", style="bold yellow"), tools, Text(),
        Text("📄 RESOURCES  (3)", style="bold green"), resources, Text(),
        Text("💬 PROMPTS  (2)", style="bold cyan"), prompts,
    )
    console.print(Panel(
        group,
        title="[bold]endpoint-ops MCP[/bold]  ·  protocol surface",
        border_style="magenta",
        padding=(1, 2),
    ))
    console.save_svg(str(OUT / "protocol-surface.svg"), title="endpoint-ops-mcp-server")


if __name__ == "__main__":
    talk_to_fleet()
    protocol_surface()
    print(f"Wrote SVGs to {OUT}")
