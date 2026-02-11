# sandproxy

LiteLLM proxy on Modal that routes Claude Code requests to open-source models.

## How it works

Claude Code sends requests using Anthropic model IDs (e.g. `claude-sonnet-4-5-20250929`). LiteLLM intercepts these, translates the Anthropic `/v1/messages` format to OpenAI format, and forwards them to the configured backend.

## Setup

1. Copy `.env.example` to `.env` and update `LLM_BACKEND_URL` to point to your Modal-deployed jazz backend (including `/v1` suffix).

2. Dev deploy (temporary endpoint for testing):

   ```bash
   modal serve app.py --env <your-environment>
   ```

3. Production deploy:

   ```bash
   modal deploy app.py --env <your-environment>
   ```

## Configure Claude Code

Point Claude Code at the proxy:

```bash
export ANTHROPIC_BASE_URL=<your-sandproxy-url>
```

## Model mapping

| Claude Code sends | Routed to |
|---|---|
| `claude-sonnet-4-5-20250929` | `llm` (jazz backend) |
| `claude-opus-4-6` | `llm` (jazz backend) |
| `claude-haiku-4-5-20251001` | `llm` (jazz backend) |

## Swapping providers/models

Edit `litellm_config.yaml` to change the backend. For example, to use a different provider:

```yaml
- model_name: claude-sonnet-4-5-20250929
  litellm_params:
    model: openai/gpt-4o
    api_base: https://your-endpoint.com/v1
    api_key: "os.environ/YOUR_API_KEY"
```

Then redeploy with `modal deploy app.py --env <your-environment>`.
