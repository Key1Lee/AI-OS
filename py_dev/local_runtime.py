"""Read-only startup checks for a loopback llama.cpp Qwen server."""

from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .providers.qwen_local import _local_base_url
from .runtime_config import ResolvedConfig


class LocalRuntimeError(RuntimeError):
    pass


_GGUF_SCALARS = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?", 10: "Q", 11: "q", 12: "d"}
_GGUF_QUANTIZATION = {14: "Q4_K_S", 15: "Q4_K_M"}


def _read_gguf_metadata(path: Path) -> dict[str, Any]:
    """Read selected header fields without loading tokenizer arrays or model tensors."""
    wanted = {"general.architecture", "general.name", "general.file_type", "qwen3.context_length"}
    try:
        with path.open("rb") as stream:
            if stream.read(4) != b"GGUF":
                raise ValueError("missing GGUF magic")
            version, _, count = struct.unpack("<IQQ", stream.read(20))
            if version not in (2, 3) or count > 10000:
                raise ValueError("unsupported GGUF header")

            def read_exact(size: int) -> bytes:
                value = stream.read(size)
                if len(value) != size:
                    raise ValueError("truncated GGUF metadata")
                return value

            def read_value(kind: int, *, keep: bool) -> Any:
                if kind == 8:
                    size = struct.unpack("<Q", read_exact(8))[0]
                    if size > path.stat().st_size:
                        raise ValueError("invalid GGUF string length")
                    if keep:
                        return read_exact(size).decode("utf-8")
                    stream.seek(size, 1)
                    return None
                if kind == 9:
                    item_kind, size = struct.unpack("<IQ", read_exact(12))
                    if size > path.stat().st_size:
                        raise ValueError("invalid GGUF array length")
                    for _ in range(size):
                        read_value(item_kind, keep=False)
                    return None
                if kind not in _GGUF_SCALARS:
                    raise ValueError("unsupported GGUF metadata type")
                fmt = "<" + _GGUF_SCALARS[kind]
                value = struct.unpack(fmt, read_exact(struct.calcsize(fmt)))[0]
                return value if keep else None

            result: dict[str, Any] = {"gguf_version": version}
            for _ in range(count):
                size = struct.unpack("<Q", read_exact(8))[0]
                if size > 512:
                    raise ValueError("invalid GGUF metadata key")
                key = read_exact(size).decode("utf-8")
                kind = struct.unpack("<I", read_exact(4))[0]
                value = read_value(kind, keep=key in wanted)
                if key in wanted:
                    result[key] = value
            return result
    except (OSError, UnicodeDecodeError, struct.error, ValueError) as exc:
        raise LocalRuntimeError(f"Cannot read GGUF metadata from {path}: {exc}") from exc


@dataclass(frozen=True)
class LocalRuntimeReport:
    gguf_path: Path
    filename: str
    quantization: str
    model_alias: str
    metadata: dict[str, Any]
    binary_path: Path
    binary_version: str
    gpu_devices: tuple[str, ...]
    gpu_layers_requested: str | int
    gpu_layers_active: str | int | None
    context_shift_disabled: bool | None
    runtime_context: int
    model_context: int
    endpoint: str
    thinking_toggle: bool
    template_effort: bool
    budget_advertised: bool
    budget_verified: bool


def _get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise LocalRuntimeError(f"Local llama.cpp endpoint is unavailable: {url}") from exc
    if not isinstance(data, dict):
        raise LocalRuntimeError(f"Invalid response from local endpoint: {url}")
    return data


def _post_json(url: str, payload: dict[str, Any], timeout: float = 20.0) -> dict[str, Any]:
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise LocalRuntimeError(f"Local llama.cpp request failed: {url}") from exc
    if not isinstance(data, dict):
        raise LocalRuntimeError("Local llama.cpp returned invalid JSON")
    return data


def discover_gguf(config: ResolvedConfig) -> Path:
    explicit = config.values["runtime"].get("model_path")
    if explicit:
        path = Path(explicit).expanduser().resolve()
    else:
        model_dir = Path(config.get("runtime", "model_dir")).expanduser()
        matches = sorted(model_dir.glob("*Qwen*.gguf")) if model_dir.is_dir() else []
        if len(matches) != 1:
            raise LocalRuntimeError(f"Expected one Qwen GGUF in {model_dir}; found {len(matches)}. Set a per-run model_path if needed")
        path = matches[0].resolve()
    if not path.is_file() or path.stat().st_size < 1024:
        raise LocalRuntimeError(f"Qwen GGUF is missing or too small: {path}")
    with path.open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise LocalRuntimeError(f"Model file is not GGUF: {path}")
    return path


def discover_binary() -> Path:
    candidates = [shutil.which("llama-server"), Path.home() / ".docker" / "bin" / "inference" / "llama-server", Path("/opt/homebrew/bin/llama-server"), Path("/usr/local/bin/llama-server")]
    for item in candidates:
        if item and Path(item).is_file():
            return Path(item).resolve()
    raise LocalRuntimeError("llama-server binary was not found on PATH or in known local install locations")


