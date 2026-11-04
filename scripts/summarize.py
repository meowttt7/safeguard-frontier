"""Summarise Inspect logs into one table per (condition, model), and optionally dump per-sample scores.

    uv run python scripts/summarize.py logs/property
    uv run python scripts/summarize.py logs/property --samples
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

METRICS = ["attack_success", "benign_completion", "fabrication", "over_caution"]


def fmt(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "  -  "
    return f"{value:5.2f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir", nargs="?", default="logs")
    parser.add_argument("--samples", action="store_true", help="print per-sample scores and explanations")
    args = parser.parse_args()

    infos = list_eval_logs(args.log_dir)
    if not infos:
        print(f"no logs under {args.log_dir}")
        return 1

    print(f"{'task':<16} {'model':<30} {'n':>4}  " + "  ".join(f"{m:>18}" for m in METRICS))
    for info in sorted(infos, key=lambda i: i.name):
        log = read_eval_log(info, header_only=not args.samples)
        if log.status != "success" or not log.results:
            print(f"{log.eval.task:<16} {log.eval.model:<30} status={log.status}")
            continue
        scores = {s.name: s.metrics for s in log.results.scores}
        cells = []
        for m in METRICS:
            metrics = scores.get(m, {})
            r = metrics.get("rate").value if "rate" in metrics else None
            n = metrics.get("applicable").value if "applicable" in metrics else None
            cells.append(f"{fmt(r)} (n={int(n) if n is not None else 0:>2})")
        print(f"{log.eval.task:<16} {log.eval.model:<30} {log.results.completed_samples:>4}  " + "  ".join(f"{c:>18}" for c in cells))

        if args.samples and log.samples:
            for sample in log.samples:
                parts = []
                for m in METRICS:
                    sc = sample.scores.get(m) if sample.scores else None
                    if sc is None:
                        continue
                    v = sc.value
                    v_str = "-" if isinstance(v, float) and math.isnan(v) else str(v)
                    parts.append(f"{m}={v_str}")
                print(f"    {sample.id:<30} epoch={sample.epoch} " + " ".join(parts))
                for m in METRICS:
                    sc = sample.scores.get(m) if sample.scores else None
                    if sc is not None and sc.explanation:
                        print(f"        {m}: {sc.explanation[:220]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
