"""Run the condition matrix for one model: every condition on the standard scenario set and, if given,
on the adaptive variants that beat that model's baseline.

    uv run python scripts/run_matrix.py --model anthropic/claude-haiku-5-5 --found attack_found_haiku55

Logs go to <log-dir>/<model-short-name>/. One process per model keeps model-level parallelism simple.
"""

from __future__ import annotations

import argparse

from inspect_ai import eval as inspect_eval

from safeguard_frontier.tasks import SCENARIO_DIR, property


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="e.g. anthropic/claude-haiku-5-5")
    parser.add_argument("--conditions", default="c0,c1,c2,c3,c4,c5,c13")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--found", default="", help="attack file stem of variants that beat this model's baseline")
    parser.add_argument("--log-dir", default="logs/matrix")
    parser.add_argument("--max-connections", type=int, default=8)
    parser.add_argument("--standard", action="store_true", default=True)
    parser.add_argument("--no-standard", dest="standard", action="store_false")
    args = parser.parse_args()

    short = args.model.split("/")[-1]
    tasks = []
    for cond in [c.strip() for c in args.conditions.split(",") if c.strip()]:
        if args.standard:
            tasks.append(property(condition=cond))
        if args.found and (SCENARIO_DIR / f"{args.found}.json").exists():
            tasks.append(property(condition=cond, kinds="attack", attacks=args.found))
    inspect_eval(
        tasks,
        model=args.model,
        epochs=args.epochs,
        log_dir=f"{args.log_dir}/{short}",
        max_connections=args.max_connections,
        max_tasks=2,
        display="plain",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
