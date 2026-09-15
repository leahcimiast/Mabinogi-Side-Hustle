# Project: Mabinogi Mobile Quest Assistant

## Goal

Build a portable Windows desktop app that automates material retrieval and

whitelisted bulletin-board quests in 瑪奇 Mobile.

Distribute a ZIP containing the executable and required supporting files.

Users must not need Python or Excel installed.

## Target environment

- Game window title: 瑪奇 Mobile

- Process: MabinogiMobile.exe

- Interface language: Traditional Chinese

- Version 1 supports a 1280 × 960 game content area.

- The window may move anywhere on screen.

- Detect the game content area; exclude window borders and desktop content.

- Verify the supported game area and UI scale during setup.

- Foreground automation is the baseline.

- Test background input separately; do not promise support before verification.

## Working rules

- Keep changes small and easy to review.

- Inspect the repository before choosing the implementation approach.

- Create a new branch for each task when working in a Git repository.

- Do not commit, push, publish, or merge without explicit authorization.

- Use pull requests instead of merging directly into main.

- Preserve existing behavior unless a change is necessary and approved.

- Update README.md when setup or usage changes.

- Prefer simple, beginner-friendly code.

- Do not overengineer hypothetical cases.

- Do not commit private screenshots, recordings, logs, or personal data.

- Preserve the supplied reference workbook and recordings.

- Report what was actually tested and what remains unverified.

- Do not implement process injection, memory modification, or anti-cheat bypass.

## Whitelist

Initial reference: whitelist_quest.xlsx

Existing columns:

- Quest Name

- Material

- Qty Per Completetion

Each entry maps a quest scroll to its required material and quantity per completion.

Rules:

- Match exact item names.

- No material substitutions are permitted.

- 採集卷軸: 蜘蛛絲 requiring 蜘蛛網 is intentional.

- The + character is a literal part of applicable item names.

- Required item counts are ordinary numbers without abbreviations.

- Count all matching stacks without double-counting overlapping scroll views.

- Leave non-whitelisted scrolls untouched.

- Allocate shared materials in whitelist display order.

- Allow editing, enabling/disabling, and reordering entries inside the app.

- Support whitelist import/export.

- Preview changes before applying a replacement import.

- App updates must preserve local whitelist edits and settings.

- Add tracked quest names only where needed for reliable identification;

  do not invent mappings.

## Workflow

### Stage 1: Preparation

The player prepares scroll stacks and starts beside the designated storage NPC.

1. Open inventory with I.

2. Select 道具 from the bottom main categories.

3. Select 任務 from the top subcategories.

   - Q moves left; E moves right.

   - 任務 is at the end of the subcategory filters.

   - Selected bottom category is orange.

   - Selected top filter is white.

4. Scan all whitelisted scroll names and stack counts, scrolling as needed.

   - Names appear below item icons.

   - Counts appear at the lower-right corner of item icons.

5. Open storage:

   - Press X.

   - Advance the expected NPC dialogue until the green 保管箱 button appears.

   - Click 保管箱 and dismiss the following dialogue.

   - Switch to 公用保管箱 at the upper left.

6. Scan both storage panels completely:

   - Left: stored items.

   - Right: carried items.

7. Calculate requirements:

   - Required materials = planned completions × quantity per completion.

   - Subtract materials already carried.

   - Use all available carried materials; no reserve setting is needed.

   - Limit the batch to available materials and carrying capacity.

   - Capacity is weight-based; use verified game information.

   - Prepare complete quests in whitelist order.

8. Show the planned completions, carried quantities, withdrawals, and shortages.

9. Require one 開始領取 click before withdrawing.

10. Retrieve every material for the planned batch:

    - Select the stored item.

    - Press Space for 移至背包.

    - Enter the required quantity in the right-side quantity field.

    - Press Space to confirm 移至背包.

    - Verify the transfer before continuing.

11. Pause after the entire batch is retrieved.

Do not alternate between storage retrieval and quest completion.

### Stage 2: Manual movement

The player moves to 任務佈告欄 and presses Start.

Automatic travel to the bulletin board is outside version 1.

### Stage 3: Quest completion

Process one bulletin quest at a time.

1. Open inventory and navigate to 道具 → 任務.

2. Select one eligible whitelisted scroll.

3. Click the green 使用 button.

4. Inventory closes automatically and the activated quest becomes tracked.

5. Verify the expected tracked quest and its reporting state.

6. Click the tracked quest and dismiss the expected dialogue.

7. Enable 自動放入.

   - This toggle defaults to off each time the submission screen opens.

   - Verify the required items were inserted.

8. Press Space to submit.

9. Dismiss the expected dialogue.

10. Verify 任務通關 and the applicable quest identity.

11. Press Space or click 確認.

12. Confirm the completion screen closes and the reporting entry disappears.

13. Only then activate the next scroll.

Example:

- Scroll: 採礦卷軸: 鐵礦石

- Tracked quest: 取得鐵礦石

- Ready-to-report text: 回報任務佈告欄

Never activate a second bulletin quest before the current one finishes.

Activating another can displace the previous quest from the tracker.

## Existing quests and recovery

- If an already-active whitelisted quest is clearly ready, finish it first.

- If it is active but incomplete, pause and explain the missing requirement.

- Never infer that no quest is active solely because reporting text is absent.

- If active-quest state is unknown, require the player to restore tracking

  or explicitly confirm that no bulletin quest is active.

- After interrupted withdrawals, rescan storage and carried materials,

  recalculate remaining withdrawals, and show an updated summary.

- Never replay original withdrawal quantities blindly.

## Controls and failure handling

- Provide a visible Pause button and global emergency-stop hotkey.

- Pause immediately when the game loses focus.

- Require explicit Resume.

- Verify expected screens and action results rather than using blind click loops.

- Use bounded waits; pause on uncertain screens or timeouts.

- Skip clearly identified quests that lack materials and report the shortage.

- Stop when the prepared batch is complete or no eligible whitelisted quests remain.

- Leave remaining scrolls for another player-initiated run.

- Do not automatically return to storage.

## Reports and privacy

- Save a local text report by default.

- Include completed quests, remaining scrolls, shortages, and pause reasons.

- Failure screenshots are optional.

- Nothing uploads automatically.

## Acceptance criteria

- Prepare and complete multiple whitelisted quest types.

- Correctly count and process player-prepared scroll stacks.

- Leave non-whitelisted scrolls untouched.

- Handle insufficient materials and limited carrying capacity.

- Pause on lost focus or uncertain screens.

- Resume interrupted withdrawals without duplicate retrieval.

- Never activate another scroll before confirming the current quest completed.

- Preserve user settings and whitelist edits across app updates.

## Delivery order

1. Verify window capture, text/count recognition, and input compatibility.

2. Implement whitelist editing, scanning, and preparation calculations.

3. Implement reviewed batch withdrawals.

4. Implement the one-quest-at-a-time completion loop.

5. Validate acceptance criteria and package the portable ZIP.

Keep background-input feasibility separate from the foreground workflow.


