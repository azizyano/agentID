# First-part engineering team

The owner requested a collaborating team on 20 November 2026. The lead launches bounded specialist tasks, routes findings to the file owner, reviews changes, and runs the integrated checks. All work stays in this local repository.

| Role | Responsibility | File ownership for this build |
| --- | --- | --- |
| Workflow engineer | Usable commands, explicit outcomes, reliable artifacts | tools/run_comparison.py; tests/integration/test_comparison_cli.py |
| State engineer | Atomic reservations, request binding, restart and conflict handling | comparison_state.py; tests/integration/test_comparison_state.py |
| Adversarial QA | Independent failing examples and acceptance checks | tests/adversarial/test_first_part_guards.py; implementation read-only |
| Lead / integration | Shared evidence/policy/parser fixes, review, final tests and docs | runner.py; workers.py; shared interfaces and documentation |

## Coordination

Use direct agent messages for suspected defects, shared-interface changes, and review handoffs. Include the affected path, minimal input, actual versus expected behavior, and a runnable test. Ask the owner before editing another role's files. Only the lead integrates reviewed changes. Use at most three active coding specialists; keep parallel file ownership exclusive.

For this build, specialists reproduced failures and handed findings to the relevant owner. The lead reviewed the implementations and ran the full suite. Work used exclusive files in the shared workspace because the repository has no initial commit; no Git branches, worktrees, commits, or merges were created.

## Delivered first part

The local experiment engine now rejects malformed evidence, enforces typed authorization, binds stored replies to exact requests, handles concurrent state conflicts, and distinguishes completed/pending/error CLI outcomes. Current verification: 140 project tests and all 40 frozen scenarios pass. Test artifacts are in `artifacts/part1/`.

This team step does not establish AI behavior, a real funded job, or product value over baseline C. Runtime selection remains deferred. Paid calls, production activity, UI/API, and deployment remain behind the documented gates.
