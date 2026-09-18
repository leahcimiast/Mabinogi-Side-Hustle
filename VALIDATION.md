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


## 2026-09-17 Transfer prompt readiness regression

- User screenshot shows the centered item tooltip and its green transfer button, not the right-hand quantity dialog. The speed change removed the wait between selection and Space; an ignored early Space left the worker waiting for a dialog that was never opened. Timing causality cannot be proven from the static screenshot alone.
- Added bounded read-only polling of the central button's 190 x 105 crop with green-color evidence and five OCR variants. Space is sent once only after readiness; no replay if the quantity dialog fails to appear. Existing final material/quantity and durable transfer-intent checks remain intact.
- Supplied 1263 x 949 screenshot normalized to 1280 x 960 for offline inspection: prompt_ready=True in 0.359 seconds; quantity_dialog=False. No game input sent.
- Code review checked central-button versus confirmation-button separation, no numeric entry before quantity-dialog evidence, cancellation after OCR, timeout behavior, and absence of Space replay. 137 tests: 136 passed, one real F8 registration test skipped because F8 was occupied.
- Full live transition remains unverified. No commit, push, merge, or packaged executable in this change.

## Potato candidate and recovery UI fix (2026-09-17)

User log at 20:10:00 contains 烤整顆馬鈴 and 烤整馬鈴薯; both score 5/6 against 烤整顆馬鈴薯. The former ranking compares OCR variants as separate candidates and rejects the tied scores. Candidate ranking now keeps the highest score per physical cell before comparing alternatives. Regression covers same-cell variants selecting the potato, different-cell ties remaining unresolved, and recovery panel hidden during active work but shown after an unresolved stop.

Offline suite: 140 tests, 139 passed, one global-hotkey test deliberately skipped. Supplied screenshot is 1272 x 949 rather than the 1280 x 960 capture baseline; it was preserved and not resized for an OCR success claim. Matching tests use the logged text variants with synthetic cell locations. Live withdrawal of potato remains unverified. No packaging or live game input.

## Storage recovery and quantity timing (2026-09-17)

User log: corn requested 30, read back 0 at 20:19:04; no transfer confirmation sent. Shell quantity was unreadable three times, then recovery stopped at 20:20:09. Log cannot prove flashing icons, focus delay, or numeric OCR as the root cause. Added a 0.5-second field-focus delay and 0.15-second cancellable clear/digit gaps. Recovery observes up to six frames, cancels each recognized overlay type at most once, and logs the individual storage markers. Unknown frames receive no input.

Offline suite: 147 tests, 146 passed, one global-hotkey test skipped deliberately. New regressions cover focus-before-type ordering, clear/digit pacing, cancellation, delayed overlay closure, distinct overlays, bounded failure, and no repeated Escape to unchanged overlays. Live game timing and shell number readability remain unverified. Source only; no package or game input.

## Initial identity and quantity-only withdrawal (2026-09-17)

Latest soybean log identified 黃豆 in the list, then title OCR returned 乛/empty. The title gate prevented numeric OCR and triggered manual name review. Per user request, withdrawal now trusts the current selected list candidate and checks only quantity-dialog presence and the entered amount. It no longer calls tooltip-name retries, remembered-name approval, or the name-review UI during withdrawal. Initial candidate uniqueness, wool-grade and literal-plus rules remain in place. Return-to-storage observation and unknown-transfer recovery remain separate from name checking.

Offline suite: 147 tests, 146 passed, one deliberate global-hotkey skip. Updated tests cover absent titles with correct numbers, initial fuzzy candidates without repeated name review, wrong numbers, missing dialogs, and unknown transfer outcomes. Live soybean retrieval remains unverified. No package or game input.

## Assume retrieval on claim dispatch (2026-09-17)

User explicitly requested skipping retrieval-result confirmation. Successful Safety.click dispatch now immediately confirms the withdrawal journal before any cancellable wait. This is an assumed transfer, not observed inventory evidence. Later storage timeout stops navigation but retains retrieved progress and cannot classify it as a manual shortfall or replay it. Input-dispatch errors remain unresolved; quest checks are unchanged. Offline suite: 149 tests, 148 passed, one deliberate hotkey skip. Covers timeout after dispatch, F8 after dispatch, failed dispatch, quantity mismatch, and single transfer after quantity retries. No live game test or packaging.

## Independent quest submission (2026-09-17)

