# huginn-flights

機票追蹤 Dashboard 線上版（複刻自同事的 ProjectHuginn 靜態快照）。

- `index.html`：自包含頁面（內嵌快照）
- `Huginn Dashboard.data.json`：sidecar 快照，頁面載入時比對 `HUGINN_GENERATED_AT`，較新就自動 reload
- `build_dashboard.py`：產生器（精簡版，輸入 `builder_input.json`）
- 更新：覆寫上面兩個檔 → `git commit` → `git push`，GitHub Pages 自動重建
