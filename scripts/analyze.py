"""Aggregate matrix logs into results/: long-form CSV, summary tables, and figures.

    uv run python scripts/analyze.py logs/matrix --out results

Confidence intervals are 95% percentile intervals from a cluster bootstrap over scenarios (a scenario's
epochs stay together), 2,000 resamples, seeded. Rates are means over all scenario-epoch observations.

Figures:
- dots.png: for each model, attack success and benign completion per condition as dot plots with
  intervals. The main figure; it stays legible when the defences cluster.
- frontier.png: attack success against benign completion per model, labels only on the points the
  text discusses (baseline, hardened prompt, strict prompt).
- found_attacks.png: attack success per condition on the variants that beat each model's baseline.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from inspect_ai.log import list_eval_logs, read_eval_log  # noqa: E402

METRICS = ["attack_success", "benign_completion", "fabrication", "over_caution"]
COND_LABELS = {
    "c0": "c0 baseline",
    "c1": "c1 hardened prompt",
    "c2": "c2 quarantine",
    "c3": "c3 monitor",
    "c4": "c4 tool scoping",
    "c5": "c5 strict prompt",
    "c13": "c13 hardened + monitor",
    "c123": "c123 hardened + quarantine + monitor",
}
COND_ORDER = list(COND_LABELS)
MODEL_LABELS = {
    "claude-haiku-4-5": "Haiku 4.5",
    "claude-haiku-5-5": "Haiku 5.5",
    "claude-sonnet-5-5": "Sonnet 5.5",
    "claude-opus-5-5": "Opus 5.5",
}
MODEL_ORDER = list(MODEL_LABELS)

# Reference palette (light mode) from the data-viz method; one hue only, identity via direct labels.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
BLUE_LIGHT = "#86b6ef"


# ----- loading and statistics ------------------------------------------------------------------


def load_rows(log_dir: str) -> list[dict]:
    rows: list[dict] = []
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info)
        if log.status != "success":
            continue
        task_args = log.eval.task_args or {}
        condition = task_args.get("condition", "c0")
        attacks = task_args.get("attacks", "attack")
        set_name = "standard" if attacks == "attack" else "found"
        model = log.eval.model.split("/")[-1]
        for sample in log.samples or []:
            md = sample.metadata or {}
            scenario = md.get("scenario") or {}
            base = {
                "model": model,
                "condition": condition,
                "set": set_name,
                "attacks": attacks,
                "sample_id": str(sample.id),
                "epoch": sample.epoch,
                "kind": md.get("kind") or scenario.get("kind", ""),
                "tier": md.get("tier") or "",
                "needs": scenario.get("needs", ""),
                "base_id": (scenario.get("attack") or {}).get("base_id", ""),
            }
            for metric in METRICS:
                score = (sample.scores or {}).get(metric)
                if score is None:
                    continue
                try:
                    value = float(score.value)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    continue
                if math.isnan(value):
                    continue
                rows.append({**base, "metric": metric, "value": value})
    return rows


def cluster_bootstrap(values_by_cluster: dict[str, list[float]], reps: int = 2000, seed: int = 7) -> tuple[float, float, float]:
    clusters = list(values_by_cluster.values())
    if not clusters:
        return float("nan"), float("nan"), float("nan")
    flat = [v for c in clusters for v in c]
    mean = sum(flat) / len(flat)
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        picked = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        obs = [v for c in picked for v in c]
        means.append(sum(obs) / len(obs))
    means.sort()
    lo = means[int(0.025 * (reps - 1))]
    hi = means[int(0.975 * (reps - 1))]
    return mean, lo, hi


def aggregate(rows: list[dict], keys: tuple[str, ...]) -> dict[tuple, dict]:
    grouped: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = tuple(r[k] for k in keys)
        grouped[key][r["sample_id"]].append(r["value"])
    out = {}
    for key, clusters in grouped.items():
        mean, lo, hi = cluster_bootstrap(clusters)
        out[key] = {"mean": mean, "lo": lo, "hi": hi, "n_scenarios": len(clusters), "n_obs": sum(len(v) for v in clusters)}
    return out


def fmt(stat: dict | None) -> str:
    if not stat or math.isnan(stat["mean"]):
        return "-"
    return f"{stat['mean']:.2f} [{stat['lo']:.2f}, {stat['hi']:.2f}] (n={stat['n_scenarios']})"


# ----- tables ------------------------------------------------------------------------------------


def write_summary(rows: list[dict], out: Path) -> None:
    standard = [r for r in rows if r["set"] == "standard"]
    found = [r for r in rows if r["set"] == "found"]
    by_cond = aggregate(standard, ("model", "condition", "metric"))
    by_found = aggregate(found, ("model", "condition", "metric"))
    by_tier = aggregate([r for r in standard if r["metric"] == "attack_success"], ("model", "condition", "tier"))
    by_needs = aggregate([r for r in standard if r["metric"] == "benign_completion" and r["kind"] == "benign"], ("model", "condition", "needs"))

    models = [m for m in MODEL_ORDER if any(r["model"] == m for r in rows)]
    conds = [c for c in COND_ORDER if any(r["condition"] == c for r in rows)]
    lines = ["# Results summary", "", "Rates with 95% cluster-bootstrap intervals over scenarios; n = scenarios (3 epochs each unless noted).", ""]
    for model in models:
        lines.append(f"## {MODEL_LABELS.get(model, model)}")
        lines.append("")
        lines.append("| condition | attack success (standard) | benign completion | fabrication | over-caution | attack success (baseline-beating variants) |")
        lines.append("|---|---|---|---|---|---|")
        for cond in conds:
            cells = [fmt(by_cond.get((model, cond, m))) for m in METRICS]
            cells.append(fmt(by_found.get((model, cond, "attack_success"))))
            lines.append(f"| {COND_LABELS.get(cond, cond)} | " + " | ".join(cells) + " |")
        lines.append("")
        tiers = sorted({r["tier"] for r in standard if r["model"] == model and r["tier"]})
        if tiers:
            lines.append("Attack success by tier (standard set):")
            lines.append("")
            lines.append("| condition | " + " | ".join(tiers) + " |")
            lines.append("|---|" + "---|" * len(tiers))
            for cond in conds:
                lines.append(f"| {COND_LABELS.get(cond, cond)} | " + " | ".join(fmt(by_tier.get((model, cond, t))) for t in tiers) + " |")
            lines.append("")
        needs = sorted({r["needs"] for r in standard if r["model"] == model and r["needs"]})
        if needs:
            lines.append("Benign completion by what the task needs (benign scenarios only):")
            lines.append("")
            lines.append("| condition | " + " | ".join(needs) + " |")
            lines.append("|---|" + "---|" * len(needs))
            for cond in conds:
                lines.append(f"| {COND_LABELS.get(cond, cond)} | " + " | ".join(fmt(by_needs.get((model, cond, n))) for n in needs) + " |")
            lines.append("")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ----- figures -----------------------------------------------------------------------------------


def style_axes(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(1)
    ax.grid(True, color=GRID, linewidth=1, linestyle="-")
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_color(INK_2)


def titles(fig, title: str, subtitle: str) -> float:
    """Title and a subtitle wrapped to the figure width. Returns the top of the plotting area as a
    figure fraction, so that tight_layout can reserve the space the text block actually needs."""
    width_in, height_in = fig.get_figwidth(), fig.get_figheight()
    title_txt = textwrap.fill(title, max(30, int(width_in * 9)))
    sub_txt = textwrap.fill(subtitle, max(40, int(width_in * 14)))
    title_lines = title_txt.count("\n") + 1
    sub_lines = sub_txt.count("\n") + 1
    y_title = 1 - 0.12 / height_in
    y_sub = y_title - (title_lines * 0.26 + 0.04) / height_in
    top = y_sub - (sub_lines * 0.17 + 0.22) / height_in
    fig.text(0.02, y_title, title_txt, fontsize=13, color=INK, fontweight="bold", va="top")
    fig.text(0.02, y_sub, sub_txt, fontsize=9, color=INK_2, va="top", linespacing=1.3)
    return top


def plot_dots(rows: list[dict], out: Path) -> None:
    """Main figure: one row per model, two panels (attack success, benign completion), conditions as rows."""
    standard = [r for r in rows if r["set"] == "standard"]
    stats = aggregate(standard, ("model", "condition", "metric"))
    models = [m for m in MODEL_ORDER if any(r["model"] == m for r in standard)]
    if not models:
        return
    conds = [c for c in COND_ORDER if any((m, c, "attack_success") in stats for m in models)]
    panel_h = 0.36 * len(conds) + 0.9
    fig, axes = plt.subplots(len(models), 2, figsize=(10.5, panel_h * len(models) + 1.0), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    for row, model in enumerate(models):
        for col, (metric, xlabel) in enumerate(
            (("attack_success", "Attacks that succeeded (share)"), ("benign_completion", "Benign tasks completed (share)"))
        ):
            ax = axes[row][col]
            style_axes(ax)
            ys = list(range(len(conds)))[::-1]
            for y, cond in zip(ys, conds):
                s = stats.get((model, cond, metric))
                if not s:
                    continue
                ax.plot([s["lo"], s["hi"]], [y, y], color=BLUE_LIGHT, linewidth=2, solid_capstyle="round", zorder=2)
                ax.plot(s["mean"], y, marker="o", markersize=8, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
                ax.text(s["hi"] + 0.015, y, f"{s['mean']:.2f}", va="center", ha="left", fontsize=8.5, color=INK_2)
            ax.set_yticks(ys)
            ax.set_yticklabels([COND_LABELS.get(c, c) for c in conds] if col == 0 else [""] * len(conds), fontsize=9)
            ax.set_xlim(-0.02, 1.12)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_ylim(-0.6, len(conds) - 0.4)
            if row == len(models) - 1:
                ax.set_xlabel(xlabel, fontsize=9, color=INK_2)
            if col == 0:
                ax.set_title(MODEL_LABELS.get(model, model), loc="left", fontsize=11, color=INK, pad=6)
            else:
                ax.set_title(" ", loc="left", fontsize=11, pad=6)
    top = titles(
        fig,
        "What each defence buys and what it costs, by model",
        "Standard scenario set: 20 attacks and 18 benign tasks, 3 epochs. Dots are rates, lines are 95% bootstrap intervals over scenarios. Lower is better on the left, higher on the right.",
    )
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(out / "dots.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def plot_frontier(rows: list[dict], out: Path) -> None:
    """Secondary figure: attack success against benign completion; labels on the discussed points only."""
    standard = [r for r in rows if r["set"] == "standard"]
    stats = aggregate(standard, ("model", "condition", "metric"))
    models = [m for m in MODEL_ORDER if any(r["model"] == m for r in standard)]
    if not models:
        return
    labelled = {"c0", "c1", "c5"}
    cols = 2 if len(models) > 1 else 1
    rows_n = math.ceil(len(models) / cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(5.2 * cols, 4.2 * rows_n + 0.6), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    for idx, model in enumerate(models):
        ax = axes[idx // cols][idx % cols]
        style_axes(ax)
        for cond in COND_ORDER:
            a = stats.get((model, cond, "attack_success"))
            b = stats.get((model, cond, "benign_completion"))
            if not a or not b:
                continue
            ax.plot([b["lo"], b["hi"]], [a["mean"], a["mean"]], color=BLUE_LIGHT, linewidth=1.2, zorder=1)
            ax.plot([b["mean"], b["mean"]], [a["lo"], a["hi"]], color=BLUE_LIGHT, linewidth=1.2, zorder=1)
            ax.plot(b["mean"], a["mean"], marker="o", markersize=8, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
            if cond in labelled:
                offset = (-10, 10) if cond == "c0" else (-8, -18) if cond == "c1" else (0, 12)
                ha = "right" if cond in ("c0", "c1") else "center"
                ax.annotate(
                    COND_LABELS[cond], (b["mean"], a["mean"]), xytext=offset, textcoords="offset points",
                    fontsize=8.5, color=INK_2, ha=ha, va="bottom",
                )
        ax.set_title(MODEL_LABELS.get(model, model), loc="left", fontsize=11, color=INK, pad=6)
        ax.set_xlim(0.55, 1.03)
        ax.set_ylim(-0.08, 0.42)
        ax.set_yticks([0, 0.1, 0.2, 0.3, 0.4])
        ax.set_xlabel("Benign tasks completed (share)", fontsize=9, color=INK_2)
        ax.set_ylabel("Attacks that succeeded (share)", fontsize=9, color=INK_2)
    for idx in range(len(models), rows_n * cols):
        axes[idx // cols][idx % cols].set_visible(False)
    top = titles(
        fig,
        "The frontier: attack success against benign completion",
        "One dot per condition; unlabelled dots are the quarantine, monitor, scoping and hardened-plus-monitor conditions, which sit with the baseline. Down and right is better.",
    )
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(out / "frontier.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def plot_found(rows: list[dict], out: Path) -> None:
    found = [r for r in rows if r["set"] == "found" and r["metric"] == "attack_success"]
    if not found:
        return
    stats = aggregate(found, ("model", "condition"))
    models = [m for m in MODEL_ORDER if any(r["model"] == m for r in found)]
    n_conds = max(len([c for c in COND_ORDER if (m, c) in stats]) for m in models)
    cols = 2 if len(models) > 1 else 1
    rows_n = math.ceil(len(models) / cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(5.2 * cols, (0.36 * n_conds + 1.1) * rows_n + 0.8), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    for idx, model in enumerate(models):
        ax = axes[idx // cols][idx % cols]
        style_axes(ax)
        conds = [c for c in COND_ORDER if (model, c) in stats]
        ys = list(range(len(conds)))[::-1]
        for y, cond in zip(ys, conds):
            s = stats[(model, cond)]
            ax.barh(y, s["mean"], height=0.42, color=BLUE, zorder=2)
            ax.plot([s["lo"], s["hi"]], [y, y], color=INK_2, linewidth=1, zorder=3)
            ax.text(s["hi"] + 0.02, y, f"{s['mean']:.2f}", va="center", ha="left", fontsize=8.5, color=INK_2)
        ax.set_yticks(ys)
        ax.set_yticklabels([COND_LABELS.get(c, c) for c in conds], fontsize=8.5)
        ax.set_xlim(0, 1.18)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xlabel("Attacks that succeeded (share)", fontsize=9, color=INK_2)
        n = stats[(model, conds[0])]["n_scenarios"] if conds else 0
        ax.set_title(f"{MODEL_LABELS.get(model, model)}: {n} baseline-beating variants", loc="left", fontsize=10.5, color=INK, pad=6)
    for idx in range(len(models), rows_n * cols):
        axes[idx // cols][idx % cols].set_visible(False)
    top = titles(
        fig,
        "Do the defences stop the attacks that beat the baseline?",
        "Adaptive variants that succeeded against each model's own baseline, rerun under every condition for 3 epochs. Lines are 95% bootstrap intervals.",
    )
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(out / "found_attacks.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ----- main --------------------------------------------------------------------------------------


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir", nargs="?", default="logs/matrix")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = load_rows(args.log_dir)
    if not rows:
        print("no successful logs found")
        return 1
    with (out / "scores.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    write_summary(rows, out)
    plot_dots(rows, out)
    plot_frontier(rows, out)
    plot_found(rows, out)
    runs = {(r["model"], r["condition"], r["set"]) for r in rows}
    print(f"{len(rows)} score rows from {len(runs)} runs; wrote scores.csv, summary.md, dots.png, frontier.png, found_attacks.png to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