User reported the retrieval test passed with 100% accuracy (user-run evidence). Submission now assumes player-prepared materials and does not require any retrieved-material count or cleared manual-shortfall list. Removed both GUI start/enable gates and runner retrieval prerequisite; removed numbered action labels. No retrieval records are fabricated. Board acknowledgement, pending-action handling, focus/F8, quantity insertion and one-quest completion checks remain. Offline suite: 151 tests, 150 passed, one deliberate global-hotkey skip. New tests cover fresh-batch start, unresolved manual shortfalls not gating submission, and the runner reaching game checks with zero retrieval. Live quest submission remains unverified. Source only; no package.


## 2026-09-17 Submission navigation, name matching, and editable remaining counts

- Source branch: `codex/quest-filter-recognition`; existing uncommitted work was preserved. No commit, push, merge, release, or new executable package.
- Inventory header: corrected the quest-button search band to y=95..175; one large wheel action on the header replaces repeated E presses. The selected quest tab still requires visible confirmation.
- Scroll names: padded the label crop upward, and use isolated 2x green-channel reads in the existing OCR session, with a 4x retry only when needed. Match the unique quest-name tail (same .66 edit-score floor and .08 ambiguity margin as material selection), preserving plus signs, known material/scroll differences, and grade distinctions. No count OCR or repeated tooltip-name confirmation. Activation and completion checks remain.
- Attachment was 1272x947; resized to 1280x960 for offline reproduction only. Original preview missed the first quest. New path located the first cell `(707,247,803,297)` from OCR `採卷軸:鐵礦石` in approximately 0.718 seconds, excluding OCR-session startup. This is a single offline observation, not an end-to-end speed guarantee.
- Added the main-window submission tab with planned/completed/remaining counts. Editing remaining counts preserves the completed sequence; zero skips, fresh batches reset to three. Running, active, and pending states block edits. Retrieval quantities stay unchanged.
- `python -m unittest discover -s tests -q`: 164 tests passed. Includes custom-plan persistence, completed-prefix preservation, zero skipping, invalid/active/pending edits, navigation dispatch, OCR tail boundaries, dashboard reset/locking, and a one-quest completion without tooltip-name rereading. Tk emits an occasional ThemeChanged message while test windows are destroyed; the suite passes.
- UI reviewed at 660x720 using mocked safety and temporary data, with no game input. Reduced table requested heights so footer and local report path remain visible. Private screenshot under ignored `.local/` only.
- Code review completed: checked plan indices/persistence, no completed-quest replay, activation/completion guards, whitelist/material separation, OCR cell bounds/batch limits, GUI worker locking, and reuse of the OCR session. `git diff --check` passed. No outstanding issue found in the reviewed changes.
- Not live-tested: whether this game build accepts the large header-wheel gesture, every scroll name at native capture size, and the full quest submission batch. No game input sent during validation.


## 2026-09-17 Inline per-quest editing and navigation follow-up

- Branch: `codex/inline-counts-fast-navigation`; prior uncommitted changes preserved. No commit/push/package.
- Removed the separate quantity/apply bar. Clicking an individual remaining-count cell opens its editor; Enter/focus loss saves only that row, Esc cancels. Scroll/resize commits before moving the editor. Running/active/pending guards and completed history remain.
- Replaced ineffective vertical header wheel with a 410-pixel horizontal drag (12 paced steps). If the quest tab is still absent, bounded E fallback checks the small inventory controls after each key, up to seven keys. Existing visible/selected quest tabs bypass unnecessary navigation.
- Navigation and scroll search now use small header and 道具-label crops with five OCR variants including native scale. Native scale was necessary to recover the white selected 任務 tab in the supplied screenshot. All ten crop images share one batch/session; five-second per-batch timeout.
- Offline attached screenshots normalized to 1280x960 for testing only: stopped-at-全部 image read 道具 and correctly did not claim 任務 selected (0.510 s); prior selected-任務 image read both and confirmed selection (0.248 s). Same-session full-screen observations took 3.039 and 3.217 s respectively. Single-run measurements exclude startup/input/animation and are not full-loop timing guarantees.
- Full test suite: 172 tests passed. Added real Tk click/focus/Enter row editing, invalid/cancelled edits, drag-success navigation, bounded E fallback, paused input rejection, and drag-button release on F8/focus loss. Existing Tk teardown warnings remain non-failing.
- Reviewed own-window render at 660x720, including active inline editor and footer. Screenshot remains under ignored `.local/`.
- Code review checked input release paths, stop/focus checks per drag step, fallback bounds, OCR coordinate remapping, single-row edits, persistence and worker locking. Fixed Treeview's default click handler stealing editor focus by consuming the handled cell click. `git diff --check` passed.
- Still unverified in the live game: drag acceptance and end-to-end submission. No game input was sent during these tests.
### 外觀修改驗證（2026-09-17）

