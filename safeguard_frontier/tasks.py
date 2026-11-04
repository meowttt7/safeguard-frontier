"""Inspect tasks, one per deployment profile. Run with, for example:

    uv run inspect eval safeguard_frontier/tasks.py@property -T condition=c0 \
        --model anthropic/claude-haiku-5-5 --epochs 3 --log-dir logs/property
    uv run inspect eval safeguard_frontier/tasks.py@trading -T condition=c3 \
        --model anthropic/claude-sonnet-5-5 --log-dir logs/trading

Conditions are listed in conditions.py. Scenarios live in profiles/<profile>/scenarios/.
"""

from __future__ import annotations

import json
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
from safeguard_frontier.profiles.registry import ProfileSpec, get_profile
from safeguard_frontier.scorers import all_scorers, attack_success


def load_scenarios(kinds: str = "all", attacks: str = "attack", profile: str = "property") -> list[dict[str, Any]]:
    """Load scenarios for a profile. `attacks` names the attack file stem (attack, attack_adaptive_..., attack_found_...)."""
    spec = get_profile(profile)
    wanted = {"benign", "attack"} if kinds == "all" else {k.strip() for k in kinds.split(",")}
    scenarios: list[dict[str, Any]] = []
    for kind in sorted(wanted):
        path = spec.scenario_dir / (f"{attacks}.json" if kind == "attack" else f"{kind}.json")
        with path.open(encoding="utf-8") as fh:
            items = json.load(fh)
        for item in items:
            item.setdefault("kind", kind)
            scenarios.append(item)
    ids = [s["id"] for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate scenario ids")
    return scenarios


def build_dataset(scenarios: list[dict[str, Any]], name: str = "scenarios") -> MemoryDataset:
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
    return MemoryDataset(samples, name=name)


@solver
def profile_solver(spec: ProfileSpec, condition: Condition) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = state.metadata["scenario"]
        env = spec.env_from_scenario(
            scenario,
            structural_scoping=condition.structural_scoping,
            quarantine=condition.quarantine,
        )
        store().set("condition", condition.name)
        store().set("profile", spec.name)
        store().set("deployment", spec.deployment)
        store().set("sources", env.sources_for_grader())
        store().set("canaries", spec.canaries)
        store().set("monitor_policy", spec.monitor_policy(env))
        prompt = spec.build_system_prompt(
            env,
            hardened=condition.hardened_prompt,
            quarantine=condition.quarantine,
            strict=condition.strict_prompt,
        )
        store().set("system_prompt", prompt)
        state.messages.insert(0, ChatMessageSystem(content=prompt))
        state.tools = spec.build_tools(env)
        state = await generate(state)
        store().set("call_log", env.call_log)
        return state

    return solve


def make_task(
    profile: str,
    condition: str = "c0",
    kinds: str = "all",
    attacks: str = "attack",
    grader: str = "anthropic/claude-sonnet-5-5",
    monitor: str = "anthropic/claude-haiku-5-5",
    scorer_set: str = "all",
) -> Task:
    """Build a task. scorer_set="attack" scores attack success only (used by the attacker search)."""
    spec = get_profile(profile)
    cond = CONDITIONS[condition]
    approval = [ApprovalPolicy(trusted_monitor(monitor), "*")] if cond.monitor else None
    scorers = all_scorers(grader) if scorer_set == "all" else [attack_success(grader)]
    return Task(
        dataset=build_dataset(load_scenarios(kinds, attacks, profile), name=profile),
        solver=profile_solver(spec, cond),
        scorer=scorers,
        approval=approval,
        config=GenerateConfig(max_tokens=4096),
        message_limit=30,
        name=f"{profile}_{condition}" + ("" if attacks == "attack" else f"_{attacks}"),
        metadata={
            "profile": profile,
            "condition": condition,
            "attacks": attacks,
            "description": cond.description,
        },
    )


@task
def property(
    condition: str = "c0",
    kinds: str = "all",
    attacks: str = "attack",
    grader: str = "anthropic/claude-sonnet-5-5",
    monitor: str = "anthropic/claude-haiku-5-5",
) -> Task:
    return make_task("property", condition, kinds, attacks, grader, monitor)


@task
def trading(
    condition: str = "c0",
    kinds: str = "all",
    attacks: str = "attack",
    grader: str = "anthropic/claude-sonnet-5-5",
    monitor: str = "anthropic/claude-haiku-5-5",
) -> Task:
    return make_task("trading", condition, kinds, attacks, grader, monitor)
