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

The language model is [Zhipu AI's GLM 4.7](https://docs.z.ai/guides/llm/glm-4.7).

It is run using:

- Nvidia B200 GPUs
- The [Modal](https://modal.com/) cloud deployment platform (project sponsor)
- The [SGLang inference server](https://github.com/sgl-project/sglang)
  - in a [custom build](https://hub.docker.com/layers/modalresearch/sglang/v0.5.7-fa4-preview/images/sha256-a0fe42112f9c90aed2571816bef9b4cb46ba0a7872c63e7b94fe514ac303993b)
  with improved support for [Flash Attention 4](https://modal.com/blog/reverse-engineer-flash-attention-4)
- The OpenAI-compatible API interface (based on `/chat/completions`).

For a single user, this achieves > 100 tok/s output,
roughly in line with [performance reported in Artificial Analysis](https://artificialanalysis.ai/models/glm-4-7-non-reasoning).

## Open Frontends - `/frontends`

### Agentic Coding TUI + WebUI - OpenCode

[OpenCode](https://opencode.ai) is a terminal user interface
for connecting human users, language models, and computer terminals,
akin to Anthropic's [Claude Code](https://code.claude.com/docs/en/overview)
but with broader LLM API support.

We provide instructions for integrating the self-hosted LLM with OpenCode
and for deploying OpenCode servers on Modal.

### Chat Web UI - AI SDK

The [Vercel AI SDK](https://ai-sdk.dev/) offers both Core and UI sub SDKs
for integrating JavaScript applications with LLMs.

We demonstrate a simple integration of this stack with the self-hosted LLM --
both a "hello world"-level integration with a NodeJS CLI
and a proper NextJS app.

It is deployed [here](https://jazz.modal.chat).

### Chat CLI - `llm`

We like the [`llm` CLI tool from Simon Willison](https://github.com/simonw/llm)
for running quick LLM queries from the terminal.

It offers integration with OpenAI-compatible API providers, like our self-hosted LLM,
via the same interface as OpenAI's models.
Docs are [here](https://llm.datasette.io/en/stable/other-models.html).

We demonstrate a small plugin in `llm_show_reasoning`
that prints the LLM's reasoning output -- not available from OpenAI reasoning models,
but available for open models). This reduces apparent latency.
