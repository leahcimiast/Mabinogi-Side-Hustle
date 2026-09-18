# Development

Requires Windows, Python 3.12, and Traditional Chinese Windows OCR support.
Run commands from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install PyInstaller==6.22.3
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 -Python .venv/Scripts/python.exe
```

`app/version.py` is the version source. The build creates a timestamped single-file EXE package and a SHA-256 sidecar without overwriting earlier builds. Only the EXE, README.md, and CHANGELOG.md are distributed. Runtime resources resolve through `sys._MEIPASS`; settings and reports stay in LOCALAPPDATA, outside the temporary extraction folder.

Review and test packaged Tk startup, icon/resource loading, offline OCR (including its PowerShell child process), clean exit, ZIP contents, and checksum. Use temporary LOCALAPPDATA for GUI tests to preserve player progress. Developer evidence remains in ../VALIDATION.md; historical change notes are in DEVELOPMENT_HISTORY.md. Neither is packaged.


## Test scope (v1.0.1)

The suite covers the three current player actions: fixed-batch material retrieval,
quest submission, and independent shared-storage stock checks. Keep regression
coverage for focus/size checks, pause/resume, uncertain input outcomes, prevention
of duplicate transfers, and verified quest completion before the next activation.
Stock checks retain the missing-count crop retry introduced in v1.0.1, including
agreement, conflicting readings, cancellation, and already-confirmed counts.

The September 18 cleanup removed 24 obsolete or duplicate cases: retired tooltip
name approval and preview review sessions, withdrawal quantity OCR readback,
manual-retrieval confirmation, the old inline editor theme check, and weaker quest
checks already covered by stronger tests. App behavior was not changed.

`test_diagnostic_preview.py`, inventory-recognition tests, and name-candidate tests
remain relevant to `main.py --diagnose` and `scripts/benchmark.py`; they do not
represent additional player GUI steps. Legacy saved-name loading tests remain
because startup still reads that settings file. The stock-count fixtures now
supply all eight OCR method results used by the current reader.

Validation after cleanup: 270 tests passed, no skips. The suite uses synthetic
images, mocked game input, and isolated GUI settings. Its Windows hotkey test may
skip if F8 is occupied. Automated tests do not replace a live-game acceptance run
or the packaged-EXE checks described above.


## v1.0.2 stock-count follow-up

A replay of the September 18 recording at 24, 26, and 28 seconds reproduced
missing shellfish counts. The new bounded fallback masks colored icon pixels,
keeps the full horizontal count region, and requires two OCR methods at each of
two vertical positions to agree. Any original weak reading must also agree;
conflicting original counts and already-confirmed counts do not enter this retry.
All three replay frames recovered 57, preserving every previously confirmed count.
Private frames and replay results remain under ignored `.local/video-shell`.

The table and copied report now preserve unknown shortages from the stock model.
Post-fix validation: 277 tests run; 276 passed and the real F8 registration test
skipped because the hotkey was occupied. No live game input was sent during replay.


### Follow-up after the second live failure

Compressed video replays passed while the player's live scan still failed. A
lossless screenshot replay exposed sensitivity to the label-row offset: the
original neutral retry moved only downward and returned on an unreadable crop.
The retry now checks six positions from -16 to +4 pixels in four-pixel steps,
ignores empty positions, and requires at least two positions with two agreeing
methods each. Any conflicting numeric reading still stops acceptance. All crops
keep the original horizontal bounds; cancellation remains checked around each OCR.
Debug logs include the per-position numeric votes.

Verified 57 using lossless pixels at five row offsets (960, 964, 968, 972, 976 before
the simulated 528-pixel scroll), plus six frames across both supplied recordings.
This is offline reproduction, not a successful live-game acceptance run.


## v1.0.2 report-line OCR fallback

When ordinary tracker OCR finds an incomplete report phrase below an action title,
retry only that right-aligned instruction with 12 bounded contrast/scale variants.
Normalize dim pixels for white/yellow masks. Preserve the shared report predicate,
multiple-report rejection, active-quest identity checks, and completion verification.
The existing 20-second activation wait captures fresh frames; no extra game input
or blind activation retry was added. Local logs include the cropped OCR readings.

The supplied activation-failure screenshot now yields the full board/report terms
at brightness factors 0.65, 1.0, and 1.35. These are offline image tests, not live
acceptance. Some synthetic tiny low-contrast text remains unreadable and is safely
rejected; the fallback does not guarantee recognition on every possible background.


### v1.0.2 release validation

The shared tracker report predicate accepts 回報 plus at least one of 佈/告/欄,
while retaining the original 回報任務 form. This applies to all 19 whitelist
quests; initial adoption still requires a unique nearby whitelist identity.
Completion is credited only after result closure and report disappearance.

The supplied screenshot reproduced the failure before this change and now returns
告回報 with 取得貝類 through the production tracker OCR path. The regression suite
passed all 287 tests, including adoption, completion and cycle continuation for
each of the 19 whitelist entries. Tk emitted teardown ThemeChanged warnings but
no test failed. Code review covered report consumers, stock-count disagreement,
cancellation and completion accounting. No blocking findings were identified.
The packaged executable passed offline startup with 19 whitelist entries and
zero game inputs; ZIP integrity and SHA-256 were checked. Live-game completion
and live performance remain unverified.
