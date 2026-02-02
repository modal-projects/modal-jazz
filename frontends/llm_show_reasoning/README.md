### Installation

Build this directory and add it as a plugin to `llm`.

```bash
# If you don't have llm installed as a uv tool
uv tool install --with llm-uv-tool llm
# From this directory
uv build
llm install dist/llm_show_reasoning-0.1.0-py3-none-any.whl
```

Then attach the LLM backend to this frontend by setting the `api_base`
to its URL, including the `/v1`.

```bash
# Set once
llm models options set jazz api_base https://your-jazz-endpoint.com/v1

# Use like other models
llm -m jazz "your prompt"
```

### Advanced Usage

```bash
# Test after configuration
llm -m jazz "Explain the Modal serverless computing platform"

# Display reasoning in cyan with custom prefix
llm -m jazz -o reasoning_color cyan -o reasoning_prefix "🤔 " "your prompt"

# Disable reasoning display
llm -m jazz -o show_reasoning false "your prompt"

# Streaming is default, use --non-streaming for full response
llm -m jazz --non-streaming "your prompt"
```
