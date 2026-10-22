"""Start the existing AI-OS Qwen runtime on the Mac when this app selects it."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

# Run as a host script from the app directory, like the other local helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings


def ready(base_url: str, expected_model: str) -> bool:
    """Confirm that the local runtime is healthy and serves the configured model."""
    try:
        with urlopen(base_url + "/health", timeout=2) as response:
            if json.load(response).get("status") != "ok":
                return False
        with urlopen(base_url + "/v1/models", timeout=2) as response:
            models = json.load(response)["data"]
        if expected_model not in {model["id"] for model in models}:
            raise RuntimeError("A different model is already served on the configured port; preserved it")
        return True
    except URLError:
        return False


def main():
    """Reuse a running Qwen server, or launch AI-OS's existing server command with a local log."""
    settings = Settings()
    if settings.llm_provider != "qwen_local":
        return
    endpoint = urlsplit(settings.provider_base_url)
    base_url = f"http://127.0.0.1:{endpoint.port or 80}"
    if ready(base_url, settings.llm_model):
        print("Local Qwen is ready: " + settings.llm_model)
        return
    root = Path(os.environ.get("AIOS_ROOT", Path(__file__).resolve().parents[4]))
    if not (root / "py_dev/__main__.py").is_file():
        raise SystemExit("Run this helper on the Mac inside AI-OS, or set AIOS_ROOT to its existing checkout")
    reports = Path(__file__).resolve().parents[1] / "reports"
    reports.mkdir(exist_ok=True)
    environment = {**os.environ, "QWEN_BASE_URL": base_url + "/v1", "QWEN_MODEL": settings.llm_model}
    with (reports / "qwen-server.log").open("ab") as log:
        process = subprocess.Popen([sys.executable, "-m", "py_dev", "serve"], cwd=root, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(60):
        if ready(base_url, settings.llm_model):
            print("Started local Qwen: " + settings.llm_model)
            return
        if process.poll() is not None:
            raise SystemExit("Qwen could not start; inspect reports/qwen-server.log")
        time.sleep(1)
    raise SystemExit("Qwen is still loading; inspect reports/qwen-server.log before retrying")


if __name__ == "__main__":
    main()