- PR 分支完整測試：135 項通過，包含按鈕 callback／disabled、動態輸入框與縮放狀態檢查。
- 最新未提交功能快照：172 項完整測試通過；其中 27 項 GUI 測試亦以獨立 Tk 程序通過，涵蓋行內編輯、Enter/Escape、交付前確認、停止與核對流程。
- 實際 Tk 視窗檢查：素材頁、任務行內編輯、除錯展開與待核對區；修正底部紀錄資訊與清除名稱按鈕的可見性。
- 原始碼審查：GUI 僅增加主題 import／初始化與視窗尺寸掛接，未更換元件、callbacks、事件綁定或批次流程。未發現阻擋合併的問題。
- 本機 PyInstaller ZIP 建置成功；打包後 offline diagnostic 成功，19 種素材／57 次、sent_keys=0；確認包含 desktop_theme 與 PIL.ImageTk。
- 尚未驗證：多螢幕間動態 DPI 切換、完整遊戲批次，以及打包後完整互動流程。GUI 測試使用暫存資料與 mock Safety；本次未向遊戲送出輸入。未發布 release。


## 2026-09-17 PR #3 integration validation

- Integrated PR #3 head `150ec792e39b6f89dc11afd9520aa6920ca905a6` with the latest withdrawal and submission changes. GUI hooks merged cleanly; README and validation append conflicts were resolved by preserving both sets of content.
- Combined suite: 175 tests passed, including the three desktop-theme tests and current inline editor/navigation/safety tests. Existing Tk teardown warnings were non-failing.
- Visually reviewed the actual themed task table with an active inline editor using temporary data and mock Safety; editing one row and debug expand/collapse also passed. Screenshot remains private under ignored `.local/`.
- Reviewed staged GUI/theme diff: only theme import/initialization and debug resize hooks modify the functional GUI; automation/input/batch modules are unchanged by the theme merge. No blocking compatibility finding. `git diff --check` passed.
- No new portable package or release. In-game full-batch and dynamic multi-monitor DPI limitations remain unverified.


## 2026-09-17 Quest Use-button detection

- Branch `codex/quest-use-button-detection`. Replaced the broad lower-screen Use lookup with a dedicated 130x90 crop, five small OCR variants, a green enabled-button check, and bounded waiting. Only the two-character button text area contributes evidence; the action clicks the verified button center. No tooltip-name reread. Activation journaling, post-activation identity and completion guards remain unchanged.
- Supplied screenshot is 1273x949 and was normalized to 1280x960 for offline testing. Old full-screen OCR did detect Use offline, so the exact live failure was not reproduced. Dedicated detection found Use at `(695,875,790,920)` in 0.328 seconds excluding OCR startup. No live input was sent.
- Six new Use-button tests passed (crop recovery, disabled color, unrelated/out-of-region text, observation-only retry, F8 after OCR, timeout). Existing single-quest integration test exercises the new center click and completion flow.
- Non-GUI regression: 151 tests run, 150 passed, one F8 registration test skipped. Eight isolated GUI tests passed; the existing inline-edit GUI test hangs in Tk `update` even in isolation. Full-suite retry was bounded with a 45-second traceback timeout; isolated GUI attempt timed out after 15 seconds. Full GUI regression remains incomplete; no GUI files changed in this fix.
- Code review checked crop coordinates, enabled-state evidence, exact button text, bounded OCR/waiting, focus/F8 checks before and after OCR, and journal intent before activation. No blocking issue found in this change; `git diff --check` passed. In-game validation remains outstanding. No commit, merge, package or release.


## 2026-09-17 Tracker activation recognition and existing-task recovery

- Reproduced the supplied 1270x948 screenshot after offline normalization to 1280x960: all useful OCR variants omitted 取得 from the title, retained 鐵礦石, and read 回報任務佈告欄. The prior tracker predicate therefore returned None despite successful activation.
- A bare exact item name now requires title-sized text and a nearby report row in the same tracker area. Smaller carried-count text, missing/distant report rows, different grades/plus signs, duplicate title rows, and conflicting OCR identities remain rejected. Full/prefix-missing variants of the same title no longer conflict. Completion name evidence uses exact canonical item identity rather than a bare-name substring.
- Fresh-session recovery may adopt only the current planned quest when its identity and nearby ready-report row are both visible. It records the observed active state and proceeds without using another scroll. Different/unknown existing tasks and unresolved journal intents still stop. Saved full titles may resume from a prefix-missing read; explicit action changes remain rejected.
- Updated screenshot result: tracker 鐵礦石, report 回報任務佈告欄, world=True. No game input sent.
- Non-GUI regression: 164 tests run, 163 passed, one F8 registration test skipped. Added 13 tracker/recovery/completion-name cases, including no duplicate activation and mismatched report rejection. GUI code was unchanged; the previously documented Tk regression hang was not rerun.
- Code review checked tracker geometry, exact identity/grade boundaries, cross-variant disagreements, observed-state adoption, intent recording, and completion guards. `git diff --check` passed. Live submission remains unverified; no commit, merge, package, or release.


