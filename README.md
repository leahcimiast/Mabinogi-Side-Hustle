# 瑪奇 Mobile 任務助手

Windows 桌面原型；第一階段提供唯讀擷取、白名單載入與 OCR 預覽，以及由使用者個別啟動的 I 鍵測試。尚未實作領取材料、啟用卷軸、交付任務或移動角色。

## 直接啟動（不需要 Python 或 Excel）

1. 解壓縮交付的 `MabinogiAssistant-milestone1-*.zip`，保留整個資料夾與 `_internal`。
2. 雙擊 `MabinogiAssistant.exe`。
3. 使用 Windows 10/11 x64，需有 Windows PowerShell 5.1 及繁體中文 OCR 語言功能。本機驗證環境為 Windows 11 x64。
4. 若提示缺少 OCR，至 Windows「設定 → 時間與語言 → 語言與地區」新增繁體中文（台灣），安裝語言選項中的光學字元辨識。受組織政策管理的電腦可能需要管理員協助。

OCR 使用本機 Windows.Media.Ocr，不上傳圖片。程式只對隨附 OCR 子程序使用 `-ExecutionPolicy Bypass`，不變更 Windows 的持久執行原則；若組織政策阻擋，顯示錯誤並停止辨識。

## 操作順序

- **參考圖片**：載入 PNG/JPG。一般圖片保留原尺寸；1920 × 1080 黑底錄影截圖只在符合已驗證的左上角配置時裁切 `(0,0,1280,960)`。參考圖不能通過即時設定驗證。
- **載入 Excel**：唯讀載入 `whitelist_quest.xlsx`。須為單一工作表，欄位為 `Quest Name`、`Material`、`Qty Per Completetion`。19 筆預設資料隨程式提供；原 Excel 未修改、未打包。
- **辨識預覽**：橘框顯示 OCR 文字位置，綠框與表格顯示完整符合白名單的名稱。表格座標以原圖片左上角為原點，單位為像素。
- **偵測遊戲**：列出 `瑪奇 Mobile`／`MabinogiMobile.exe` 視窗；只允許單一候選，擷取前再次確認程序名稱。
- **3 秒後唯讀擷取**：在倒數期間切回遊戲。遊戲必須為前景、未最小化、完整在螢幕內且未被其他視窗遮擋。以 DPI-aware Win32 client rectangle 擷取，不包含標題列或邊框；僅接受 1280 × 960，不把錄影畫布尺寸當作遊戲尺寸。
- **確認本次遊戲 UI 比例與內容**：檢查預覽完整、沒有黑邊或遮擋，確認圖示與文字比例。第一階段的 UI 比例驗證需要人工核對，尚無自動 UI 比例分類器。換圖或再次擷取會清除確認。
- **Start / Resume：單次 I 測試**：先關閉聊天、NPC 對話、交易等視窗。每次明確確認後倒數 3 秒，切回遊戲，程式只送出一次 I，約 0.6 秒後擷取结果供人工確認並暫停。要測試關閉背包，需再次核對預覽並單獨啟動另一次測試。沒有盲目開關迴圈或自動重試。
- **暫停 / 取消** 或全域 **F8**：取消待執行動作。F8 註冊失敗會禁止輸入。啟用期間每 20 ms 檢查焦點，失焦會暫停；每次送鍵前另行核對焦點、程序與尺寸。重新執行必須明確按 Start / Resume。

實際遊戲按鍵效果仍未驗證。Win32 送鍵成功只表示系統接受請求，不代表遊戲已切換畫面；本階段必須人工檢查。視窗移動後請重新擷取及核對。其他 topmost 視窗可能污染螢幕擷取，必須移開。

## 辨識限制

- Windows OCR 沒有提供此介面的信心分數；低對比、小字、圖示上的白色數字、提示視窗及重疊 UI 可能漏讀。
- 只比對完整視覺標籤；忽略 OCR 字元間排版空白，但不替換標點、`+` 或其他字元。不使用模糊匹配，不推測材料替代。
- 數量只接受一般整數。缺失、`1萬` 等縮寫、多個候選、同一數字可能配給多個品名時均顯示「不明」，不猜成 1。
- 數量與名稱的空間配對仍為**候選**，需要人工核對。提示框中的白名單名稱也可能出現在預覽中，不代表它是一個可用堆疊。
- 只分析單張畫面；尚未完成自動捲動、跨畫面去重、所有卷軸堆疊總數或容量計算。辨識結果不能執行任何領取或任務操作。

## 本機資料與隱私

文字報告寫入 `%LOCALAPPDATA%\MabinogiSideHustle\reports`，包含預覽結果、暫停原因，以及任務數量尚未計算的說明。不自動保存擷取圖片；OCR 臨時圖片在處理結束後刪除。沒有上傳功能。

Excel 的作者中繼資料含個人姓名，因此 Git 只收錄遊戲資料 JSON。原 Excel、影片、截圖、`.local`、報告、設定、虛擬環境與打包產物均排除。載入 Excel 目前只影響本次執行；永久白名單編輯／匯入預覽／設定保存於下一階段實作。

## 開發與打包

需自行安裝 Python 3.12 x64；PowerShell 在專案根目錄執行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 -Python .venv/Scripts/python.exe
```

打包輸出：`dist/MabinogiAssistant/` 與含時間戳記的 ZIP。一般使用者只需解壓縮，不需要 Python 或 Excel。未在乾淨的第二台 Windows 電腦驗證。

唯讀診斷（不送出任何遊戲按鍵）：

```powershell
.\MabinogiAssistant.exe --diagnose diagnostic.json --reference 'C:\path\reference.png'
```

省略 `--reference` 可只檢查 Tk、預設白名單、視窗偵測與 F8 註冊。

## 模組與後續

- `app/capture.py`：視窗辨識、DPI、client area 與唯讀擷取。
- `app/recognition.py`、`scripts/ocr.ps1`：本機 OCR 與候選配對。
- `app/whitelist.py`：唯讀載入與欄位／數量驗證。
- `app/input_control.py`：單次 I、F8、失焦暫停。
- `app/planning.py`：明確禁止執行計畫，預留下一階段邊界。
- `app/gui.py`：桌面介面與本機報告。

下一步：改善完整背包／保管箱的品名與數量辨識、建立堆疊去重與白名單編輯，再做準備需求計算。背景輸入是獨立研究項目，**未驗證、未啟用**；沒有注入、讀寫遊戲記憶體或繞過保護機制。

完整需求見 [AGENTS.md](AGENTS.md)；驗證結果見 [VALIDATION.md](VALIDATION.md)。
