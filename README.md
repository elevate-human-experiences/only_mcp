# only_mcp

A simple archetype MCP v0.2 client and server implementation

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
