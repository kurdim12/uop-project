"""
One-shot deploy of this project to a Hugging Face Docker Space.

This avoids any git-remote setup: it creates the Space (if needed) and uploads
the whole project folder. The Dockerfile + the README front-matter then build
and run the app on Hugging Face automatically.

Usage:
    pip install huggingface_hub
    # Get a WRITE token: https://huggingface.co/settings/tokens
    export HF_TOKEN=hf_xxxxxxxx            # macOS/Linux
    #  set    HF_TOKEN=hf_xxxxxxxx         # Windows (cmd)
    #  $env:HF_TOKEN="hf_xxxxxxxx"         # Windows (PowerShell)

    python deploy_hf.py YOUR_HF_USERNAME             # space -> raw-smith-circle
    python deploy_hf.py YOUR_HF_USERNAME my-space    # custom space name
"""
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    sys.exit("Missing dependency. Run:  pip install huggingface_hub")

# Never upload local-only or generated files to the Space.
IGNORE = [
    ".git*",
    ".venv*",
    "venv*",
    "**/__pycache__*",
    "*.pyc",
    "db.sqlite3",
    "staticfiles*",
    ".env",
]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python deploy_hf.py <hf_username> [space_name]")

    username = sys.argv[1]
    space_name = sys.argv[2] if len(sys.argv) > 2 else "raw-smith-circle"
    repo_id = f"{username}/{space_name}"

    # Token from HF_TOKEN env var, or fall back to a cached `huggingface-cli login`.
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)

    print(f"Creating/locating Space: {repo_id} ...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
    )

    print("Uploading project files (this can take a minute) ...")
    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(Path(__file__).resolve().parent),
        ignore_patterns=IGNORE,
        commit_message="Deploy Raw Smith Circle",
    )

    print("\nDone. The Space is building now.")
    print(f"  App (live shortly): https://{username}-{space_name}.hf.space")
    print(f"  Build logs:         https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()
