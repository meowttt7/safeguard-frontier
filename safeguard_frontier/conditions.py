"""Experimental conditions: which defences are switched on."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Condition:
    name: str
    description: str
    hardened_prompt: bool = False
    quarantine: bool = False
    monitor: bool = False
    structural_scoping: bool = False


CONDITIONS: dict[str, Condition] = {
    "c0": Condition("c0", "Baseline: product-style system prompt, no defence."),
    "c1": Condition("c1", "Hardened prompt: explicit rules on untrusted content, tenancy and confirmation.", hardened_prompt=True),
    "c2": Condition("c2", "Quarantined tool results: results labelled as data, free text marked untrusted.", quarantine=True),
    "c3": Condition("c3", "Trusted monitor: a cheaper model reviews every tool call before it executes.", monitor=True),
    "c4": Condition("c4", "Structural scoping: the tool layer refuses any call outside the serving tenant.", structural_scoping=True),
    "c13": Condition("c13", "Hardened prompt plus trusted monitor.", hardened_prompt=True, monitor=True),
    "c123": Condition("c123", "Hardened prompt, quarantine and monitor together.", hardened_prompt=True, quarantine=True, monitor=True),
}
