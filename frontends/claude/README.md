# Claude Code Proxy

LiteLLM proxy on Modal that routes Claude Code requests to open-source models.

## How it works

Claude Code sends requests using Anthropic model IDs (e.g. `claude-sonnet-4-5-20250929`). LiteLLM intercepts these, translates the Anthropic `/v1/messages` format to OpenAI format, and forwards them to the configured backend.

## Setup

1. Copy `.env.example` to `.env`.

2. In the `.env` file, update `LLM_BACKEND_URL` to point to your Modal-deployed LLM backend (including the `/v1` suffix) and add an `LLM_BACKEND_API_KEY` if necessary.

3. Deploy:

   ```bash
   uvx --with python-dotenv modal deploy litellm_proxy.py
   ```

## Configure Claude Code

Point Claude Code at the proxy:

```bash
export ANTHROPIC_BASE_URL=<your-proxy-url>
```

## Advanced configuration

Edit `litellm_config.yaml` to change the backend. For example, to use a different provider:

```yaml
- model_name: claude-sonnet-4-5-20250929
  litellm_params:
    model: openai/gpt-4o
    api_base: https://your-endpoint.com/v1
    api_key: "os.environ/YOUR_API_KEY"
```

Then redeploy.
