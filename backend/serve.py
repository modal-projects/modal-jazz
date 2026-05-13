import os
import re

import modal
import modal.experimental


def app_name_from_model(model_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model_name.split("/")[-1].lower()).strip("-")


MINUTES = 60
HOURS = 60 * MINUTES
DEFAULT_PORT = 8000
HF_CACHE_PATH = "/root/.cache/huggingface"
HF_CACHE_VOLUME_NAME = "huggingface-cache"
HF_IMAGE_ENV = {
    "HF_XET_HIGH_PERFORMANCE": "1",
    "HF_HUB_ENABLE_HF_TRANSFER": "1",
}

MODEL_NAME = "deepseek-ai/DeepSeek-V4-Pro"
app = modal.App("jazz-backend")

GPU_TYPE = "B200"
N_GPUS = 8
GPU = f"{GPU_TYPE}:{N_GPUS}"

SGLANG_IMAGE_TAG = "lmsysorg/sglang:deepseek-v4-blackwell"

DG_CACHE_DIR = "/root/dg-cache"
DG_CACHE_VOLUME_NAME = "dg-cache"

MIN_CONTAINERS = int(os.getenv("MIN_CONTAINERS", "0"))
SCALEDOWN_WINDOW = 20 * MINUTES
PROXY_REGIONS = os.getenv("PROXY_REGIONS", "us-east").split(",")
TARGET_INPUTS = 10
STARTUP_TIMEOUT = 3 * HOURS
WARMUP_REQUEST_TIMEOUT = 20 * MINUTES

HF_CACHE_VOL = modal.Volume.from_name(HF_CACHE_VOLUME_NAME)
DG_CACHE_VOL = modal.Volume.from_name(DG_CACHE_VOLUME_NAME, create_if_missing=True)

AUTOINFERENCE_UTILS_VERSION = "0.1.2"

ENV_VARS = {
    "CUDA_VISIBLE_DEVICES": ",".join(str(idx) for idx in range(N_GPUS)),
    "SGLANG_DG_CACHE_DIR": DG_CACHE_DIR,
    "SGLANG_ENABLE_SPEC_V2": "1",
    "SGLANG_ENABLE_THINKING": "1",
}


def patch_sglang_for_deepseek_v4():
    from pathlib import Path

    def sglang_file(relative_path: str) -> Path:
        roots = (
            Path("/workspace/sglang/python/sglang"),
            Path("/sgl-workspace/sglang/python/sglang"),
        )
        for root in roots:
            candidate = root / relative_path
            if candidate.exists():
                return candidate
        raise FileNotFoundError(relative_path)

    http_server_path = sglang_file("srt/entrypoints/http_server.py")
    http_server_src = http_server_path.read_text()
    keepalive_count = http_server_src.count("timeout_keep_alive=5")
    assert keepalive_count > 0 or "timeout_keep_alive=300" in http_server_src, (
        "Expected SGLang HTTP keepalive timeout target"
    )
    if keepalive_count:
        http_server_path.write_text(
            http_server_src.replace("timeout_keep_alive=5", "timeout_keep_alive=300")
        )

    protocol_path = sglang_file("srt/entrypoints/openai/protocol.py")
    protocol_src = protocol_path.read_text()
    protocol_old = """    @model_validator(mode="before")
    @classmethod
    def normalize_reasoning_inputs(cls, values: Dict):
        r = values.get("reasoning")
        if r is None:
            return values

        if isinstance(r, dict):
            effort = r.get("effort") or r.get("reasoning_effort")
            if effort in {"low", "medium", "high"}:
                values["reasoning_effort"] = effort

            enabled = (
                r.get("enabled")
                if r.get("enabled") is not None
                else r.get("enable", False)
            )
            if isinstance(enabled, str):
                enabled = enabled.strip().lower() in {"1", "true", "yes", "y", "on"}
            if enabled:
                ctk = values.get("chat_template_kwargs")
                if not isinstance(ctk, dict):
                    ctk = {}
                ctk.setdefault("thinking", True)
                values["chat_template_kwargs"] = ctk

        return values
"""
    protocol_new = """    @model_validator(mode="before")
    @classmethod
    def normalize_reasoning_inputs(cls, values: Dict):
        ctk = values.get("chat_template_kwargs")
        if not isinstance(ctk, dict):
            ctk = {}

        if "thinking" not in ctk:
            thinking = values.get("thinking")
            if isinstance(thinking, dict):
                thinking_type = thinking.get("type")
                if isinstance(thinking_type, str):
                    thinking_type = thinking_type.strip().lower()
                    if thinking_type == "enabled":
                        ctk["thinking"] = True
                    elif thinking_type == "disabled":
                        ctk["thinking"] = False
            elif isinstance(thinking, bool):
                ctk["thinking"] = thinking
            elif isinstance(thinking, str):
                thinking_type = thinking.strip().lower()
                if thinking_type in {"enabled", "true", "1", "yes", "y", "on"}:
                    ctk["thinking"] = True
                elif thinking_type in {"disabled", "false", "0", "no", "n", "off"}:
                    ctk["thinking"] = False

        r = values.get("reasoning")
        if isinstance(r, dict):
            effort = r.get("effort") or r.get("reasoning_effort")
            if effort in {"low", "medium", "high"}:
                values["reasoning_effort"] = effort

            enabled = (
                r.get("enabled")
                if r.get("enabled") is not None
                else r.get("enable", False)
            )
            if isinstance(enabled, str):
                enabled = enabled.strip().lower() in {"1", "true", "yes", "y", "on"}
            if enabled and "thinking" not in ctk:
                ctk["thinking"] = True

        ctk.setdefault("thinking", True)
        values["chat_template_kwargs"] = ctk
        return values
"""
    protocol_count = protocol_src.count(protocol_old)
    assert protocol_count == 1, (
        f"Expected 1 DeepSeek protocol patch target, found {protocol_count}"
    )
    protocol_path.write_text(protocol_src.replace(protocol_old, protocol_new))

    serving_chat_path = sglang_file("srt/entrypoints/openai/serving_chat.py")
    serving_chat_src = serving_chat_path.read_text()
    serving_chat_old = """        if self.reasoning_parser in ["deepseek-v3", "deepseek-v4"]:
            return (
                request.chat_template_kwargs is not None
                and request.chat_template_kwargs.get("thinking") is True
            )
"""
    serving_chat_new = """        if self.reasoning_parser in ["deepseek-v3", "deepseek-v4"]:
            if (
                request.chat_template_kwargs is not None
                and "thinking" in request.chat_template_kwargs
            ):
                return request.chat_template_kwargs.get("thinking") is True
            return envs.SGLANG_ENABLE_THINKING.get()
"""
    serving_chat_count = serving_chat_src.count(serving_chat_old)
    assert serving_chat_count == 1, (
        f"Expected 1 DeepSeek serving_chat patch target, found {serving_chat_count}"
    )
    serving_chat_path.write_text(
        serving_chat_src.replace(serving_chat_old, serving_chat_new)
    )
    print("[PATCH] Applied DeepSeek V4 SGLang deployment patches")


