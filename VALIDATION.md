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
