# Changelog

## 1.0.0 — 2026-09-18

First portable Windows release of 瑪奇M - 兼職小助手.

- Combine material retrieval, sequential quest submission, and independent shared-storage stock checking in one compact window.
- Prepare 19 material types for three completions each; allow per-quest remaining counts and finish uniquely identified ready active quests first.
- Preserve completed history when missing scrolls are skipped; require result closure and report disappearance before completion credit.
- Include scoped OCR, reviewed shared aliases, configurable pause/resume hotkeys, local reports, recovery controls, and the application icon.
- Package version 1.0.0 consistently in the title, Windows executable metadata, ZIP, and checksum.
- Full live 19-material / 57-quest batch, stock-scan coverage across layouts, and multi-monitor DPI behavior remain unverified. See README.md and VALIDATION.md.

The entries below record development history and may describe superseded behavior.

## 0.2.0-dev — Tab controls and resumable pause (unreleased)

- Show version in the title; move retrieval controls and notices into their tabs.
- Add persistent F1–F12 pause/resume binding, retaining the old key on registration failure.
- Resume the same worker after bringing the game to the foreground; fatal stops still require recovery.
- After entering withdrawal quantity, use the fixed green confirmation area without numeric OCR.
- Rename the batch reset and remove the manual-retrieval confirmation button.

## 0.1.4 — Batch OCR and reviewed name suggestions

- Reuse one local OCR process per scan; batch atlas and unresolved-cell images.
- Measure startup, preprocessing, OCR, transport, matching and retry times.
- Add grouped fuzzy-name review with original pixels, explicit accept/reject and stale-preview invalidation.
- Preserve count uncertainty, plus distinctions and canonical material mappings.
- Add offline diagnostics/benchmarking and timestamped non-overwriting builds.

## 0.1.3 — Bounded OCR retries

- Retry unconfirmed labels using green-channel and isolated 5x OCR.
- Accept only one exact whitelist identity; retain unknown on conflicts or OCR failure.

## 0.1.2 — Quest-scroll recognition

- Separate quest-scroll and material preview modes; require matching selected subcategory.
- Join each quest cell's wrapped label and read its own enlarged count crop.
- Never interpret a material-name fragment on the quest page as carried materials.
- Show unknown labels/counts explicitly; keep exact names and literal plus signs.

## 0.1.1 — Window detection fix

- Match the verified game process instead of title substrings, so the assistant does not count itself as a second game window.
- Preserve refusal when multiple actual game windows exist or process identity cannot be read.

## 0.1.0 — Capture and recognition prototype

- Add Traditional Chinese desktop capture and recognition preview.
- Detect game process/client rectangle, require 1280 × 960 live capture and manual UI-scale confirmation.
- Load and validate XLSX without modification; distribute game-only whitelist defaults.
- Add global F8, visible Pause, focus checks and an explicitly triggered single-I test.
- Add local reports, diagnostic mode, safety/recognition tests and portable build script.
- Keep planning, withdrawals, quest activation and background input disabled.

## 0.1.5

- Player-entered per-cell scroll quantities default to 3; quest count OCR is skipped.
- Unique fuzzy names scoring at least 75% can be adopted, with type, literal-plus and ambiguity checks.

## 0.2.0

- Fixed 19-by-three preparation and sequential submission workflow; player opens shared storage and moves to board.
- Guarded foreground mouse/keyboard primitives, bounded visual states, durable interrupted-action journal and explicit reconciliation.
- Count OCR removed from main workflow; only typed withdrawal input is verified. Full live cycle remains unverified.

## 0.2.1

- Clear default quantity with Ctrl+A and Backspace before typing the requested amount, with cancellable event spacing.
- Batch start discovers and validates the foreground game automatically; manual capture and UI confirmation are no longer prerequisites.

## 0.2.2

- Replace the legacy capture/preview GUI and separate batch window with one core-workflow dashboard.
- Add live current-item/quantity/step reporting, automatic material and quest progress, timestamped debug log, and persistent stop reasons.
- Move quest-start acknowledgement, interrupted-action reconciliation and new-batch confirmation inline.
- Preserve saved batch progress and all guarded automation behavior.

## Unreleased — source-only reset fix

- Explain restored saved progress at startup.
- Place new-batch and recovery confirmation above the expanding progress area; visibly acknowledge reset clicks and allow inline cancellation.
- Preserve saved progress until explicit confirmation and archive it on reset. No package produced.

## Unreleased — fresh batches and effective storage scrolling

- Every launch creates a fresh batch, archives previous state, and uses single-click reset.
- Rename window and remove the large batch-count heading.
- Replace OCR-repeat/empty-page stopping with paced wheel retries and storage-panel motion comparison; detect name-row offsets after scrolling.
- Source-only, no package produced.

## Source update: storage search (2026-09-17)

- Removed stock-difference wording from withdrawal debug confirmations.
- Treat truncated 花 as an 箭花 tooltip candidate; exact tooltip verification remains mandatory.
- Increased each storage wheel burst from 3 to 15 paced notches; stop after two stationary observations.
- Source only; no package generated.
