# KICKOFF PROMPT — paste this as your first message in Claude Code

Before starting, make sure the repo contains: `CLAUDE.md`, `docs/SPEC.md`
(your existing v3 spec document, saved as-is), `docs/SPEC_AMENDMENTS.md`,
`docs/BUILD_PLAN.md`, `docs/EXPERT_PLAYBOOK.md`, the 6 CSVs in `data/`, and
the `scripts/` folder (generator + pinned expected values).
Run `git init` first if you haven't. Then start Claude Code in the repo root
and paste:

---

Read docs/SPEC_AMENDMENTS.md, docs/BUILD_PLAN.md, docs/VALIDATION_MATRIX.md,
and docs/EXPERT_NOTES.md in full. Skim
docs/SPEC.md's table of contents only — read individual sections on demand as
each phase requires them. SPEC_AMENDMENTS.md overrides SPEC.md wherever they
conflict.

Then implement Phase 0 and Phase 1 of the build plan. Use plan mode: show me
the file list and any open decisions before writing code. When Phase 1's exit
criteria pass (server boots, /api/v1/health returns the envelope, store
round-trip works), commit and stop — I'll review before Phase 2.

Throughout the whole build:
- Verify against data/underwriting_scorecard_clean.csv by actually running
  code, not by reasoning about it.
- Keep scripts/smoke_test.py growing with each phase and run it before
  declaring a phase done.
- If SPEC.md is ambiguous and SPEC_AMENDMENTS.md doesn't resolve it, ask me
  rather than guessing.

---

## Follow-up prompts (one per phase)

"Phase N: read the spec sections listed for it in docs/BUILD_PLAN.md, plan,
implement, extend smoke_test.py, run `python scripts/smoke_test.py --phase N`
against a running server, fix failures, commit."

## Practical tips
- `/clear` between phases so stale context from earlier phases doesn't crowd
  out the current spec sections.
- If Claude Code fails the same fix twice, `/clear` and restate the problem
  with what you learned — don't stack corrections.
- After Phase 4, open http://localhost:8000/docs and click through the demo
  flow yourself once; Swagger UI doubles as your demo dashboard.
- Phase 8's grep check is your dataset-agnostic guarantee — don't skip it.
