"""Inspect tasks. Run with, for example:

    uv run inspect eval safeguard_frontier/tasks.py@property -T condition=c0 \
        --model anthropic/claude-haiku-5-5 --epochs 3 --log-dir logs/property

Conditions are listed in conditions.py. Scenarios live in profiles/property/scenarios/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspect_ai import Task, task
from inspect_ai.approval import ApprovalPolicy
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser, GenerateConfig
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import store

# Absolute imports: Inspect loads this file by path, outside the package, when run from the CLI.
from safeguard_frontier.conditions import CONDITIONS, Condition
from safeguard_frontier.monitor import trusted_monitor
from safeguard_frontier.profiles.property.env import PropertyEnv
from safeguard_frontier.profiles.property.prompts import build_system_prompt
from safeguard_frontier.profiles.property.tools import build_tools
from safeguard_frontier.scorers import all_scorers

SCENARIO_DIR = Path(__file__).parent / "profiles" / "property" / "scenarios"


def load_scenarios(kinds: str = "all", attacks: str = "attack") -> list[dict[str, Any]]:
    """Load scenarios. `attacks` names the attack file stem (attack, attack_adaptive_..., attack_found)."""
    wanted = {"benign", "attack"} if kinds == "all" else {k.strip() for k in kinds.split(",")}
    scenarios: list[dict[str, Any]] = []
    for kind in sorted(wanted):
        path = SCENARIO_DIR / (f"{attacks}.json" if kind == "attack" else f"{kind}.json")
        with path.open(encoding="utf-8") as fh:
            items = json.load(fh)
        for item in items:
            item.setdefault("kind", kind)
            scenarios.append(item)
    ids = [s["id"] for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate scenario ids")
    return scenarios


def build_dataset(scenarios: list[dict[str, Any]]) -> MemoryDataset:
    samples: list[Sample] = []
    for sc in scenarios:
        messages = []
        for m in sc["messages"]:
            if m["role"] == "user":
                messages.append(ChatMessageUser(content=m["content"]))
            elif m["role"] == "assistant":
                messages.append(ChatMessageAssistant(content=m["content"]))
            else:
                raise ValueError(f"unsupported role {m['role']!r} in scenario {sc['id']}")
        attack = sc.get("attack") or {}
        samples.append(
            Sample(
                id=sc["id"],
                input=messages,
                target=sc["kind"],
                metadata={
                    "scenario": sc,
                    "kind": sc["kind"],
                    "goal": attack.get("goal"),
                    "channel": attack.get("channel"),
                    "tier": attack.get("tier"),
                },
            )
        )
    return MemoryDataset(samples, name="property")


@solver
def property_solver(condition: Condition) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = state.metadata["scenario"]
        env = PropertyEnv.from_scenario(
            scenario,
            structural_scoping=condition.structural_scoping,
            quarantine=condition.quarantine,
        )
        store().set("tenant_id", env.tenant_id)
        store().set("condition", condition.name)
        store().set("sources", env.sources_for_grader())
        prompt = build_system_prompt(
            env,
            hardened=condition.hardened_prompt,
            quarantine=condition.quarantine,
            strict=condition.strict_prompt,
        )
        state.messages.insert(0, ChatMessageSystem(content=prompt))
        state.tools = build_tools(env)
        state = await generate(state)
        store().set("call_log", env.call_log)
        store().set("proposals", env.proposals)
        store().set("handoffs", env.handoffs)
        return state

    return solve


@task
def property(
    condition: str = "c0",
    kinds: str = "all",
    attacks: str = "attack",
    grader: str = "anthropic/claude-sonnet-5-5",
    monitor: str = "anthropic/claude-haiku-5-5",
) -> Task:
    cond = CONDITIONS[condition]
    approval = [ApprovalPolicy(trusted_monitor(monitor), "*")] if cond.monitor else None
    return Task(
        dataset=build_dataset(load_scenarios(kinds, attacks)),
        solver=property_solver(cond),
        scorer=all_scorers(grader),
        approval=approval,
        config=GenerateConfig(max_tokens=4096),
        message_limit=30,
        name=f"property_{condition}" + ("" if attacks == "attack" else f"_{attacks}"),
        metadata={
            "profile": "property",
            "condition": condition,
            "attacks": attacks,
            "description": cond.description,
        },
    )
