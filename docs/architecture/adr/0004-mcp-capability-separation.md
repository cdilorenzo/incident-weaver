# ADR 0004: Separate MCP read and write capability surfaces

- Status: Accepted
- Date: 2026-08-18

## Context

MCP is a core integration mechanism in the project, but exposing all tools to the AI runtime would weaken least privilege.

## Decision

Operations tools are separated into read and write capability surfaces.

The AI runtime is configured only with the read surface. The privileged control-plane execution path is the only component allowed to reach the write surface.

The implementation may reuse common tool/server code internally, but deployment configuration and credentials must preserve capability separation.

Use Streamable HTTP for remote MCP communication when the MCP slice is implemented.

## Consequences

- tool availability communicates least privilege structurally,
- security tests can assert that write tools are absent from the AI runtime,
- MCP configuration becomes part of the security architecture and must be tested.
