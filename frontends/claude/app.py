import modal

LITELLM_PORT = 4000

litellm_image = (
    modal.Image.from_registry(
        "docker.litellm.ai/berriai/litellm:main-latest",
    )
    .entrypoint([])
    .pip_install("grpclib")
    .add_local_file(
        "litellm_config.yaml",
        remote_path="/app/config.yaml",
        copy=True,
    )
)

app = modal.App("sandproxy", image=litellm_image)


@app.function(
    scaledown_window=300,
    timeout=600,
)
@modal.concurrent(max_inputs=100)
@modal.web_server(port=LITELLM_PORT, startup_timeout=120)
def serve():
    import subprocess

    subprocess.Popen(
        [
            "litellm",
            "--config", "/app/config.yaml",
            "--host", "0.0.0.0",
            "--port", str(LITELLM_PORT),
        ]
    )