def _binary_info(binary: Path) -> tuple[str, tuple[str, ...], bool]:
    try:
        version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=15, check=True)
        devices = subprocess.run([str(binary), "--list-devices"], capture_output=True, text=True, timeout=15, check=True)
        help_text = subprocess.run([str(binary), "--help"], capture_output=True, text=True, timeout=15, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise LocalRuntimeError(f"llama-server binary cannot be inspected: {binary}") from exc
    listed = tuple(line.strip() for line in (devices.stdout + devices.stderr).splitlines() if line.strip().startswith(("MTL", "CUDA", "Vulkan", "ROCm")))
    return (version.stdout + version.stderr).strip(), listed, "--reasoning-budget" in (help_text.stdout + help_text.stderr)


def _active_server_options(binary: Path, model_path: Path) -> tuple[str | int | None, bool | None]:
    try:
        processes = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True, timeout=5, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None, None
    for line in processes.stdout.splitlines():
        if str(binary) not in line or str(model_path) not in line or "--model" not in line:
            continue
        match = re.search(r"(?:--n-gpu-layers|--gpu-layers|-ngl)\s+(\S+)", line)
        active = match.group(1) if match else "auto"
        if isinstance(active, str) and active.isdigit():
            active = int(active)
        return active, "--no-context-shift" in line
    return None, None


def inspect_local(config: ResolvedConfig, *, probe_budget: bool = False) -> LocalRuntimeReport:
    if config.get("runtime", "provider") != "qwen_local":
        raise LocalRuntimeError("Local runtime inspection requires qwen_local")
    path = discover_gguf(config)
    gguf = _read_gguf_metadata(path)
    if gguf.get("general.architecture") != "qwen3":
        raise LocalRuntimeError(f"Selected GGUF is not a Qwen3 model: {path}")
    quant = _GGUF_QUANTIZATION.get(gguf.get("general.file_type"))
    if quant is None:
        raise LocalRuntimeError(f"Unsupported or unknown GGUF quantization type: {gguf.get('general.file_type')}")
    binary = discover_binary()
    version, devices, budget_advertised = _binary_info(binary)
    requested_gpu = config.values["runtime"].get("gpu_layers", "auto")
    if requested_gpu != "auto" and (not isinstance(requested_gpu, int) or requested_gpu < 0):
        raise LocalRuntimeError("GPU layers must be auto or a nonnegative integer")
    if isinstance(requested_gpu, int) and requested_gpu > 0 and not devices:
        raise LocalRuntimeError("GPU offload was requested but no llama.cpp GPU device is available")
    endpoint = _local_base_url(config.get("runtime", "endpoint"))
    origin = endpoint.removesuffix("/v1")
    health = _get_json(origin + "/health")
    if health.get("status") != "ok":
        raise LocalRuntimeError("llama.cpp health endpoint is not ready")
    models = _get_json(endpoint + "/models").get("data", [])
    if not isinstance(models, list) or len(models) != 1 or not isinstance(models[0], dict):
        raise LocalRuntimeError("Expected exactly one loaded local model")
    model = models[0]
    alias = model.get("id")
    requested_alias = config.values["runtime"].get("model")
    if not isinstance(alias, str) or (requested_alias and alias != requested_alias):
        raise LocalRuntimeError(f"Loaded model identity differs from configured model: {requested_alias or path.stem}")
    props = _get_json(origin + "/props")
    reported_path = props.get("model_path")
    if not isinstance(reported_path, str) or Path(reported_path).expanduser().resolve() != path:
        raise LocalRuntimeError(f"Server model path differs from GGUF selected by AI-OS: {path}")
    metadata = model.get("meta", {})
    if not isinstance(metadata, dict):
        raise LocalRuntimeError("Model metadata is unavailable")
    model_context = metadata.get("n_ctx_train")
    runtime_context = props.get("default_generation_settings", {}).get("n_ctx")
    if not isinstance(model_context, int) or model_context <= 0 or not isinstance(runtime_context, int) or runtime_context <= 0:
        raise LocalRuntimeError("Model or server context limit is unavailable")
    if gguf.get("qwen3.context_length") != model_context:
        raise LocalRuntimeError("GGUF native context differs from llama.cpp model metadata")
    if runtime_context > model_context and not config.values["context"].get("allow_extended", False):
        raise LocalRuntimeError("Server context exceeds model metadata without an explicit extended-context policy")
    template = props.get("chat_template", "")
    if not isinstance(template, str):
        template = ""
    active_layers, no_shift = _active_server_options(binary, path)
    if no_shift is not True:
        raise LocalRuntimeError("Cannot verify --no-context-shift on the active llama-server; restart with that flag to protect instructions from silent truncation")
    if isinstance(active_layers, int) and active_layers > 0 and not devices:
        raise LocalRuntimeError("Active GPU offload requests layers but llama.cpp reports no GPU device")
    report = LocalRuntimeReport(path, path.name, quant, alias, {**metadata, "gguf": gguf}, binary, version, devices, requested_gpu, active_layers, no_shift, runtime_context, model_context, endpoint, "enable_thinking" in template, "reasoning_effort" in template, budget_advertised, False)
    if probe_budget and report.thinking_toggle and report.budget_advertised:
        report = replace(report, budget_verified=_verify_budget(report))
    return report


def _verify_budget(report: LocalRuntimeReport) -> bool:
    base = {"model": report.model_alias, "messages": [{"role": "user", "content": "Reply with exactly: ready"}], "temperature": 0, "max_tokens": 128, "reasoning_format": "deepseek", "chat_template_kwargs": {"enable_thinking": True}}
    try:
        normal = _post_json(report.endpoint + "/chat/completions", base)
        limited = _post_json(report.endpoint + "/chat/completions", {**base, "reasoning_budget_tokens": 0})
        normal_reasoning = normal["choices"][0]["message"].get("reasoning_content") or ""
        limited_reasoning = limited["choices"][0]["message"].get("reasoning_content") or ""
        return bool(normal_reasoning and not limited_reasoning and limited["choices"][0]["message"].get("content"))
    except (LocalRuntimeError, KeyError, IndexError, TypeError):
        return False
