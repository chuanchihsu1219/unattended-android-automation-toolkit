# Engineering decision record

- Product direction and acceptance criteria: Chuan-Chih Hsu
- Implementation support: OpenAI Codex

This record shows the human decisions that shaped the system. It is intentionally separate from the code-generation history: engineering ownership includes deciding what must be true, which risks matter, and how success is verified.

## D1 — Separate settled and intraday records

**Context:** A daily settled value and a same-day cumulative snapshot have different meanings and update behavior.

**Decision:** Store them as distinct observation types. Derive interval usage only from adjacent intraday snapshots.

**Acceptance check:** A same-day refresh cannot overwrite or masquerade as the prior day's settled record.

## D2 — Do not collect at midnight

**Context:** At exactly 00:00, UI labels such as “today” and “yesterday” may transition at different times across the app, backend, and local clock.

**Decision:** Schedule hourly collection from 01:00 through 23:00. Let the next settled observation represent the prior day.

**Acceptance check:** The task definition contains no midnight trigger, and delayed work during 00:00–00:59 exits without collecting.

## D3 — Treat laptop sleep and reboot as expected states

**Context:** The deployment target is a laptop that may sleep when the lid is closed.

**Decision:** Combine `WakeToRun`, `StartWhenAvailable`, a logon trigger, battery execution, and bounded restart-on-failure.

**Acceptance check:** Task XML is audited automatically; after resume or logon the next eligible run can recover without storing the Windows password.

## D4 — Validate before canonical persistence

**Context:** A visible number can belong to the wrong subject, date, mode, or loading state.

**Decision:** Require identity, state, numeric range, and cross-metric reconciliation before insertion.

**Acceptance check:** Fault injection produces a failed or rejected run with evidence while the current validated observation remains unchanged.

## D5 — Prefer deterministic UI evidence

**Context:** Desktop mouse coordinates and visual agents are difficult to reproduce in a hidden session.

**Decision:** Use resource IDs and accessibility first, then hierarchy-relative selectors and deterministic text/state. Use local fixed-region OCR only when hierarchy extraction is insufficient.

**Acceptance check:** The collector sends no Windows input events and operates only on an explicit Emulator serial.

## D6 — Preserve login state without trusting snapshots as the only recovery path

**Context:** Emulator userdata can persist while Quick Boot snapshots are disabled. Apps may still expire sessions.

**Decision:** Keep a fixed AVD userdata directory, cold boot with `-no-snapshot`, and make the private adapter capable of returning to its authenticated state safely.

**Acceptance check:** A cold boot completes the workflow using persisted state or the authorized login path.

## D7 — Decouple collection success from Excel availability

**Context:** Windows locks a workbook while Excel is editing it.

**Decision:** Commit validated data first. Publish a verified pending workbook through atomic replacement; defer publication if the destination is locked.

**Acceptance check:** A locked workbook never rolls back or duplicates the database record, and a later run can publish without re-scraping.

## D8 — Keep the vendor adapter private

**Context:** A useful portfolio should demonstrate engineering without publishing credentials, personal usage, proprietary assets, or target-specific instructions.

**Decision:** Open-source the generic lifecycle and synthetic example. Keep production package names, selectors, authentication flows, captured evidence, and real data in a separate private repository.

**Acceptance check:** A repository-wide scan finds no production identifiers, secrets, personal paths, or third-party screenshots.