## 2026-09-17 Active whitelist quest first

- Submission checks the world/tracker before inventory. Any unique ready whitelist task can be adopted regardless of its current plan position. One existing scheduled completion is moved to the front of the remaining sequence without altering the completed prefix or other quest totals; if its remaining count was zero, only the already-active completion is added.
- Adoption persists identity and the reordered plan, but does not increment completed. Completion is credited only after the existing submission, completion-banner, and closed/report-disappeared checks. Subsequent inventory activation follows the original remaining order. Pending journal intent, unknown/ambiguous/non-whitelist reports and recognized incomplete tasks block new activation.
- GUI reads the journal's current plan so per-quest completed/remaining rows stay correct after reordering. Confirmation wording now allows an already-active whitelist quest. A zero-total plan can still inspect and submit an existing task.
- Non-GUI suite: 169 run, 168 passed, one F8 registration test skipped. New tests verify persisted reordering, prefix preservation, zero remaining, failed-save rollback, and wool-first completion followed by the normal iron-scroll cycle without an initial inventory open. Two targeted GUI tests passed for per-row completion accounting and zero-plan startup. Full GUI suite was not rerun due to the previously documented Tk update hang.
- Code review checked identity uniqueness, material mapping, save rollback, no premature/double credit, plan/GUI synchronization, and no inventory activation before current completion. No blocking finding; diff checks passed. No live game run, commit, main merge, or package.


## 2026-09-17 Partially read active-task prefix

- Reproduced the supplied desktop screenshot: OCR returned 得鐵礦石 (one variant with a trailing pin-like tilde) and a nearby 回報任務佈告欄. The previous normalizer handled full or fully missing action prefixes, but not a partially missing prefix.
- Normalization now handles partial 取得/製作 prefixes and trailing pin-like OCR marks. Partial titles still require the full exact item identity, title-sized text, and their own nearby reporting row. Grade and literal plus distinctions and cross-variant conflict checks remain enforced. Active-task detection logs raw tracker text and the number of matching whitelist entries on failure.
- Offline replay cropped the supplied desktop image to the game area and normalized it to 1280x960; this does not change live capture geometry. The updated real OCR path returned 得鐵礦石 and exactly one matching whitelist entry: 採礦卷軸: 鐵礦石. No live game input was sent.
- Non-GUI regression: 172 run, 171 passed, one occupied F8 registration test skipped. Added partial-prefix/pin, missing-report, grade/plus, and conflicting-variant cases. GUI tests were not rerun; the previously documented full GUI regression limitation remains.
- Code review checked normalization boundaries, report anchoring, whitelist uniqueness, and unchanged completion accounting. No blocking finding; diff whitespace check passed. Live submission, executable packaging, commit and merge remain unperformed.


## 2026-09-17 Submission controls without material OCR

- Removed material-name OCR from submission and submit-readiness checks as requested. On the identified submission screen, enable auto-insert unless already visibly on, then wait for the green submit button. No material/count scanning was added. Completion identity, journal intent, closed/report-disappeared checks, and foreground/F8 protection remain.
- Submission/dialogue/completion observation now reads four small regions with five OCR variants, mapped back to game coordinates and batched at no more than 12 images. The full-screen path resumes before verifying the closed completion screen. Native-scale recognition and a wider header crop preserved the older t43 submission reference.
- Supplied screenshot replay: submission=True, auto-insert=False, ready=False without reading material names. Same-session benchmark excluding OCR startup: full-screen 1.298 seconds versus cropped 0.608 seconds. This is an offline observation comparison, not an end-to-end live timing promise. Existing t43/t45 submission references and t47 corn completion were checked; no live game input was sent.
- All 176 non-GUI tests passed, including material-OCR rejection in the full submission cycle, auto-insert click, readiness without material text, disabled-button rejection, bounded cropped OCR, coordinate mapping and safety checks. Existing GUI regression limitation remains; GUI was not changed in this task.
- Code review checked no premature completion credit, no inventory activation during an existing quest, no toggle-off when visibly enabled, reader scope and batch bounds, and read-after-click before submit. Diff whitespace check passed. No commit, merge, package or release.


