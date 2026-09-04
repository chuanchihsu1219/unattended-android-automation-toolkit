# AI-assisted development

## Authorship statement

The implementation and documentation were developed with substantial assistance from an OpenAI Codex coding agent. Chuan-Chih Hsu served as project owner: defining the problem, adding operating constraints, choosing behavior at ambiguous boundaries, authorizing external actions, and reviewing acceptance outcomes.

This is not presented as unaided manual coding.

## Human contribution

- Identified the need for unattended historical and intraday data collection.
- Specified the real deployment environment: Windows laptop, lid-close sleep, reboot, Excel usage, and no midnight collection.
- Chose separate settled and hourly data semantics.
- Required auditable formulas, append-only records, failure evidence, and no canonical writes after validation failure.
- Required official app distribution, explicit authentication checkpoints, and secret isolation.
- Evaluated the usefulness of the output for future analysis and portfolio presentation.

## Agent contribution

- Implemented the Python modules, PowerShell scripts, SQLite schema, tests, and documentation.
- Ran local diagnostics, failure analysis, and iterative fixes under user authorization.
- Created synthetic portfolio artifacts and performed secret and personal-information scans.

## Verification model

AI-generated code is treated as an untrusted draft until checked by executable evidence:

1. Unit tests for validation, redaction, idempotency, superseding, and cleanup.
2. PowerShell parser checks.
3. Synthetic end-to-end pipeline runs.
4. Secret and personal-path scans across the full Git history.
5. Production-specific end-to-end verification in the separate private adapter repository.

## What engineering ownership means here

Typing code is one part of engineering. Ownership also requires defining semantics, resolving tradeoffs, setting safety boundaries, designing acceptance tests, and being able to explain failures. The decision record makes those contributions inspectable instead of claiming credit based only on commit volume.
