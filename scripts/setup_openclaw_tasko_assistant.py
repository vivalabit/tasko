#!/usr/bin/env python3
"""Create or update Tasko's isolated OpenClaw assistant agent."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

AGENT_ID = "tasko-assistant"
DEFAULT_MODEL = "openai/gpt-5.4-mini"
REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "openclaw" / AGENT_ID


def run_openclaw(command: str, *args: str) -> str:
    completed = subprocess.run(
        [command, *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def load_agents(command: str) -> list[dict[str, Any]]:
    raw = run_openclaw(command, "config", "get", "agents.list", "--json")
    agents = json.loads(raw)
    if not isinstance(agents, list):
        raise RuntimeError("OpenClaw agents.list is not an array")
    return agents


def install_workspace(home: Path) -> Path:
    workspace = home / ".openclaw" / f"workspace-{AGENT_ID}"
    workspace.mkdir(parents=True, exist_ok=True)
    for template in TEMPLATE_DIR.iterdir():
        if template.is_file():
            destination = workspace / template.name
            if template.name == "AGENTS.md" or not destination.exists():
                shutil.copyfile(template, destination)
    (workspace / "memory").mkdir(exist_ok=True)
    return workspace


def configure_agent(command: str, workspace: Path, model: str) -> None:
    agents = load_agents(command)
    index = next(
        (index for index, agent in enumerate(agents) if agent.get("id") == AGENT_ID),
        None,
    )
    if index is None:
        run_openclaw(
            command,
            "agents",
            "add",
            AGENT_ID,
            "--workspace",
            str(workspace),
            "--model",
            model,
            "--non-interactive",
            "--json",
        )
        agents = load_agents(command)
        index = next(
            index for index, agent in enumerate(agents) if agent.get("id") == AGENT_ID
        )

    prefix = f"agents.list[{index}]"
    operations = [
        {"path": f"{prefix}.name", "value": "Tasko Assistant"},
        {"path": f"{prefix}.workspace", "value": f"~/.openclaw/workspace-{AGENT_ID}"},
        {"path": f"{prefix}.agentDir", "value": f"~/.openclaw/agents/{AGENT_ID}/agent"},
        {
            "path": f"{prefix}.model",
            "value": {"primary": model, "fallbacks": []},
        },
        {
            "path": f"{prefix}.models",
            "value": {model: {"agentRuntime": {"id": "openclaw"}}},
        },
        {"path": f"{prefix}.thinkingDefault", "value": "off"},
        {"path": f"{prefix}.reasoningDefault", "value": "off"},
        {"path": f"{prefix}.fastModeDefault", "value": True},
        {"path": f"{prefix}.verboseDefault", "value": "off"},
        {"path": f"{prefix}.skills", "value": []},
        {"path": f"{prefix}.contextInjection", "value": "continuation-skip"},
        {"path": f"{prefix}.bootstrapMaxChars", "value": 4_000},
        {"path": f"{prefix}.bootstrapTotalMaxChars", "value": 5_000},
        {
            "path": f"{prefix}.params",
            "value": {"maxTokens": 1_200, "cacheRetention": "short"},
        },
        {
            "path": f"{prefix}.tools",
            "value": {
                "profile": "minimal",
                "allow": [],
                "deny": ["*"],
                "elevated": {"enabled": False},
            },
        },
    ]
    run_openclaw(
        command,
        "config",
        "set",
        "--batch-json",
        json.dumps(operations, separators=(",", ":")),
        "--strict-json",
    )
    run_openclaw(command, "config", "validate")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command",
        default=os.environ.get("OPENCLAW_COMMAND", "openclaw"),
        help="OpenClaw executable (default: OPENCLAW_COMMAND or openclaw)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("TASKO_ASSISTANT_MODEL", DEFAULT_MODEL),
        help=f"Model for the isolated agent (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    command = shutil.which(args.command)
    if not command:
        parser.error(f"OpenClaw executable was not found: {args.command}")

    workspace = install_workspace(Path.home())
    try:
        configure_agent(command, workspace, args.model)
    except (subprocess.CalledProcessError, json.JSONDecodeError, RuntimeError) as exc:
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        print(f"Failed to configure {AGENT_ID}: {exc}", file=sys.stderr)
        return 1

    print(f"Configured {AGENT_ID} with isolated workspace {workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
