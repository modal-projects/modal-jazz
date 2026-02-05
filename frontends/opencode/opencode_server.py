"""
Launch an OpenCode server on Modal with a GitHub repo cloned.

Supports configurable timeout, custom app names, Modal credential management,
Git repository cloning with authentication, and local config file inclusion.

By default, clones the Modal Examples repo:
    https://github.com/modal-labs/modal-examples
"""

import argparse
import os
import secrets
from pathlib import Path

import modal

OPENCODE_PORT = 4096
HERE = Path(__file__).parent
DEFAULT_GITHUB_REPO = "modal-labs/modal-examples"


def main(
    timeout: int,
    app_name: str,
    allow_modal_access: bool,
    github_repo: str,
    github_ref: str,
    github_token: str | None,
):
    app = modal.App.lookup(app_name, create_if_missing=True)
    image = define_base_image()
    if allow_modal_access:
        image = add_modal_access(image)

    image = clone_github_repo(image, github_repo, github_ref, github_token)
    working_dir = "/root/code"

    password = secrets.token_urlsafe(13)
    password_secret = modal.Secret.from_dict({"OPENCODE_SERVER_PASSWORD": password})

    sandbox = create_sandbox(image, timeout, app, password_secret, working_dir)
    print_access_info(sandbox, password)


def define_base_image() -> modal.Image:
    image = (
        modal.Image.debian_slim()
        .apt_install("curl", "git")
        .run_commands("curl -fsSL https://opencode.ai/install | bash")
        .env({"PATH": "/root/.opencode/bin:${PATH}"})
    )

    CONFIG_PATH = HERE / "opencode.json"
    if CONFIG_PATH.exists():
        print("🏖️  Including config from", CONFIG_PATH)
        image = image.add_local_file(CONFIG_PATH, "/root/.config/opencode/opencode.json", copy=True)

    return image


def create_sandbox(
    image: modal.Image,
    timeout: int,
    app: modal.App,
    password_secret: modal.Secret,
    working_dir: str | None = None,
) -> modal.Sandbox:
    print("🏖️  Creating sandbox")

    with modal.enable_output():
        sandbox = modal.Sandbox.create(
            "opencode",
            "serve",
            "--hostname=0.0.0.0",
            f"--port={OPENCODE_PORT}",
            "--log-level=DEBUG",
            "--print-logs",
            encrypted_ports=[OPENCODE_PORT],
            secrets=[password_secret],
            timeout=timeout,
            image=image,
            app=app,
            workdir=working_dir,
        )

    return sandbox


def clone_github_repo(
    image: modal.Image, repo: str, ref: str, token: str | None = None
) -> modal.Image:
    git_config = "git config --global advice.detachedHead false"

    if token:
        clone_cmd = f"GIT_ASKPASS=echo git clone --quiet --depth 1 --branch {ref} https://oauth2:{token}@github.com/{repo}.git /root/code"
    else:
        clone_cmd = f"GIT_TERMINAL_PROMPT=0 git clone --quiet --depth 1 --branch {ref} https://github.com/{repo}.git /root/code"

    print(f"🏖️  Cloning {repo}@{ref} to /root/code")
    image = image.run_commands(git_config, clone_cmd, force_build=True)

    return image


def add_modal_access(image: modal.Image) -> modal.Image:
    image = image.uv_pip_install("modal", "fastapi~=0.128.0")

    modal_token_id = os.environ.get("MODAL_TOKEN_ID")
    modal_token_secret = os.environ.get("MODAL_TOKEN_SECRET")

    if modal_token_id and modal_token_secret:
        return image.env(
            {"MODAL_TOKEN_ID": modal_token_id, "MODAL_TOKEN_SECRET": modal_token_secret}
        )

    MODAL_PATH = (Path("~") / ".modal.toml").expanduser()
    if MODAL_PATH.exists():
        print("🏖️  Including Modal auth from", MODAL_PATH)
        return image.add_local_file(MODAL_PATH, "/root/.modal.toml", copy=True)

    raise EnvironmentError(
        "No Modal credentials found. "
        "Either set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET environment variables, "
        "or ensure .modal.toml exists in your home directory."
    )


def print_access_info(sandbox: modal.Sandbox, password: str):
    print(
        "🏖️  Access the sandbox directly:",
        f"modal shell {sandbox.object_id}",
        sep="\n\t",
    )

    tunnel = sandbox.tunnels()[OPENCODE_PORT]
    print(
        "🏖️  Access the WebUI",
        f"{tunnel.url}",
        "Username: opencode",
        f"Password: {password}",
        sep="\n\t",
    )
    print(
        "🏖️  Access the TUI:",
        f"OPENCODE_SERVER_PASSWORD={password} opencode attach {tunnel.url}",
        sep="\n\t",
    )


def parse_timeout(timeout_str: str) -> int:
    if timeout_str.endswith("h"):
        minutes = int(timeout_str[:-1]) * 60
    elif timeout_str.endswith("m"):
        minutes = int(timeout_str[:-1])
    else:
        minutes = int(timeout_str) * 60

    if minutes < 1:
        raise argparse.ArgumentTypeError("Timeout must be at least 1 minute")
    if minutes > 24 * 60:
        raise argparse.ArgumentTypeError("Timeout cannot exceed 24 hours")

    return minutes * 60  # timeout in seconds


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch OpenCode server on Modal")
    parser.add_argument(
        "--timeout",
        type=str,
        default="12",
        help="Server timeout (e.g. 2h, 90m). No suffix -> hours. Default: 12",
    )
    parser.add_argument(
        "--app-name",
        type=str,
        default="modal-jazz-opencode-server",
        help="Modal app name. Default: modal-jazz-opencode-server",
    )
    parser.add_argument(
        "--no-allow-modal-access",
        action="store_false",
        dest="allow_modal_access",
        default=True,
        help="Disable Modal credential access",
    )
    parser.add_argument(
        "--github-repo",
        type=str,
        default=DEFAULT_GITHUB_REPO,
        help=f"GitHub repository in owner/repo format. Default: {DEFAULT_GITHUB_REPO}",
    )
    parser.add_argument(
        "--github-ref",
        type=str,
        default="main",
        help="Git reference to checkout (branch, tag, or SHA). Default: main",
    )
    parser.add_argument(
        "--github-token",
        type=str,
        default=None,
        help="GitHub personal access token for private repositories",
    )
    args = parser.parse_args()

    main(
        parse_timeout(args.timeout),
        args.app_name,
        args.allow_modal_access,
        args.github_repo,
        args.github_ref,
        args.github_token,
    )
