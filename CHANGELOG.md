# Changelog

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
