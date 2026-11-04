# Changelog

## 2026-11-04 (evening)

- Baseline results on the 38 hand-written scenarios, one epoch: Haiku 5.5 attack success 0.05,
  benign completion 0.95; Sonnet 5.5 0.00 and 0.95; Haiku 4.5 0.10 and 0.84. Both current models
  ignored every explicit injected instruction; the only hand-written success was plain false portal
  text asserted as fact (a11). Conclusion: the hand-written set sits at a ceiling for current models.
- Adaptive attacker added (scripts/generate_attacks.py): Sonnet 5.5 wrote five variants per base
  attack, 90 in total; it refused two base goals (cross-tenant exfiltration, deposit scam) under its
  cyber policy, so those remain hand-written only. Against the baseline, per-variant success was
  0.07 on Haiku 5.5, 0.06 on Sonnet 5.5 and 0.26 on Haiku 4.5; best-of-5 success was 2/18, 3/18 and
  8/18 base goals. Sonnet 5.5 fell for a fake-policy message that Haiku 5.5 did not.
- Strict condition c5 added to populate the over-cautious end: on Haiku 5.5 attack success 0 and
  benign completion 0.76, with every description-dependent task handed over.
- scripts/select_found.py writes the variants that beat a model's baseline to a fixed file per model
  (attack_found_haiku55, attack_found_sonnet55, attack_found_haiku45); defences are measured on these.
- scripts/run_matrix.py runs every condition on the standard set and the found set for one model.

## 2026-11-04 (later)

- Profile A harness runs end to end on Haiku 5.5 for conditions c0 to c4. Agent-written, author-run.
- Tools reduced from the eight in the design to seven: the tenant rules are inline in the system prompt,
  as they would be in the product, so tenant_rules was dropped. Added update_listing so that H2 has a
  database-changing action, not only a booking.
- Fabrication grader fix: the first run flagged "Mr Tan"-style greetings as invented facts because the
  grader was not shown the client identity. The grader now sees the client's name and phone and is
  told to ignore greetings and statements about next steps. Fabrication on the baseline went from 7/24
  to 0/24, which matches a manual read of the transcripts.
- Added condition c4 (tool-level tenant scoping) and the combinations c13 and c123. Scoping is the
  structural fix for H1; measuring it shows what a zero-cost defence looks like on the frontier.
- Attack tiers introduced (instruction, false_content, poisoned_source, pressure) and eight attacks
  added, plus six description-dependent benign scenarios, because the baseline model resisted every
  explicit instruction. See docs/design.md, "Attack tiers".

## 2026-11-04

- Project scaffold: pyproject with Inspect, the Anthropic SDK and python-dotenv; env wiring; smoke test
  that checks the key and lists the planned models.
- docs/design.md v0 written before any run, so hazards, scenarios, conditions and acceptance criteria
  are fixed in advance. Agent-proposed, author-approved: the three deployment profiles and their order.
