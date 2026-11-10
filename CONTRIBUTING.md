# Contributing

- **A connector note changed:** update the doc and name the page and date you checked.
- **A new error pattern:** add a rule to `scripts/error_triage.py` and a case to `tests/test_scripts.py`.
- **A new object pair:** add it to `samples/plan.example.json` and `docs/what-to-sync.md`, and any new rule to `scripts/plan_check.py` with a test.
- **Standard field names:** they are the usual ones. If your connection exposes different names, say so in `docs/field-mapping.md`.
- Describe behavior, not outcomes. Do not state how a sync resolves a conflict unless the product documentation does.
- Use "two-way sync". Describe restrictions as read-only access or per-field direction.
- Use synthetic data only. Never include real customers, ids, credentials or internal URLs.