serving_image = (
    modal.Image.from_registry(SGLANG_IMAGE_TAG)
    .entrypoint([])
    .run_function(patch_sglang_for_deepseek_v4)
    .pip_install(f"autoinference-utils=={AUTOINFERENCE_UTILS_VERSION}")
    .env(HF_IMAGE_ENV)
    .env(ENV_VARS)
    .add_local_file(__file__, "/root/serve.py")
)

with serving_image.imports():
    from autoinference_utils.endpoint import (
        SGLangEndpoint,
        start_heartbeat_thread,
        warmup_chat_completions,
    )

ENGINE_MAX_RUNNING_REQUESTS = 32

SERVER_ARGS = {
    "--tool-call-parser": "deepseekv4",
    "--reasoning-parser": "deepseek-v4",
    "--trust-remote-code": "",
    "--mem-fraction-static": "0.82",
    "--chunked-prefill-size": "4096",
    "--moe-runner-backend": "flashinfer_mxfp4",
    "--collect-tokens-histogram": "",
    "--max-running-requests": str(ENGINE_MAX_RUNNING_REQUESTS),
    "--cuda-graph-max-bs": str(ENGINE_MAX_RUNNING_REQUESTS),
    # EAGLE speculative decoding, as recommended by the DeepSeek V4 recipe.
    "--speculative-algorithm": "EAGLE",
    "--speculative-num-steps": "3",
    "--speculative-eagle-topk": "1",
    "--speculative-num-draft-tokens": "4",
    "--disable-flashinfer-autotune": "",
}

WARMUP_PAYLOAD = {
    "model": MODEL_NAME,
    "messages": [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Reply with exactly OK."},
    ],
    "max_tokens": 16,
    "temperature": 0,
    "chat_template_kwargs": {"thinking": False},
}


@app.cls(
    image=serving_image,
    gpu=GPU,
    volumes={
        HF_CACHE_PATH: HF_CACHE_VOL,
        DG_CACHE_DIR: DG_CACHE_VOL,
    },
    region="us",
    min_containers=MIN_CONTAINERS,
    timeout=STARTUP_TIMEOUT,
    scaledown_window=SCALEDOWN_WINDOW,
    include_source=False,
    experimental_options={"override_eof_timeout": 30 * MINUTES},
)
@modal.experimental.http_server(
    port=DEFAULT_PORT,
    proxy_regions=PROXY_REGIONS,
    exit_grace_period=25,
    startup_timeout=STARTUP_TIMEOUT,
)
@modal.concurrent(target_inputs=TARGET_INPUTS)
class Server:
    @modal.enter()
    def startup(self):
        self.endpoint = SGLangEndpoint(
            model_path=MODEL_NAME,
            worker_port=DEFAULT_PORT,
            tp=N_GPUS,
            extra_server_args=SERVER_ARGS,
            health_timeout=STARTUP_TIMEOUT,
            health_poll_interval=10.0,
        )
        self.endpoint.start()
        warmup_chat_completions(
            port=DEFAULT_PORT,
            payload=WARMUP_PAYLOAD,
            successful_requests=3,
            request_timeout=WARMUP_REQUEST_TIMEOUT,
        )
        start_heartbeat_thread(
            self.endpoint.health_check,
            on_failure=lambda: modal.experimental.stop_fetching_inputs(),
        )
        print("DeepSeek-V4-Pro (8xB200) is ready to serve.")

    @modal.exit()
    def stop(self):
        if hasattr(self, "endpoint"):
            self.endpoint.stop()
