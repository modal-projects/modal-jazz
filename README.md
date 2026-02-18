# 🎷 Modal Jazz

> The spirit of jazz is the spirit of openness.
>
> — Herbie Hancock, on software licensing

> I’ll play it first and tell you what it is later.
>
> — Miles Davis, on vibe-coding

This repository collects together a complete "open AI stack" --
everything you need to run a smart language model and the interfaces
that help it complete useful tasks. It uses [Modal](https://modal.com).

## Open Language Modeling Backend

The language model is [z.ai's GLM 5](https://docs.z.ai/guides/llm/glm-5).

It is run using:

- Nvidia B200 GPUs
- The [Modal](https://modal.com/) cloud deployment platform (project sponsor)
- The [SGLang inference server](https://github.com/sgl-project/sglang)
- The OpenAI-compatible API interface (based on `/chat/completions`).

To speed up the model weight downloading process, you'll need to add a
[Hugging Face](https://huggingface.co/) access token
stored as a [Modal Secret](https://modal.com/secrets).

For a single user, this achieves > 60 tok/s output.

You can also use a [free multitenant endpoint from Modal](https://modal.com/glm-5-endpoint).
The endpoint is free until April 30, 2026.
Users are limited to no more than one concurrent request.
See the instructions there for the API URL and authentication information.

## Open Frontends - `/frontends`

### Agentic Coding TUI + WebUI - OpenCode

[OpenCode](https://opencode.ai) is a terminal user interface
for connecting human users, language models, and computer terminals,
akin to Anthropic's [Claude Code](https://code.claude.com/docs/en/overview)
but with broader LLM API support.

We provide instructions for integrating the self-hosted LLM with OpenCode
and for deploying OpenCode servers on Modal
[here](./frontends/opencode/README.md)

### Agentic Assistant - OpenClaw

[OpenClaw](https://docs.openclaw.ai) is an agentic assistant system
designed for maximum integrability.

We provide instructions for integrating the self-hosted LLM with OpenClaw
[here](./frontends/openclaw/README.md).

### Chat Web UI - AI SDK

The [Vercel AI SDK](https://ai-sdk.dev/) offers both Core and UI sub SDKs
for integrating JavaScript applications with LLMs.

We demonstrate a simple integration of this stack with the self-hosted LLM --
both a "hello world"-level integration with a NodeJS CLI
[here](./frontends/ai_sdk_cli/README.md)
and a proper NextJS app
[here](./frontends/ai_sdk_react/README.md).

It is deployed [here](https://jazz.modal.chat).

### Chat CLI - `llm`

We like the [`llm` CLI tool from Simon Willison](https://github.com/simonw/llm)
for running quick LLM queries from the terminal.

It offers integration with OpenAI-compatible API providers, like our self-hosted LLM,
via the same interface as OpenAI's models.
Docs are [here](https://llm.datasette.io/en/stable/other-models.html).

We demonstrate a small plugin in [`llm_show_reasoning`](./frontends/llm_show_reasoning/README.md)
that prints the LLM's reasoning output -- not available from OpenAI reasoning models,
but available for open models. This reduces apparent latency.
