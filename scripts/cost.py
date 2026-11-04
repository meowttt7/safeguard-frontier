"""Estimate API spend from Inspect logs using the first-party list prices (USD per million tokens).

    uv run python scripts/cost.py logs

Prices are the public Anthropic rates as of November 2026; cache writes are billed at 1.25x input and
cache reads at the model's cache-read rate. The estimate ignores the first-run failures and the tiny
smoke test, so it slightly understates the true spend.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

PRICES = {  # input, output, cache_read per million tokens
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-haiku-4-5": (1.00, 5.00, 0.10),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
}


def main() -> int:
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs"
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    n_logs = 0
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info, header_only=True)
        if not log.stats:
            continue
        n_logs += 1
        for model, usage in log.stats.model_usage.items():
            short = model.split("/")[-1]
            totals[short]["input"] += usage.input_tokens or 0
            totals[short]["output"] += usage.output_tokens or 0
            totals[short]["cache_write"] += usage.input_tokens_cache_write or 0
            totals[short]["cache_read"] += usage.input_tokens_cache_read or 0
    grand = 0.0
    print(f"{n_logs} logs under {log_dir}")
    print(f"{'model':<20} {'input':>12} {'cache write':>12} {'cache read':>12} {'output':>12} {'USD':>8}")
    for model, t in sorted(totals.items()):
        p_in, p_out, p_read = PRICES.get(model, (0, 0, 0))
        cost = (t["input"] * p_in + t["cache_write"] * p_in * 1.25 + t["cache_read"] * p_read + t["output"] * p_out) / 1e6
        grand += cost
        print(f"{model:<20} {t['input']:>12,} {t['cache_write']:>12,} {t['cache_read']:>12,} {t['output']:>12,} {cost:>8.2f}")
    print(f"{'total':<20} {'':>12} {'':>12} {'':>12} {'':>12} {grand:>8.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
