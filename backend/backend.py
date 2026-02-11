# Test (APP_USE_DUMMY_WEIGHTS=0 when testing GLM 5)
# ```bash
# APP_USE_DUMMY_WEIGHTS=1 modal run backend.py
# ```

# Deploy
# ```bash
# APP_USE_DUMMY_WEIGHTS=0 modal deploy backend.py
# ```

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path

import aiohttp
import modal
import modal.experimental

here = Path(__file__).parent

image = modal.Image.from_registry("lmsysorg/sglang:v0.5.8").entrypoint([])

image = image.uv_pip_install("transformers==5.0.0")

# patch SGLang and DeepGemm for GLM 5 support
image = (
    image.add_local_file(
        here / "glm5_support.patch",
        "/root/glm5_support.patch",
        copy=True,
    )
    .run_commands(
        "cd /sgl-workspace/sglang",
        "git fetch origin pull/18297/head:glm5_support",
        "git checkout glm5_support",
        "git apply /root/glm5_support.patch",
    )
    .run_commands(
        "rm -rf /root/.cache/deep_gemm/cache || true",
        "curl -L 'https://raw.githubusercontent.com/deepseek-ai/DeepGEMM/477618cd51baffca09c4b0b87e97c03fe827ef03/deep_gemm/include/deep_gemm/impls/sm100_fp8_mqa_logits.cuh' "
        "-o /usr/local/lib/python3.12/dist-packages/deep_gemm/include/deep_gemm/impls/sm100_fp8_mqa_logits.cuh",
    )
)

# TODO: download to `examples`
hf_cache_path = "/root/.cache/huggingface"
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)

USE_DUMMY_WEIGHTS = os.environ.get("APP_USE_DUMMY_WEIGHTS", "0") == "1"

image = image.env(
    {
        "HF_XET_HIGH_PERFORMANCE": "1",  # faster downloads
        "APP_USE_DUMMY_WEIGHTS": str(int(USE_DUMMY_WEIGHTS)),
        "SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN": "1",
        "SGLANG_JIT_DEEPGEMM_FAST_WARMUP": "1",
        "SGLANG_NSA_FORCE_MLA": "1",
        "SGLANG_LOCAL_IP_NIC": "overlay0",
    }
)


def download_model(repo_id, revision=None):
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo_id, revision=revision)


dg_cache_vol = modal.Volume.from_name("deepgemm-cache", create_if_missing=True)
dg_cache_path = "/root/.cache/deep_gemm"


REPO_ID = "zai-org/GLM-5-0127-FP8"


def compile_deep_gemm():
    import os

    if int(os.environ.get("SGLANG_ENABLE_JIT_DEEPGEMM", "1")):
        subprocess.run(
            f"python3 -m sglang.compile_deep_gemm --model-path {REPO_ID} --tp {GPU_COUNT}",
            shell=True,
        )


GPU_TYPE = "B200"
GPU_COUNT = 8
GPU = f"{GPU_TYPE}:{GPU_COUNT}"

# image = image.run_function(
#     compile_deep_gemm,
#     volumes={dg_cache_path: dg_cache_vol, hf_cache_path: hf_cache_vol},
#     gpu=GPU,
# )

if not USE_DUMMY_WEIGHTS:  # skip download if we don't need real weights
    image = image.run_function(
        download_model,
        volumes={"/root/.cache/huggingface": hf_cache_vol},
        args=(REPO_ID,),
    )

# ### Configure the inference engine

# **Environment variables**


def is_sglang_env_var(key):
    return key.startswith("SGL_") or key.startswith("SGLANG_")


image = image.env(
    {key: value for key, value in os.environ.items() if is_sglang_env_var(key)}
)

# **YAML**

local_config_path = os.environ.get("APP_LOCAL_CONFIG_PATH")

if modal.is_local():
    if local_config_path is None:
        local_config_path = here / "config.yaml"

    image = image.add_local_file(local_config_path, "/root/config.yaml")

# ** Command-line arguments**


def _start_server() -> subprocess.Popen:
    """Start SGLang server in a subprocess"""
    cmd = [
        f"HF_HUB_OFFLINE={1 - int(USE_DUMMY_WEIGHTS)}",
        "python",
        "-m",
        "sglang.launch_server",
        "--host",
        "0.0.0.0",
        "--port",
        str(SGLANG_PORT),
        "--model-path",
        REPO_ID,
        "--served-model-name",
        "llm",
        "--tp",
        str(GPU_COUNT),
        "--dp",
        str(GPU_COUNT),
        "--enable-dp-attention",
        "--config",
        "/root/config.yaml",
    ]

    if USE_DUMMY_WEIGHTS:
        cmd.extend(["--load-format", "dummy"])

    print("Starting SGLang server with command:")
    print(*cmd)

    return subprocess.Popen(" ".join(cmd), shell=True, start_new_session=True)


