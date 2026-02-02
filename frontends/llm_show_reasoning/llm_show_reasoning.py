import json
import os
from typing import Iterable, Iterator, Optional

import httpx
import llm


@llm.hookimpl
def register_models(register):
    register(JazzReasoning(), aliases=("jazz",))

ANSI = {
    "reset": "\x1b[0m",
    "dim": "\x1b[2m",
    "gray": "\x1b[90m",
    "cyan": "\x1b[36m",
    "yellow": "\x1b[33m",
    "red": "\x1b[31m",
    "none": "",
}


class JazzReasoning(llm.KeyModel):
    """
    OpenAI-compatible Chat Completions client that also prints reasoning content.
    """

    model_id = "modal-jazz"
    can_stream = True
    supports_schema = True

    class Options(llm.Options):
        api_base: str = os.environ.get(
            "JAZZ_API_BASE",
            "https://PLEASE_CONFIGURE_JAZZ_API_BASE/v1"
        )
        upstream_model: str = "llm"
        show_reasoning: bool = True

        color_reasoning: bool = True
        reasoning_color: str = "dim"

        reasoning_prefix: Optional[str] = None
        reasoning_suffix: Optional[str] = "\n"

        temperature: Optional[float] = None
        max_tokens: Optional[int] = None

    def execute(
        self,
        prompt: llm.Prompt,
        stream: bool,
        response: llm.Response,
        conversation: Optional[llm.Conversation],
        key: Optional[str] = None,
    ) -> Iterable[str]:
        # Return an iterator of text chunks (sync streaming style).
        if stream:
            return self._streaming_iterator(prompt, response, conversation, key)
        else:
            return self._nonstream_iterator(prompt, response, conversation, key)

    def _build_messages(
        self, prompt: llm.Prompt, conversation: Optional[llm.Conversation]
    ):
        messages = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})

        # Minimal conversation support
        if conversation is not None:
            for prev in conversation.responses:
                # prev.prompt.prompt may be None for tool-only turns; skip those
                if getattr(prev.prompt, "prompt", None):
                    messages.append({"role": "user", "content": prev.prompt.prompt})
                text = prev.text()
                if text:
                    messages.append({"role": "assistant", "content": text})

        messages.append({"role": "user", "content": prompt.prompt or ""})
        return messages

    def _streaming_iterator(
        self,
        prompt: llm.Prompt,
        response: llm.Response,
        conversation: Optional[llm.Conversation],
        key: Optional[str],
    ) -> Iterator[str]:
        opts = prompt.options
        api_base = opts.api_base.rstrip("/")

        if "PLEASE_CONFIGURE_JAZZ_API_BASE" in api_base:
            raise ValueError(
                "Jazz API base URL is not configured.\n"
                "Set it with:\n"
                "     llm models options set jazz api_base https://your-endpoint.com/v1"
            )

        url = f"{api_base}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        else:
            headers["Authorization"] = "Bearer dummy"

        payload = {
            "model": opts.upstream_model,
            "stream": True,
            "messages": self._build_messages(prompt, conversation),
        }
        if opts.temperature is not None:
            payload["temperature"] = opts.temperature
        if opts.max_tokens is not None:
            payload["max_tokens"] = opts.max_tokens

        saw_reasoning = False

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, headers=headers, json=payload) as r:
                r.raise_for_status()
                for raw_line in r.iter_lines():
                    if not raw_line:
                        continue
                    if not raw_line.startswith("data: "):
                        continue

                    data = raw_line[6:].strip()
                    if data == "[DONE]":
                        break

                    evt = json.loads(data)

                    # Best-effort usage capture if your server sends it in-stream
                    if "usage" in evt and isinstance(evt["usage"], dict):
                        u = evt["usage"]
                        response.set_usage(
                            input=u.get("prompt_tokens"),
                            output=u.get("completion_tokens"),
                            total=u.get("total_tokens"),
                        )

                    choice = evt.get("choices", [{}])[0]
                    delta = choice.get("delta") or {}

                    rc = delta.get("reasoning_content")
                    if opts.show_reasoning and rc:
                        if not saw_reasoning:
                            saw_reasoning = True
                            if opts.reasoning_prefix:
                                yield opts.reasoning_prefix

                            if opts.color_reasoning:
                                yield ANSI.get(opts.reasoning_color, "")
                        yield rc

                    c = delta.get("content")
                    if c:
                        if saw_reasoning:
                            if opts.color_reasoning:
                                yield ANSI["reset"]
                            if opts.reasoning_suffix:
                                yield opts.reasoning_suffix
                                opts.reasoning_suffix = ""
                        yield c

                    c = delta.get("content")


    def _nonstream_iterator(
        self,
        prompt: llm.Prompt,
        response: llm.Response,
        conversation: Optional[llm.Conversation],
        key: Optional[str],
    ) -> Iterator[str]:
        opts = prompt.options
        api_base = opts.api_base.rstrip("/")

        if "PLEASE_CONFIGURE_JAZZ_API_BASE" in api_base:
            raise ValueError(
                "Jazz API base URL is not configured.\n"
                "Set it with one of these methods:\n"
                "  1. Export JAZZ_API_BASE environment variable:\n"
                "     export JAZZ_API_BASE='https://your-endpoint.com/v1'\n"
                "  2. Set persistent configuration:\n"
                "     llm models options set jazz api_base https://your-endpoint.com/v1"
            )

        url = f"{api_base}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        else:
            headers["Authorization"] = "Bearer dummy"

        payload = {
            "model": opts.upstream_model,
            "stream": False,
            "messages": self._build_messages(prompt, conversation),
        }
        if opts.temperature is not None:
            payload["temperature"] = opts.temperature
        if opts.max_tokens is not None:
            payload["max_tokens"] = opts.max_tokens

        with httpx.Client(timeout=None) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            evt = r.json()

        u = evt.get("usage")
        if isinstance(u, dict):
            response.set_usage(
                input=u.get("prompt_tokens"),
                output=u.get("completion_tokens"),
                total=u.get("total_tokens"),
            )

        msg = (evt.get("choices") or [{}])[0].get("message") or {}
        rc = msg.get("reasoning_content") or msg.get("reasoning")
        c = msg.get("content") or ""

        if opts.show_reasoning and rc:
            if opts.reasoning_prefix:
                yield opts.reasoning_prefix
            if opts.color_reasoning:
                yield ANSI.get(opts.reasoning_color, "")
            yield rc
            if opts.color_reasoning:
                yield ANSI["reset"]
            if opts.reasoning_suffix:
                yield opts.reasoning_suffix

        if c:
            yield c
