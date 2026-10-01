"""CLI for visible Py.Dev runtime configuration and local model runs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from urllib.parse import urlsplit

from .context_policy import ContextLimitError
from .local_runtime import LocalRuntimeError, _read_gguf_metadata, discover_binary, discover_gguf
from .runtime import AIOSRuntime, RuntimeInput
from .runtime_config import RuntimeConfigError
from .config import ModelSettings
from .models import ModelRequest
from .router import ModelRouter
from .skills import SkillCatalog, SkillError, SkillRunner
from .skill_state import SkillStateError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m py_dev")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "check", "run", "serve"):
        item = sub.add_parser(command)
        item.add_argument("--project")
        item.add_argument("--task")
        item.add_argument("--brain", default="auto", choices=("auto", "qwen", "openai", "claude"))
        item.add_argument("--model")
        item.add_argument("--reasoning", choices=("none", "low", "medium", "high", "xhigh"))
        item.add_argument("--context", choices=("small", "standard", "large", "very_large"))
        item.add_argument("--max-output", type=int)
        if command == "run":
            item.add_argument("--task-type", default="general")
            item.add_argument("--workflow", default="")
            item.add_argument("--task-id", default="")
            item.add_argument("--private", action="store_true")
            item.add_argument("--offline", action="store_true")
            item.add_argument("--review-with", choices=("qwen", "openai", "claude"))
            item.add_argument("--tool", action="append", default=[])
            item.add_argument("--no-verification", action="store_true")
    skill = sub.add_parser("skill", help="Resolve and run a canonical AI-OS Skill")
    skill.add_argument("skill_command", choices=("list", "run"))
    skill.add_argument("request", nargs="*")
    skill.add_argument("--project")
    skill.add_argument("--skill", dest="skill_name")
    skill.add_argument("--brain", default="auto", choices=("auto", "qwen", "openai", "claude"))
    skill.add_argument("--reasoning", choices=("none", "low", "medium", "high", "xhigh"))
    skill.add_argument("--context", choices=("small", "standard", "large", "very_large"))
    skill.add_argument("--max-output", type=int)
    skill.add_argument("--session-id")
    skill.add_argument("--answer")
    skill.add_argument("--question")
    skill.add_argument("--answer-status", choices=("unclassified", "confirmed", "hypothesis", "idea"), default="unclassified")
    return parser


def _overrides(args: argparse.Namespace) -> dict:
    overrides = {}
    for argument, field in (("brain", "provider"), ("model", "model"), ("reasoning", "reasoning"), ("context", "context"), ("max_output", "max_output")):
        value = getattr(args, argument, None)
        if value is not None and value != "auto":
            overrides[field] = "qwen_local" if field == "provider" and value == "qwen" else value
    if getattr(args, "tool", None):
        overrides["tools"] = args.tool
    if getattr(args, "no_verification", False):
        overrides["verification"] = False
    return overrides


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "skill":
            catalog = SkillCatalog()
            if args.skill_command == "list":
                for definition in catalog.skills.values():
                    print(f"${definition.name}\t{definition.description}")
                return 0
            prompt = " ".join(args.request).strip() or sys.stdin.read().strip()
            if not prompt and args.skill_name:
                prompt = f"Start ${args.skill_name}"
            if not prompt:
                raise SkillError("A Skill run needs a request or explicit --skill")
            execution = SkillRunner(catalog=catalog).run(
                prompt, project=args.project, skill=args.skill_name,
                overrides=_overrides(args), session_id=args.session_id,
                answer=args.answer, question=args.question, answer_status=args.answer_status,
            )
            if execution.result.response.degraded:
                print(f"Degraded: {execution.result.response.error}", file=sys.stderr)
                return 3
            print(f"Skill: {execution.skill.name if execution.skill else 'none'} | Provider: {execution.result.response.provider} | Task profile: {execution.skill.task_profile if execution.skill else 'general'}", file=sys.stderr)
            if execution.session_id:
                print(f"Interview session: {execution.session_id}", file=sys.stderr)
            print(execution.result.response.content)
            return 0
        # Preserve the original projectless auto-routing CLI for task/workflow policy.
        if (args.command == "run" and not args.project and not args.task and args.brain == "auto"
                and (args.task_type != "general" or args.workflow)
                and not (args.model or args.reasoning or args.context or args.max_output or args.tool or args.no_verification)):
            request = ModelRequest(
                messages=({"role": "user", "content": sys.stdin.read()},),
                task_type=args.task_type, task_id=args.task_id, workflow=args.workflow,
                brain="auto", review_with=args.review_with,
                privacy_requirement=args.private, offline_requirement=args.offline,
            )
            response = ModelRouter(ModelSettings.from_env()).run(request)
            if response.degraded:
                print(f"Degraded: {response.error}", file=sys.stderr)
                return 3
            print(response.content)
            if response.review:
                print(f"\nReview ({response.review.provider or 'unavailable'}):\n{response.review.content or response.review.error}")
            return 0
        runtime = AIOSRuntime()
        overrides = _overrides(args)
        config = runtime.resolve(project=args.project, task=args.task, overrides=overrides)
        provider = config.get("runtime", "provider")
        reasoning = config.get("reasoning", "default")
        context = config.values["context"].get("tier", "dynamic")
        if args.command == "serve":
            if provider != "qwen_local":
                raise RuntimeConfigError("serve requires the qwen_local provider")
            model_path = discover_gguf(config)
            gguf = _read_gguf_metadata(model_path)
            binary = discover_binary()
            endpoint = urlsplit(config.get("runtime", "endpoint"))
            context_size = config.get("context", "default_tokens") if context == "dynamic" else config.get("context", "tiers", context)
            if context_size > config.get("context", "default_tokens"):
                raise RuntimeConfigError("Starting above the default context requires prior model and runtime validation")
            native_context = gguf.get("qwen3.context_length")
            if gguf.get("general.architecture") != "qwen3" or not isinstance(native_context, int) or context_size > native_context:
                raise LocalRuntimeError("Selected Qwen GGUF does not support the configured startup context")
            command = [str(binary), "--model", str(model_path), "--alias", config.values["runtime"].get("model") or model_path.stem, "--host", "127.0.0.1", "--port", str(endpoint.port or 8080), "--ctx-size", str(context_size), "--parallel", "1", "--no-context-shift", "--reasoning-format", "deepseek"]
            layers = config.values["runtime"].get("gpu_layers", "auto")
            if layers != "auto":
                command.extend(["--n-gpu-layers", str(layers)])
            print(f"Starting Qwen from {model_path} with context {context_size}", file=sys.stderr)
            return subprocess.call(command)
        if provider == "qwen_local":
            report = runtime.check_local(config)
            model = report.model_alias
        else:
            report = None
            model = config.values["runtime"].get("model") or "configured by provider environment"
        print(f"Brain: {provider}\nModel: {model}\nReasoning: {reasoning}\nContext: {context}", file=sys.stderr)
        if report:
            print(f"Runtime: llama.cpp {report.binary_version.splitlines()[0]}\nQuantization: {report.quantization}\nEndpoint: {report.endpoint}\nServer context: {report.runtime_context}\nModel context: {report.model_context}", file=sys.stderr)
        if args.command == "status":
            return 0
        if args.command == "check":
            if report:
                print(f"GGUF: {report.gguf_path}\nGPU devices: {', '.join(report.gpu_devices) or 'none'}\nGPU layers requested: {report.gpu_layers_requested}\nGPU layers active: {report.gpu_layers_active}\nContext shift disabled: {report.context_shift_disabled}\nThinking toggle: {report.thinking_toggle}\nTemplate effort: {report.template_effort}\nReasoning budget verified: {report.budget_verified}", file=sys.stderr)
            return 0
        prompt = sys.stdin.read()
        result = runtime.run(RuntimeInput(
            prompt=prompt,
            project=args.project,
            task=args.task,
            task_id=args.task_id,
            task_type=args.task_type,
            workflow=args.workflow,
            review_with=args.review_with,
            private=args.private,
            offline=args.offline,
            overrides=overrides,
        ))
        if result.response.degraded:
            print(f"Degraded: {result.response.error}", file=sys.stderr)
            return 3
        if result.response.fallback_occurred:
            print(f"Fallback: {provider} -> {result.response.effective_provider}", file=sys.stderr)
        print(result.response.content)
        if result.response.review:
            print(f"\nReview ({result.response.review.provider or 'unavailable'}):\n{result.response.review.content or result.response.review.error}")
        return 0
    except (RuntimeConfigError, LocalRuntimeError, ContextLimitError, SkillError, SkillStateError, ValueError) as exc:
        print(f"AI-OS runtime: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
