# only_mcp

A simple MCP v0.2 client and server implementation, for me to learn about MCP.

IT is not a complete implementation. Neither is it to be used for production.

## Story So Far

Spent the weekend implementing MCP v0.2—exactly as fun as it sounds! Agents can now leverage authenticated tools, though there's room for improvement.

Key observations:

- **Protocol Changes**: MCP v0.2 significantly differs from v0.1—most notably, the SSE endpoint is gone. It also relies on a `.well-known` OAuth flow for auth. The introduction of application/json requests simplify some interactions but remove the option for server push via SSE.

- **SDK and Tooling Gaps**: Current Python SDK to build your MCP server quickly is still at v0.2 with limited auth support, which pushed me into building a Falcon-based server compatible with both standards. Dev tooling lags behind—Claude integration, for instance, still demands local stdio-based setups. The promising `mcp-proxy` tool doesn't yet support v0.2, causing unexpected detours during implementation.

- **Interoperability Concerns**: MCP's tool schema differs from OpenAI's chat-completion standard, complicating implementations. Function call chains (e.g., fetching schema before updates) also present challenges—tool-calling workflows could be more streamlined.

- **Long-running Tasks**: While direct support is still missing, MCP v0.2 introduces event IDs for task status polling—a welcome addition, though yet to be tested in my setup.

- **Deployment and Strategy**: MCP endpoints ideally coexist alongside REST APIs and OAuth flows, making it suitable for dedicated agent traffic handling. Cloudflare emerges as a solid managed option, though self-hosting might become preferable as tooling matures. Founders considering building a standalone MCP gateway in the cloud might want to reassess the long-term viability of that approach.

Overall, MCP v0.2 is progressing nicely but needs a few iterations for tooling and SDK maturity.

## Developer Instructions

1. Pre-commit

```sh
pre-commit install
```

1. We only develop inside containers.

```sh
docker compose up --build
```

1. Frontend dependencies are managed locally. If you need to run eslint manually, run:

```sh
npm --prefix frontend install && npx eslint
```
