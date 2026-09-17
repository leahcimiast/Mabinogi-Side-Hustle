# Milestone 1 validation

Validated locally on Windows 11 x64, Python 3.12.14, Pillow 12.3.0, openpyxl 3.1.5, Windows OCR zh-Hant-TW; packaged with PyInstaller 6.22.3.

## Verified

- Original workbook: 19 rows; exact spider-silk scroll to spider-web material mapping and literal plus preserved. No cell comments or external workbook links. Original personal author metadata excluded from Git by excluding the XLSX itself.
- Recorded canvas is 1920 × 1080; visual inspection confirms game content at (0,0,1280,960). Newly extracted 14 s and 36 s frames crop to baseline without altering source media.
- Windows OCR processed those frames (141 and 157 word boxes), recognizing the corn material and corn scroll labels. Popup images have unknown associated stack counts, correctly not treated as executable inventory data.
- Supplied 1664 × 1340 screenshot: 174 OCR word boxes; four full whitelist material labels. Sheep wool 70 and high-grade log+ 186 matched visible counts. Iron ore and spider web counts were missing and remained unknown. No partial match of mushroom juice to mushroom material.
- Live process and window identity detected. Foreground capture returned 1280 × 960 pixels, visually inspected as game content without desktop borders. No game keys were sent during this validation.
- Tk interface starts, shows four reference results, registers global F8, and closes cleanly.
- All 10 unit tests passed, including a synthetic WM_HOTKEY message and mocked focus-loss monitoring (no real keyboard input).
- Packaged EXE read-only diagnostic exited 0: Tk initialized, 19 defaults loaded, F8 registered, one game window detected, and the reference OCR reproduced 174 boxes/four labels. No Python command was used inside the packaged process.
- SHA-256 before/after checks confirmed the original workbook, supplied recording and screenshot are unchanged.
- Unit tests cover default mappings, invalid and duplicate whitelist rows, plus preservation, full-label matching, unknown/abbreviated/ambiguous counts, and refusal to send input while paused, cancelled, unfocused or wrong-sized.

## Unverified / limits

- Actual I-key acceptance by the game, inventory open/close result, game elevation compatibility, multi-monitor DPI variants, and live focus-loss interruption during input require a supervised player-triggered test. Safety gates are tested with mocks without sending game keys.
- Background input: **unverified**. No background-input implementation is enabled and no background messages were sent to the game. Foreground desktop capture success does not establish background input support. Test separately at a safe idle screen; do not infer support from Win32 call return values.
- UI scale is a manual setup confirmation after exact client-size validation. Occlusion by topmost windows is not automatically classified.
- OCR is incomplete on icon counts and low-contrast labels. No complete stack scan, scrolling deduplication, planning, withdrawals, or quest automation is claimed.
- Portable build still requires Windows OCR language components and PowerShell 5.1. A separate clean Windows installation has not been tested.

Private screenshots, logs, extracted frames and source hashes remain local and are excluded from Git.

## 0.1.1 window-detection regression

- Reproduced two candidates with the original assistant open: the actual game process and MabinogiAssistant.exe whose title contains the game name.
- Removed the title-substring fallback. With the original assistant still open, the fixed detector returns only the actual game window.
- Regression tests cover assistant/same-title document exclusion, unreadable process identity, case-insensitive game process names, and multiple genuine game windows remaining ambiguous.
- Current suite: 13 tests, 12 passed, 1 skipped because the running original assistant owns F8. No game input was sent.
- Bug-fix binary is delivered separately; the running original executable is preserved.

## 0.1.2 quest-scroll recognition

