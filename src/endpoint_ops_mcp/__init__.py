"""Endpoint Ops MCP Server — talk to a studio endpoint fleet from Claude.

A Model Context Protocol server that exposes a synthetic managed-endpoint fleet as
Tools, Resources, and Prompts. No API key: the server returns ground-truth data and
the connected Claude client (Claude Code, Claude Desktop) supplies the reasoning.
"""

__version__ = "0.1.0"