## 2026-09-17 Split tracker action OCR

- Reproduced the supplied screenshot and matching local failure log. Four variants retained the full iron-ore identity; the threshold variant split the title into an isolated 取得 and 礦石~. The empty canonical identity from 取得 incorrectly vetoed the four complete reads.
- Ignore action-only fragments when checking conflicting identities. They cannot positively identify a quest; an independently accepted full item title is still required. Conflicting actual item names, grade/plus distinctions and position checks remain. Leading bullet normalization now also applies to conflict checks; conflict messages include the raw conflicting text.
- Real OCR replay of the supplied game-area crop now produces exactly one whitelist match, 採礦卷軸: 鐵礦石. No screenshot is tracked and no live game input was sent.
- Non-GUI regression: 178 tests run, 177 passed, one occupied F8 registration test skipped. New tests cover full-title plus split-action variants, rejection of split-only evidence, and conflicting bulleted grade text. Code review checked empty-identity rejection, preserved actual conflicts and unchanged completion accounting. Diff whitespace check passed. No commit, merge or package.


## 2026-09-18 Compact dashboard and button-based completion

- Replaced submission checkbox with the exact requested static reminder and removed its start gate. Existing pending-result reconciliation remains. Compact button padding/borders, cards, table headings and tabs reclaim vertical space; debug actions share one row, and the text area is no longer forced to six lines by the theme.
- Per the latest request, post-submit completion now uses the bottom green confirmation control geometry: width 450-550, height 45-85, centered near x=640/y=885-925, over 80 percent green coverage. It no longer depends on completion-title OCR or the moved title on special-reward results. Small inventory Use buttons, middle-screen submit controls and missing buttons fail. The runner checks this directly only during pending completion before slower OCR; close-screen/report-disappearance verification still precedes credit and the next scroll.
- Supplied special-reward screenshot passes without OCR. The older reference captured before the green confirmation appears does not yet count as complete; the runner waits for the button. No live game input sent.
- GUI preview used temporary data/mock Safety with recovery visible: button height 29 pixels, log text area 579x222 pixels, exact static reminder. Visually reviewed the enlarged readable log and compact layout. Four targeted GUI/theme tests passed; existing non-failing Tk ThemeChanged teardown warning remains. Full GUI regression not rerun due to earlier documented hang.
- Code review checked button geometry, post-submit-only fast path, focus/F8 checks, journal accounting and unchanged recovery guard. No commit, merge or executable package. Running session has pending completion; it was not restarted or its progress discarded.


## 2026-09-18 Quest tab fresh-position selection

- Supplied post-failure screenshot correctly yields the rightmost 任務 label at game coordinates (1174,133)-(1204,147), center (1189,140). The screenshot cannot establish the position used by the earlier click. Existing navigation accepted substring matches and reused the observation preceding selection without corrective clicks.
- Quest-tab lookup now requires an exact label. Re-read the small inventory controls immediately before each click, log its coordinates, and verify selected state immediately afterward. Up to three fresh-position clicks are allowed; missing identity, focus loss/F8, or persistent wrong selection stops. Inventory scroll search still requires the quest filter to be selected.
- Regression covers moved tab coordinates, wrong-category correction, exact matching and bounded three-click failure. All non-GUI checks passed except the occupied global F8 registration skip; GUI unchanged. Code review checked fresh-coordinate use, bounded inputs, safety calls and selected-tab guard. Diff check passed; no live input, commit, merge or package.


## 2026-09-18 Fixed quest filter navigation (user override)

- Replaced OCR-based quest-tab navigation with two full header swipes from (1185,135) to (775,135), 350 ms settle after each, and one fixed click at (1189,140). The supported layout has only a short overflow; repeated full swipes saturate the right endpoint. Live end-position reliability remains unverified.
- Removed quest-tab OCR, selected-tab OCR during scroll search, and E-key fallback. Bottom 道具 identification now crops only the bottom category, not the header. Scroll-name matching, activation and completion handling remain; every input and capture still checks focus/F8.
- Non-GUI regression passed; navigation tests verify two swipes, fixed click, no tab OCR/E, and no quest click after interrupted drag. Review checked scope, game-relative coordinates, bounded swipes, retained item matching and failure propagation. No live game input, commit, merge or package.


## 2026-09-18 Single filter swipe

- Per user request, reduced quest-filter navigation to one complete swipe followed by the existing 350 ms settle and fixed-position click. No tab OCR or E-key fallback. Reviewed the diff: no change to material storage scrolling or quest recognition. The two navigation regression tests passed; live game validation remains outstanding.