- Explicit quest/material mode and selected-tab evidence gate prevent the quest page from yielding carried-material counts. The default raw matching API now searches quest names only; material matching must be explicitly requested.
- The supplied clean recording at 34 seconds yields 14 complete whitelist scroll labels, 12 readable stack counts (3 each), and 5 unconfirmed labels. These are scroll stacks, not materials. The first icon is obscured by the cursor; its count remains unknown. Some labels lose OCR characters and remain unconfirmed, including non-whitelisted text; no character substitutions or material mappings are invented.
- Each of the fixed 5-column top-of-list cells has its two-line label enlarged separately from its digit crop. A nonnumeric Qty layout cue helps Windows OCR segment isolated digits; only OCR boxes wholly inside the source-digit region count as evidence.
- All 21 tests passed, including wrapped prefixes, material-fragment rejection, missing plus/prefix characters, count ambiguity, atlas region ownership and wrong selected page rejection.
- GUI smoke: 19 result rows, explicit scroll-count heading, scrollbar and mode-switch invalidation verified; screenshot inspected. No game input sent.
- Separate material reference was conservatively rejected because OCR missed its selected material-tab label. This is an acknowledged recognition limitation, not zero materials. The same reference in quest mode correctly returns no quest results.
- A new live inventory capture could not be taken because the game was not foreground; no focus change or game input was forced. Validation used original clean recording frames, not enlarged assistant-screen thumbnails.
- Current scope remains a single, unobscured, top-of-list 1280 × 960 quest inventory page. Scrolling, cross-page deduplication and complete inventory totals remain unimplemented.


## 0.1.3 bounded label retries

Original 34-second recording: 16 exact quest labels versus 14 previously; recovered wheat and spider-silk scrolls with count 3 each. Remaining unread/non-whitelisted labels remain unknown. No fuzzy replacement, material inference, game input, or source-image changes. User's latest assistant screenshot is a downscaled, annotated preview and does not establish that its iron-ore/mushroom errors are resolved on the original capture; a new player capture is still required. Added tests cover exact identity acceptance, conflict rejection, partial-text rejection, failure preservation, skipping confirmed cells, and the nine-call maximum retry budget.

## 0.1.4 batch OCR and reviewed name candidates

- Three runs on the same clean 34-second recording frame: median 6432 ms before, 1870 ms after (about 3.4x faster). OCR host processes per scan fell from nine to one. All three runs preserved the same 16 exact labels and 14 known counts. One additional fuzzy name candidate remains pending until explicitly reviewed.
- The 38-second nonmatching page remained rejected in both implementations. These two reference frames are limited evidence, not a general recognition accuracy claim.
- Timing reports separate startup, PNG encoding, image decoding, OCR, preprocessing and matching. Host startup and transport overhead are estimates; retry timing overlaps other stages. Similarity scores are not confidence probabilities.
- Offline suite: 46 tests, 45 passed and one real F8 registration test deliberately excluded. Withdrawn Tk tests cover candidate acceptance/rejection and invalidation. No game input or foreground changes were performed.
- Candidate review never guesses counts, changes material mappings, or silently accepts names. Ambiguous suggestions remain unresolved; scroll-type conflicts require individual confirmation; literal plus signs must agree.
- Complete scrolling, deduplication, storage totals and background input remain unverified or unimplemented. A fresh original capture is still needed to evaluate the player's latest recognition failures.


## 0.1.5 manual scroll quantity

Offline suite: 52 tests, 51 passed, one real hotkey integration test deliberately skipped. New tests cover editable quantities surviving name review, cancelled edits, unique fuzzy adoption, ambiguous/type/plus conflicts, and omission of the digit atlas from OCR. The clean 34-second reference produces default quantity 3 for all detected scroll cells; these are player defaults, not measured counts. No game input. Full inventory scrolling remains unimplemented.


## 0.2.0 fixed-batch automation

- Fixed plan generates 19 material requests and 57 ordered completions. No carried-stock subtraction or stock/scroll count OCR is used by this workflow.
- Offline suite covers journal intent persisted before input, reload blocking duplicate actions, explicit reconciliation, quantity mismatch preventing confirmation, lost confirmation retaining pending state, and preventing next quest activation after uncertain submission. Input tests mock SendInput and verify paused/focus-loss rejection.
- Original recording frames at 12, 17, 19, 39, 43, 45, 47 and 49 seconds were inspected. Checks recognize shared storage, item tooltip, quantity dialog, tracker identity, submission screen, enabled submission button, and return to world. Typed field 1 is readable; cursor-obscured 30 is rejected. Runtime moves the cursor away before readback.
- Stylized completion text was not recognized by Windows OCR. A compact gradient signature of the nonpersonal game completion banner is combined with OCR of the exact tracked quest name; the corn success reference passes, wrong identity and ordinary submission/world frames do not. No reference screenshots are distributed.
- Full 19-material retrieval, scrolling alignment, all 19 tracked quest names, cooking-item tooltip categories, toggle behavior, foreground mouse/key acceptance, insufficient stock/weight behavior and 57 live completions remain UNVERIFIED. No live input was sent during development. This release is a guarded foreground prototype requiring player-triggered testing.
- Transfer confirmation checks requested input and return to shared storage; it does not measure inventory deltas. Unknown transaction outcomes block replay and require explicit player reconciliation.

