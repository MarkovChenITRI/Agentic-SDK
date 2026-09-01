# 03: 執行層改成接收 spec

**What to build:** 執行 agent 的入口直接接收 spec，不再從編譯出來的 Python 文字反推設定。對外行為完全不變——這張票只換資料來源，不換資料進來以後的用法。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 執行入口與兩個串流入口接收 spec，名稱改為以職責命名（`run_agent` 與對應的串流版本）
- [ ] 建構 Workflow 的函式從私有升為公開介面 `build_workflow(spec, deployment)`
- [ ] 四個語意檔案路徑參數收斂成單一參數，來源仍是同一個上傳識別碼
- [ ] `workflow_fingerprint` 移除，對話狀態不再需要 Python 文字
- [ ] 模型端點需求與工作流程摘要改為從 spec 取得
- [ ] 建立 `CONTEXT.md`，只定義 Agent 一個詞
- [ ] 七項尚未接通的 spec 設定仍然使用預設值，本票不改變它們
- [ ] HTTP 路由層的行為與 01 完成時完全相同，測試全綠

## Comments

`CONTEXT.md` 在這張票才建立，因為 Agent 這個詞是被這次改名釐清的。專案的 domain 文件規則要求詞彙延後建立，不要一次補齊。

Agent 的定義：一份 spec，加上執行它所需的環境設定。Workflow 是 SDK 裡執行它的那個東西。