## 2026-09-18 Visible zero during inline count editing

- Inline quest-count entries now use a dedicated flat, zero-padding style rather than rounded form-entry chrome. This keeps the editable text within the compact row instead of clipping it until the editor closes.
- GUI validation with temporary data and mock Safety: typed value 0 is visible before Enter, editor requests 21 pixels within the 28-pixel row, and cancelling preserves the original 57-count plan. Visually inspected the actual app window screenshot. Entry bindings, Enter/focus-out save and Escape cancel remain unchanged.
- Reviewed the two-line functional/style application boundary; other entries retain their existing style. No live game input or running-batch change. Diff whitespace check passed.


## 2026-09-18 Per-row steppers, spider tracker and scoped cycle OCR

- Each quest row now offers minus/plus click cells, immediately persisting its remaining count with zero floor and existing active/pending/worker guards. Real UI click and screenshot verified; two targeted GUI tests verify persistence, row isolation, zero floor and pending lock.
- Reproduced spider screenshot: title is 尋找蜘蛛網. Added 尋找 to supported action prefixes and preserved the whitelist mapping from 蜘蛛絲 scroll to 蜘蛛網 material. Exact item, grade/plus and action-conflict rules remain.
- Quest-cycle world/tracker captures use the top-right quadrant rather than full-screen OCR; post-activation capture reads only that quadrant, while startup/closure also reads the small bottom-left world indicator. Native and 2x color variants retained; the threshold variant incorrectly truncated spider-web text and was excluded from this targeted reader. Other workflows retain their existing OCR paths.
- Real screenshot replay passed for spider web, arrow flower and iron ore. Tracker-only observation took 0.451/0.475/0.418 seconds respectively, excluding OCR startup; earlier full-screen spider observation took 2.505 seconds. Timings are offline measurements, not a live-cycle guarantee.
- Use-button recognition now reads fixed green geometry after a known scroll is selected, without OCR; side patches reject the wider completion button. Existing fixed quest-tab, auto-insert, submit and completion actions retained. Identity OCR is not replaced by an assumed quest.
- Non-GUI regression passed with one occupied F8 skip; targeted GUI/recognition tests and actual stepper click passed. Review checked coordinate mapping, crop bounds, no premature count credit, pause/focus checks, exact spider mapping and isolated GUI controls. No restart, journal modification, commit, merge or package; current pending activation remains for player reconciliation.


## 2026-09-18 Truncated tracker reading and pin punctuation

- Actual run log showed 尋找蜘 vetoing the complete spider-web identity. Offline screenshot replay additionally reproduced a trailing comma in 尋找蜘蛛網,. Both are now handled without accepting an incomplete identity on its own.
- A conflicting prefix fragment is ignored only if another variant independently matches the full exact item, the fragment shares the action and title location, and its right edge is at least eight pixels shorter. Literal-plus targets are excluded from this exception. Non-prefix names, grade differences, full-width conflicts and action changes still stop. Trailing comma pin noise is removed during canonicalization.
- Supplied screenshot passes tracker and report recognition. All 185 non-GUI tests passed, including fragment-only rejection, different-material/action rejection, geometry restriction and plus preservation. Code review and diff check passed. No game input, running-batch modification, restart, commit or package.


## 2026-09-18 Report-indicator-only after known activation

- Store the selected scroll identity in the activation intent. Once its use has been dispatched, wait only for the bulletin-board report indicator in the upper-right crop. Click that report row directly; no tracked-title matching or cross-variant title conflict is evaluated for a recorded active quest.
- Initial adoption of an unrecorded existing task still matches its whitelist identity for correct accounting. Multiple distinct report rows stop. Completion still requires the large green bottom result control, closure/world evidence and absence of the report row before incrementing the recorded quest.
- Full-cycle test now raises if tracker-name matching is attempted after scroll use; known-active resume likewise rejects any title OCR call in its fixture. Existing unknown-task, interrupted activation, and completion accounting checks remain. Non-GUI suite passed; targeted report ambiguity test passed. Review checked single-quest ledger continuity, intent-before-input and no premature completion credit. No restart or player progress mutation; live report-row click remains unverified.


## 2026-09-18 Skip missing planned scrolls

- The existing bounded scroll search now raises a distinct missing-scroll outcome. Only this outcome removes every remaining occurrence of the current quest from the submission plan, with a persisted count/reason and save rollback. Completed prefix and other quest quantities are unchanged. The runner closes inventory and verifies the world before continuing; no skipped count is credited as completed.
- Active/pending journal entries cannot be skipped. Ambiguous OCR, focus/F8 failures and unknown activation/submission outcomes retain their prior stop behavior. GUI reads the revised journal plan and displays zero remaining for the skipped task.
- All 191 non-GUI tests passed. Added reload/prefix preservation, save rollback, active/pending rejection, next-kind continuation and non-missing failure tests. Code review checked catch scope, input ordering, persistence and no duplicate activation. Diff check passed. No game input, restart, live-batch mutation, commit or package.


