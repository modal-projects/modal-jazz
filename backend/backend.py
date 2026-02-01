# Test
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

image = modal.Image.from_registry("modalresearch/sglang:v0.5.7-fa4-preview").entrypoint(
    []
)

hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)

USE_DUMMY_WEIGHTS = os.environ.get("APP_USE_DUMMY_WEIGHTS", "0") == "1"

image = image.env(
    {
        "HF_XET_HIGH_PERFORMANCE": "1",  # faster downloads
        "APP_USE_DUMMY_WEIGHTS": str(int(USE_DUMMY_WEIGHTS)),
        "SGLANG_ENABLE_SPEC_V2": "1",
    }
)


def download_model(repo_id, revision=None):
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo_id, revision=revision)


REPO_ID = "zai-org/GLM-4.7-FP8"

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
        "--tp-size",
        str(GPU_COUNT),
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

GPU_TYPE = "B200"
GPU_COUNT = 4

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
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    region=REGION,
    min_containers=MIN_CONTAINERS,
)
@modal.experimental.http_server(
    port=SGLANG_PORT,
    proxy_regions=["us-east"],
    exit_grace_period=5 * MINUTES,  # time to finish requests on shutdown
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
async def test(test_timeout=20 * MINUTES, content=None, twice=True):
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


async def probe(url, messages, timeout=20 * MINUTES):
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
