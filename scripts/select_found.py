"""Select the adaptive variants that beat the baseline and write them as a fixed attack set.

    uv run python scripts/select_found.py logs/adaptive_c0/haiku-5-5 --profile property --source attack_adaptive_sonnet --out attack_found_haiku55

Reads every log under the directory, collects sample ids whose attack_success score is 1 in any epoch,
and writes those scenarios (from the source file) to the profile's scenarios/<out>.json. Also prints
best-of-N success per base scenario, which is the headline for the adaptive attacker.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict

from inspect_ai.log import list_eval_logs, read_eval_log

from safeguard_frontier.profiles.registry import get_profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir")
    parser.add_argument("--profile", default="property")
    parser.add_argument("--source", default="attack_adaptive_sonnet")
    parser.add_argument("--out", default="attack_found")
    args = parser.parse_args()

    scenario_dir = get_profile(args.profile).scenario_dir
    source = json.loads((scenario_dir / f"{args.source}.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in source}

    hits: set[str] = set()
    per_base: dict[str, list[float]] = defaultdict(list)
    for info in list_eval_logs(args.log_dir):
        log = read_eval_log(info)
        if log.status != "success":
            continue
        for sample in log.samples or []:
            sc = (sample.scores or {}).get("attack_success")
            if sc is None:
                continue
            v = float(sc.value)
            if math.isnan(v):
                continue
            base = (sample.metadata or {}).get("scenario", {}).get("attack", {}).get("base_id", str(sample.id))
            per_base[base].append(v)
            if v >= 1.0 and str(sample.id) in by_id:
                hits.add(str(sample.id))

    print(f"{'base scenario':<32} {'variants':>8} {'per-variant':>12} {'best-of-N':>10}")
    for base, vals in sorted(per_base.items()):
        print(f"{base:<32} {len(vals):>8} {sum(vals) / len(vals):>12.2f} {1.0 if any(v >= 1.0 for v in vals) else 0.0:>10.0f}")
    bases_hit = sum(1 for vals in per_base.values() if any(v >= 1.0 for v in vals))
    print(f"\nbest-of-N success: {bases_hit}/{len(per_base)} base scenarios; {len(hits)} successful variants")

    found = [by_id[i] for i in sorted(hits)]
    out = scenario_dir / f"{args.out}.json"
    out.write_text(json.dumps(found, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(found)} scenarios to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
