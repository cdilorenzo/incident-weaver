"""Stable connector/provider contracts for operational capabilities.

This package defines the minimal, vendor-neutral abstraction that read and
write operational capability providers must implement (CONN-001). The MCP
tool layer (``server.py`` / ``write_server.py``) depends only on these
contracts; vendor-specific knowledge stays inside individual connector
modules and never leaks into the tool layer or across the read/write
boundary.
"""