## 2026-09-18 Faster missing-scroll search

- Previous search compared exact bytes from the icon-and-text panel and could repeatedly OCR twenty observations when animated pixels changed. Now compare blurred grayscale name strips with noise tolerance before OCR; icon/count regions are excluded.
- One stationary observation triggers one alternate-position wheel retry; a second stationary observation ends search with the existing missing-scroll skip outcome. A stationary list gets one normal/enlarged OCR pair, not twenty pairs. Search cap reduced to six observations; lists beyond that bounded range may be skipped, per the requested speed tradeoff.
- Non-GUI suite: 195 run, 194 passed, one occupied F8 test skipped. Added icon/noise exclusion, real name-area motion, stationary early exit and six-observation bound tests. Review checked safety checks before/after captures and OCR, no repeated activation, unchanged missing-quest accounting and separate storage scrolling. Diff check passed. No live-game timing claim, restart, commit or package.


## 2026-09-18 Reuse inventory and start from materials

- Reuse the open quest inventory between missing-scroll skips; no I press, category navigation, or world-screen wait between them. Search still resets list position for the next quest. Successful scroll use clears the open-inventory state so the next completion cycle can open inventory normally.
- At submission startup, if the world screen is absent, inspect only the existing bottom inventory category. A recognized inventory (including material filter) navigates directly to the quest category without toggling I. Unknown screens still stop; pending results still require reconciliation. Restart/resume re-detects the screen instead of trusting a stale inventory flag.
- Non-GUI suite: 197 run, 196 passed, one occupied F8 test skipped. Tests cover no inventory toggle or redundant world read after skip, material-page startup without I, and no action from unknown screens. Review checked inventory-state reset after use, unchanged journal accounting and foreground/F8 behavior. Diff check passed. No runtime restart, live-batch mutation, commit or package.


## 2026-09-18 Board readiness and post-submit delay

- Log shows milk activation timed out, followed by manual activation reconciliation as not happened and startup world-detection failures. Supplied screenshot confirms an existing ready milk task. Offline replay reproduced report OCR as 回報壬務佈告欄; the exact chat prompt was readable in one native crop but may be absent in live observations.
- Accept a ready bulletin report without requiring the separate chat-text world indicator at startup. Existing-task adoption still matches the whitelist. Report recognition accepts exact 回報 and 佈告欄 around a noisy 任務 word; no board/report word alone suffices. Retry missing report/chat evidence in small dedicated regions only.
- After submit intent, recognize the green completion control first; otherwise OCR only the dialogue crop with two variants, rather than all submission controls with five variants. Dialogue-loop pauses reduced to 100 ms; input settling and foreground/F8 checks remain. No blind dialogue advance or premature completion credit.
- Screenshot replay passes milk identity, report and world recognition. Added tests for chat-absent ready-task adoption, report-word noise, targeted retry and dialogue-only pending-completion reader. Non-GUI regression passed with one occupied F8 skip. Review checked startup/adoption boundaries, capture safety and completion accounting. Diff check passed. No live speed claim, restart, batch mutation, commit or package.


## 2026-09-18 Version 1.0.0 release review

- Release branch preserves the current working-tree feature set; other linked worktrees are untouched. No gameplay behavior changes were made during release preparation.
- Full unittest suite: 289 tests passed in 22.556 seconds, with no failures or skips, including GUI, pause/resume, focus gates, journal recovery, active-quest adoption, missing-scroll accounting, OCR distinctions, and stock scanning.
- Reviewed automation/journal transitions, input cancellation and short-drag release, scoped OCR and literal-plus/material distinctions, Tk worker event handoff, stock overlap accounting, and packaging inputs. No new release-blocking regression identified in this review.
- Known boundaries remain: OCR can miss hidden/untracked quests; prepare the tracked quest state before starting. Quantity entry is not read back and game-side clamping is not detected. Short gestures finish releasing the mouse before resumable pause. Full live 19-material/57-quest execution, complete stock scans across layouts, and mixed-monitor DPI remain unverified.
- Version 1.0.0 is shared by app title, build validation, and Windows executable metadata. Packaging includes only the frozen app, required resources, and release documentation; private captures, recordings, workbooks, local logs, and player settings are excluded.

