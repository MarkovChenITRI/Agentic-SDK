# 03: 執行層改成接收 spec

**What to build:** 執行 agent 的入口直接接收 spec，不再從編譯出來的 Python 文字反推設定。對外行為完全不變——這張票只換資料來源，不換資料進來以後的用法。

**Blocked by:** 01

**Status:** done

- [x] 執行入口與兩個串流入口接收 spec，名稱改為以職責命名（`run_agent` 與對應的串流版本）
- [x] 建構 Workflow 的函式從私有升為公開介面 `build_workflow(spec, deployment)`
- [x] 四個語意檔案路徑參數收斂成單一參數，來源仍是同一個上傳識別碼
- [x] `workflow_fingerprint` 移除，對話狀態不再需要 Python 文字
- [x] 模型端點需求與工作流程摘要改為從 spec 取得
- [x] 建立 `CONTEXT.md`，只定義 Agent 一個詞
- [x] 七項尚未接通的 spec 設定仍然使用預設值，本票不改變它們
- [x] HTTP 路由層的行為與 01 完成時完全相同，測試全綠

## Comments

`CONTEXT.md` 在這張票才建立，因為 Agent 這個詞是被這次改名釐清的。專案的 domain 文件規則要求詞彙延後建立，不要一次補齊。

Agent 的定義：一份 spec，加上執行它所需的環境設定。Workflow 是 SDK 裡執行它的那個東西。

## 實作期間的三項發現

**一、AC7 只達成四項，不是七項。** 原本寫「七項尚未接通的設定仍然使用預設值」。實際上 `spec_to_config` 直接讀整份 spec，所以其中三項會隨本票一起生效：`perceive.importance`、`retrieve.fallback`、`retrieve.top_k`。要壓住它們，得寫程式碼刻意忽略使用者的設定，而票 06 又會把那段刪掉。

這三項生效的方向是對的——它們都是 Builder 已經收集、卻被編譯文字丟掉的值。剩下四項（`gates`、`entry_module`、`memory.kind`、`output_format`）確實仍未接通，留給票 06。

新增的 `test_spec_path_and_compiled_source_path_agree_except_on_dropped_settings` 把這個界線釘住：兩條 config 路徑對七種真實 Builder 操作序列的結果，只允許在這三個欄位上不同。

**二、修掉一個本票造成的退步。** `spec_to_config` 原本只讀 `retrieve.params.description`，而編譯路徑會從 `search_goal` 推導出描述再寫進 `NextStepPlan`。結果是使用者設定的檢索目標在新路徑上遺失。

修法要精確：只在推導結果**不是**兩個預設描述之一時才採用。因為 `NextStepPlan` 把這個值的有無當成「這個 agent 有檢索來源」，並據此啟用那份硬編碼的零售關鍵字覆寫。無條件推導會讓該覆寫對所有帶 plan 的 agent 生效——正是票 `sdk-breaking-change/02` 要處理的陷阱。

**三、三條路由曾經全毀，測試沒抓到。** `/run/name`、`/run/description`、`/run/metadata` 的 legacy 分支仍呼叫已從 import 移除的函式，會丟 `NameError` 回 500。這三條路由原本沒有任何測試涵蓋。修法是改用 `current_spec()`，版本分叉自然消失；同時補上 `test_runner_metadata_routes_answer_for_a_session_that_only_has_python_source`。

**範圍說明：** 本票新增 `playground/services/session_spec.py`，並讓 `routes/builder.py` 改用它，因為原本 `_current_spec`/`_config_to_spec` 只存在於 builder 路由裡，而 Runner 也需要取得 spec。這不是票 08 的工作——它只搬動既有的一份，沒有引入新抽象。`_spec_from_legacy_source` 是 `_config_from_source` 的第二個呼叫點，票 04 要一併移除。