## 0.2.1 direct start and quantity replacement

69 offline tests: 68 passed, one actual F8 registration test deliberately skipped. Added a text-field simulation proving default 1 is cleared before typing 60, cancellation before digits, and automatic startup checks for missing/multiple games and invalid capture. All input is mocked; actual game text-field clearing and full live batch remain unverified.

## 0.2.2 unified dashboard

- 72 offline tests: 71 passed, one actual F8 registration test deliberately skipped. Removed obsolete preview-UI tests and added dashboard tests covering absence of legacy controls/extra windows, current item and failure display, automatic progress refresh, direct start, inline quest acknowledgement, explicit recovery, reset gates and pause.
- Tk layout instantiated offscreen: at 1120 x 800 the material tree is 500 x 489 and debug text is 517 x 379. Windows PrintWindow returned blank pixels for the offscreen Tk client, so visual screenshot QA is not claimed. Hidden-window callback/layout checks passed; no game input was sent.
- Logs now include scanned names/pages, requested versus observed input, action boundaries and timeouts. Unknown results still block replay. Full live withdrawal and quest acceptance remain unverified.

## Source-only reset fix

74 offline tests: 73 passed, one real hotkey registration test deliberately skipped. Regression tests verify reset confirmation precedes the progress area in layout order, restored 3/19 is explained, and confirmed reset archives the three-item record before starting at zero. Tests use temporary user-data directories; actual player progress is unchanged. No package or live game input.

## Source-only fresh batch and storage scrolling

80 offline tests: 79 passed, one actual hotkey registration test intentionally skipped. Tests cover startup resetting old three-item progress while archiving it, one-click reset including pending-state archival, no reset during a running worker, paced wheel retries, ignored changes outside storage, cancellation, and continued search across empty OCR pages with actual panel movement. The original recording keeps the same isolated-name results; a synthetic 37-pixel panel translation moves the detected iron-ore click position by 38 pixels (within 1 pixel). Live milk retrieval and real bottom-of-list behavior remain unverified. A motionless panel after three retries is reported as bottom or unaccepted wheel input, not proof that stock is absent. No package built or live input sent.

## Storage search update (2026-09-17)

Offline suite: 83 tests, 82 passed, 1 deliberate global-hotkey skip. Covers two stationary attempts, 30 total wheel notches across two attempts, cancellation, truncated arrowflower rejection on wrong tooltip, ambiguous candidates, and preference for exact names. No live game input performed. Actual 15-notch scroll distance and full inventory coverage remain unverified; larger jumps may skip intermediate rows depending on game wheel sensitivity. No package generated.


## 2026-09-17 Quantity observation and player name confirmation

- Supplied arrowflower screenshot is 1267 x 948. Offline Windows OCR read the exact tooltip title, recognized the transfer dialog, and returned 60 with normalized 1280 x 960 and padded variants. The historical failure was not reproduced; the old combined message cannot identify which check failed.
- Unknown quantity evidence now retries three observations without retyping or confirming. Explicit numeric mismatches still stop immediately. Logs separate title, dialog, and numeric evidence.
- Player-approved tooltip OCR corrections persist locally. Confirmation retains the worker and batch, waits three seconds for return to the foreground game, and discards pre-review pixels. Numeric checks remain mandatory. Rejection, F8, timeout, and changed game window stop continuation.
- Debug panel starts hidden at 660 x 720 and expands in the same window. Hidden logs continue collecting. Widget layout measurements: compact tree 599 x 314; expanded tree 503 x 314 and log 514 x 277. Offscreen PrintWindow produced a blank image on this host, so rendered visual appearance is not verified.
- unittest discovery: 96 tests, 95 passed, one real F8 registration test skipped because another app owns F8. Mocked F8 cancellation during player review passed. No live game input or full withdrawal batch was tested. No new executable/ZIP was built.


## 2026-09-17 Onion candidate and manual shortfalls