with image.imports():
    import sglang  # noqa

# ## Configure infrastructure

app = modal.App("jazz-backend", image=image)

REGION = "us"
PROXY_REGIONS = ["us-east"]


MIN_CONTAINERS = 1  # Set to 1 for production to keep a warm replica
TARGET_INPUTS = 10  # Concurrent requests per replica before scaling

# ### Define the server

SGLANG_PORT = 8000
MINUTES = 60  # seconds


@app.cls(
    image=image,
    gpu=f"{GPU_TYPE}:{GPU_COUNT}",
    scaledown_window=20 * MINUTES,  # how long should we stay up with no requests?
    timeout=30 * MINUTES,  # how long should we wait for container start?
    volumes={hf_cache_path: hf_cache_vol, dg_cache_path: dg_cache_vol},
    region=REGION,
    min_containers=MIN_CONTAINERS,
)
@modal.experimental.http_server(
    port=SGLANG_PORT,
    proxy_regions=["us-east"],
    exit_grace_period=25,  # time to finish requests on shutdown (seconds)
)
@modal.concurrent(target_inputs=TARGET_INPUTS)
class Server:
    @modal.enter()
    def start(self):
        """Start SGLang server process and wait for it to be ready"""
        self.proc = _start_server()
        wait_for_server_ready()

    @modal.exit()
    def stop(self):
        """Terminate the SGLang server process"""
        self.proc.terminate()
        self.proc.wait()


def wait_for_server_ready():
    """Wait for SGLang server to be ready"""
    import requests

    url = f"http://localhost:{SGLANG_PORT}/health"
    print(f"Waiting for server to be ready at {url}")

    while True:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print("Server is ready!")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)


# ## Test the server


@app.local_entrypoint()
async def test(test_timeout=60 * MINUTES, content=None, twice=True):
    """Test the model serving endpoint"""
    url = Server._experimental_get_flash_urls()[0]

    if USE_DUMMY_WEIGHTS:
        system_prompt = {"role": "system", "content": "This system produces gibberish."}
    else:
        system_prompt = {"role": "system", "content": "You are a helpful AI assistant."}

    if content is None:
        content = "Explain the transformer architecture in one paragraph."

    messages = [system_prompt, {"role": "user", "content": content}]

    print(f"Sending messages to {url}:", *messages, sep="\n\t")
    await probe(url, messages, timeout=test_timeout)

    if twice:
        messages[1]["content"] = "What is the capital of France?"
        print(f"Sending second request to {url}:", *messages, sep="\n\t")
        await probe(url, messages, timeout=1 * MINUTES)


async def probe(url, messages, timeout=60 * MINUTES):
    """Send request with retry logic for startup delays"""
    deadline = time.time() + timeout
    async with aiohttp.ClientSession(base_url=url) as session:
        while time.time() < deadline:
            try:
                await _send_request_streaming(session, messages)
                return
            except asyncio.TimeoutError:
                await asyncio.sleep(1)
            except aiohttp.client_exceptions.ClientResponseError as e:
                if e.status == 503:  # Service Unavailable during startup
                    await asyncio.sleep(1)
                    continue
                raise e
    raise TimeoutError(f"No response from server within {timeout} seconds")


async def _send_request_streaming(
    session: aiohttp.ClientSession, messages: list, timeout: int | None = None
):
    """Stream response from chat completions endpoint"""
    payload = {
        "messages": messages,
        "stream": True,
        "max_tokens": 1024 if USE_DUMMY_WEIGHTS else None,
    }
    headers = {"Accept": "text/event-stream"}

    async with session.post(
        "/v1/chat/completions", json=payload, headers=headers, timeout=timeout
    ) as resp:
        resp.raise_for_status()
        full_text = ""

        async for raw in resp.content:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            if not line.startswith("data:"):
                continue

            data = line[len("data:") :].strip()
            if data == "[DONE]":
                break

            try:
                evt = json.loads(data)
            except json.JSONDecodeError:
                continue

            delta = (evt.get("choices") or [{}])[0].get("delta") or {}
            chunk = delta.get("content") or delta.get("reasoning_content")

            if chunk:
                print(
                    chunk,
                    end="",
                    flush="\n" in chunk or "." in chunk or len(chunk) > 100,
                )
                full_text += chunk
        print()