- Release-candidate ZIP passed CRC and SHA-256 checks; all required OCR scripts, default whitelist, icon, and documentation were present. No private reference workbooks, recordings, logs, settings, or batch history were included.
- Extracted executable passed offline diagnostics: Tk initialized, 19 whitelist entries, 19 material requests / 57 planned completions, 352 OCR words and 19 detections from the existing private quest fixture, zero game inputs.
- Packaged main GUI launched with temporary LOCALAPPDATA, exposed the v1.0.0 window title, created its isolated journal, and closed cleanly. Real player data was not modified. Windows FileVersion and ProductVersion both read 1.0.0. This is a startup smoke test, not a live gameplay test.
- Corrected a build-only relative version-resource path discovered by the first packaging attempt; the successful build uses an absolute path. Gameplay code was not changed during release preparation.


## 2026-09-18 Player documentation and single-EXE package

- Rewrote README around player preparation, retrieval, submission, stock checks, pause/recovery, and reset. Removed developer commands, implementation chronology, and contradictory obsolete UI instructions. Changelog now contains player-visible release notes; development history and build instructions remain under docs/ and are excluded from the download.
- Build uses PyInstaller onefile with the same embedded whitelist, icon, OCR scripts, and version resource. ZIP contains exactly MabinogiAssistant.exe, README.md, and CHANGELOG.md. VALIDATION.md is not a runtime dependency and is no longer packaged.
- Reviewed the build diff and app resource paths: existing sys._MEIPASS resolution supports extraction; settings remain in LOCALAPPDATA; OCR child process uses the extracted absolute script path. No gameplay code or behavior changed.
- Tested the EXE alone in an isolated folder with Chinese characters and spaces, without accompanying README/resources and with Python omitted from PATH. Offline Tk/OCR diagnostics passed: 19 whitelist entries, 57 planned completions, 352 OCR words, 19 detections, zero game input. Diagnostic run took 8.50 seconds on this computer.
- Main GUI title appeared in approximately 2.55 seconds (including polling overhead); isolated settings were preserved, journal initialized, GUI closed cleanly, and onefile temporary runtime was removed after both runs. Real player settings/progress were untouched. These timings are not guarantees for other PCs.
- CRC, exact ZIP contents, document equality, and SHA-256 checks passed. Existing 289-test release result still applies to unchanged gameplay source. Full live gameplay limitations remain unchanged. Windows Traditional Chinese OCR is still an OS prerequisite; no different recognition engine was introduced.

## 2026-09-18 Shellfish quantity retry

- User log: 19:50 run counted shellfish 58; 20:02 run recognized its name but all eight count methods returned None. Final result correctly remained uncertain, although the player table displayed zero recognized stock.
- Supplied 1832x955 screenshot replay (left game area cropped, no scaling) reads shellfish 58. A screenshot-derived count box displaced downward by 12 pixels reproduces eight empty readings. This demonstrates sensitivity to row/crop position; the actual failing capture was not available, so the precise live cause is not proven.
- Only an all-empty count result receives three bounded same-cell vertical retries. Each position requires multiple agreeing OCR methods; at least two positions must produce the same count. Conflicting/nonempty original readings retain their existing unresolved behavior; confirmed stacks are untouched. Screenshot-derived failure recovered 58.
- Reviewed scope, crop bounds, cancellation checks before/after each OCR batch, quantity consensus, and no inferred/expected counts. No gameplay input, state reset, or running-player process changes were made.
- Corrected an existing GUI regression assertion that still expected the pre-release title version; it now uses APP_VERSION.
- Full regression run: 294 tests, 293 passed and one skipped because the running application owns F8. No failures. Live shellfish scan remains to be verified with the local test package.

## 2026-09-18 Version 1.0.1 release

- Final release regression: all 294 tests passed in 22.750 seconds, no skips or failures.
- Reviewed bounded count retry, same-cell bounds, two-position agreement, no retry for nonempty/conflicting initial counts, cancellation before/after OCR, and preservation of confirmed stacks. No additional blocking findings identified. Actual failing capture was unavailable; the log and screenshot-derived crop failure support the targeted fix, while live scan validation remains outstanding.
- Version 1.0.1 matches the app source, player README, changelog, executable FileVersion/ProductVersion, and ZIP. Packaged code includes retry_missing_count.
- Final three-file ZIP passed CRC, content equality, and SHA-256 checks. EXE-alone diagnostics in an isolated Chinese/spaced path passed Tk and OCR (352 words, 19 detections, zero game inputs). GUI showed v1.0.1, preserved isolated settings, closed cleanly, and removed extracted runtime files. No player data or game input was changed.
