# Playground Frontend Package

This package contains the Flask-based Playground Entry, Builder, and Runner experience.

## Run Locally

All local and deployed executions read model configuration from the Azure `agentic-sdk-models` Key Vault. Local runs fetch the access token through the Azure CLI, so before starting the Playground:

1. Install the Azure CLI (`winget install -e --id Microsoft.AzureCLI`, or the MSI at https://aka.ms/installazurecliwindows).
2. Run `az login --tenant <訂閱租戶 ID>` with an account that has read access to the `agentic-sdk-models` Key Vault, replacing `<訂閱租戶 ID>` with the tenant ID of the 訂閱 that owns this Key Vault. Pinning `--tenant` avoids `az login` silently landing on a different signed-in tenant that has no access to this vault and won't trigger the MFA challenge the correct tenant requires.
3. If prompted for a subscription after signing in, any subscription under that tenant works — the Key Vault access token isn't scoped to a specific subscription.

Then start the Playground:

```powershell
uv run python -m flask --app playground.app run --debug --port 5050
```

Then open:

- `http://127.0.0.1:5050/playground`
- `http://127.0.0.1:5050/playground/builder`
- `http://127.0.0.1:5050/playground/run`

Before release, run the [Browser FAE checklist](../docs/browser-fae.md) through the VS Code Browser.

AI Hub navigation also enters the same pages through these handoff routes:

- `POST /playground/aihub/navigation/builder`
- `POST /playground/aihub/navigation/runner`
- `GET` / `POST /playground/aihub/navigation/shared-runner`

## Current Scope

- Entry route and template
- Windows OOBE-style Builder shell
- Task-page Runner shell
- Lightweight page-specific JavaScript modules
- Shared visual language across the three pages
- v2 workflow contract as canonical state, with Python source compiled for preview/export
- AI Hub login or handoff-token verification, including account `display_name` for Runner identity labels
- Agent listing, config load/reload, public readonly config load, and Runner save-back through the AI Hub API
- Public readonly Runner mode for shared AI Hub Agents, with save/reload owner-only controls hidden outside editable sessions

Gateway execution, arbitrary Python execution, and SDK multimodal/structured modules are intentionally left for later implementation slices.