- Added explicit grid candidate 洋蒽 for 洋蔥 without lowering global similarity thresholds. Tooltip identity still requires exact recognition or player confirmation. Wool exact-only filtering remains intact.
- Typed material failures before transfer intent are recorded as skipped and processing continues only after storage is verified. Recognized item/quantity overlays may be cancelled with at most two Escape presses; unknown screens stop. Pending transfers, F8, and focus loss never become automatic skips.
- Skipped items persist with reasons, appear in the main GUI independently of debug visibility, and are listed with full quantities in the local report. Explicit per-item manual completion is required to unlock quest submission.
- 108 tests: 107 passed, one real F8 registration test skipped because F8 is occupied. Includes onion review, continuation to the next item, no automatic replay, durable shortfalls, manual-completion gating, overlay recovery, unknown-screen blocking, and pending-transfer preservation.
- No live game input, complete live batch, or newly packaged executable tested in this change.


## 2026-09-17 Material OCR fallback and food tooltip title fix

- User log: five skipped materials; 咻咻蘑菇 and 黃豆 were not found in grid searches, while 烤整顆馬鈴薯, 煎蛋 and 蘋果汁 failed the tooltip gate. Previous gate demanded 材料 under every title. Food-specific failure mechanism is supported by code/log correlation; no actual failing food tooltip screenshot was supplied for reproduction.
- Added acquisition-footer/header geometry detection independent of category, four targeted title OCR variants, four additional grid preprocessing variants before scrolling, and two numeric threshold fallbacks. Different material identities, grade conflicts, plus conflicts and numeric conflicts stay blocked.
- Actual Windows OCR on existing local fixtures: 玉米 tooltip and quantity 1 preserved; supplied 箭花 tooltip and entered 60 preserved. On t12 storage fixture, baseline missed the full 咻咻蘑菇 spelling; fallback recovered it. Storage baseline plus retries took 2.14 seconds in this single run. Tooltip diagnostic including all retries and quantity took 1.62 seconds per fixture. These are offline measurements, not live-game timing guarantees.
- Synthetic tests cover food categories, rejecting bare grid text, fallback coordinate mapping, retry exhaustion, same-cell grade conflict, number conflicts and requested UI ordering/style. All 119 tests passed on this run, including F8 registration (available at test time).
- No live game input, full batch, failing food screenshot reproduction, or rebuilt EXE/ZIP in this change.


## 2026-09-17 Initial multi-method scans, submission OCR, and debug controls

- Storage always runs all five name preprocessing methods on the initial scan of every page, including when the first method found an exact name.
- Quest cells run five atlas methods, including initially empty cells. Conflicting exact whitelist identities remain conflict detections and cannot become fuzzy candidates. Full-screen OCR retains original scale plus four 2x variants; original scale was necessary for the task-tab header in the local quest recording fixture.
- Offline Windows OCR: quest-recording-34 game-area crop produced 16 exact quest labels, zero fuzzy labels and zero conflicts, in 5.38 seconds in one run. Storage, reporting, submission, completion and post-completion fixtures were recognized using the new variant evidence. Source screenshots remained unchanged; no game input was sent.
- Debug copy uses the complete current report under its write lock, not the truncated text widget. Clipboard behavior tested with mocked clipboard calls, leaving the user's clipboard unchanged. Search/success and failure color tags tested while the panel is hidden.
- Live quest submission and a full batch remain unverified; no executable/ZIP build or publication performed.


## 2026-09-17 Soybean omission and withdrawal speed review

- Supplied 637 x 942 storage-panel crop was placed at (0,0) on a blank 1280 x 960 offline canvas, not treated as a live capture. At the visible soybean cell, isolated 2x OCR returned 黃豆; 4x/6x and atlas-only variants omitted it. The new isolated unread-cell fallback returned 黃豆 from the supplied image.
- Current-page-first search removes unconditional rewinds. Storage ROI observations retain five OCR methods and original source pixels. A duplicate initial search observation and pre-quantity title check were removed; name and actual quantity are still checked immediately before transfer.
- Timing and code-review findings are in PERFORMANCE_REVIEW.md. 132 tests passed. No live game input, complete 19-material timing, executable build, commit, push or publication performed. The requested two-thirds overall reduction remains unverified.
