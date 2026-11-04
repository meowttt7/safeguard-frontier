# safeguard-frontier

Measuring what agent safeguards cost. For an assistant that reads untrusted content on behalf of a
user, which defences reduce attack success without making the assistant useless, and by how much?

Status: scaffold, 2026-11-04. Nothing has been measured yet. This file is rewritten as results come in;
the build history is in CHANGELOG.md and the pre-registered design is in docs/design.md.

## Why

Small operators put language models in front of the public with no way to measure what slips through.
I ran one such product, a WhatsApp assistant for property agents built on Claude, and tuned it by hand
through eleven rounds against two failures that pull in opposite directions: the model stating facts
that were not in its sources, and, once restrained, deferring to a human so often that it stopped being
useful. This evaluation is the instrument I did not have then.

Anthropic's [Recommendations for Technical AI Safety Research Directions](https://alignment.anthropic.com/2025/recommended-directions/)
ask for "defenses ... that interfere minimally with benign use" and for "better measures of the
practical reliability of defenses". This project sits there.

## Design in one screen

- Deployment profiles modelled on products I have run, each with four to six tools over synthetic data:
  a property assistant serving two tenants, a trading companion holding a scoped key with limits, and,
  if time allows, a block-explorer assistant reading attacker-controlled on-chain metadata.
- Attacks arrive through content the agent reads, client messages and tool results, never through
  jailbreak prompts aimed at the model directly.
- Conditions: no defence; hardened system prompt; quarantined tool results; trusted monitor, where a
  cheaper model screens consequential tool calls before they execute.
- Measurements per run: attack success (tenant boundary crossed or forbidden action taken), fabrication
  (facts asserted that are not in the sources), and over-caution (a benign task refused or deferred when
  the agent had what it needed).
- Models: Claude Haiku 5.5 and Claude Sonnet 5.5 through the API, plus one open-weights model run
  locally if it fits the schedule.
- Headline result: attack success against benign completion, per defence and per model.

Built on [Inspect](https://inspect.aisi.org.uk/), the UK AI Security Institute's evaluation framework.

## Running

```
uv sync
cp .env.example .env          # paste your Anthropic API key into .env
uv run python scripts/smoke_test.py
```

Evaluation tasks live under `safeguard_frontier/` and run with `inspect eval`. Instructions follow once
the first task exists.

## Provenance

Author: Tin Tran. The code is written with coding agents (Claude Code) under the author's direction.
The research question, the hazards and acceptance criteria in docs/design.md, the analysis and the
report are the author's. Where an agent made a design choice, the changelog says so.
