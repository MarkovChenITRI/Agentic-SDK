# 技術 Blog

AI Hub 將模型、執行環境與硬體條件整理成模型卡，並將部署後的模型服務以 OpenAI 相容介面提供給應用程式使用。Agentic SDK 則讓應用程式把這些服務放進工作流程，安排輸入理解、資料查找、回覆、工具操作與安全檢查。

本區記錄三個相互獨立的模組整合案例。每篇文章都從實際遇到的開發問題開始，接著說明外部服務與單一 SDK 模組如何分工，並提供核心程式與驗證情境。三種整合可以分別採用；若要放進同一條 workflow，應用程式仍要明確決定執行順序與資料是否相容，本文不預設它們會自動串接。

## 文章

- [以 Letta 為工作流程建立長期記憶](reflect-letta.md)：由 Reflect 從完成的 Action 結果中判定可長期沿用的資訊，再交由應用程式 adapter 寫入 Letta memory block。
- [以 Fara 為工作流程建立可檢視的畫面操作提案](action-fara.md)：由 Action 將畫面與使用者任務轉成可檢視的 Fara 操作提案。
- [以 MatrAIx Persona 1M 盤查工作流程回覆的一致性](action-matraix.md)：以 Persona 1M 的已核准維度建立評估情境，盤查同一個 Action 是否維持必要事實。

## 選擇整合方式

| 適合解決的問題 | 外部能力 | SDK 所屬模組 | 文章輸入 | 文章輸出 | 本文不處理的責任 |
| --- | --- | --- | --- | --- | --- |
| 想留下跨回合仍有效的偏好與限制 | Letta 長期資訊保存 | Reflect | 完成的 Action 結果與本輪對話 | 保存狀態、候選識別與 reflection entry | 查回資料、排序候選與將內容送入下一輪 Action |
| 想將畫面理解模型的建議交給人或系統檢視 | Fara 視覺操作提案 | Action | 使用者任務 | 可檢視的結構化操作提案 | 瀏覽器控制、操作執行、授權與人工確認 |
| 想在不同模擬使用者情境下盤查回覆是否維持事實 | MatrAIx Persona 1M 評估 | Action | 已核准的 persona 維度與固定問題集 | Action 回覆與 persona 分組評估紀錄 | 資料集選用、欄位映射、授權確認與完整語意評估 |

讀者先依要解決的問題選擇文章，再以各篇的 adapter、runner 或設定物件接上外部服務。這能避免把共享 workflow state 誤認為每篇文章都必須實作整條 workflow。

## 成果總結與展望

三個案例完成後，Agentic SDK 的使用者可用一致的模組協定（`name`、`__call__(WorkflowState)` 與 `ModuleOutput`）接入三種外部能力：由 Reflect 判定並記錄 Letta memory block 寫入、由 Action 產生畫面操作提案、以及由 Action 產生可供 Persona 1M 情境評估的回覆。各模組家族仍有自己的輸入與輸出欄位，並不是可互換的同一個介面；外部 client 與資料來源則被限制在各自的 adapter 或設定邊界。

後續若要逐步原生化，應以可選整合方式加入各模組家族：Letta 維持為 Reflect adapter、Fara 維持為 Action runner、MatrAIx 維持為 Action 評估案例與結果比較 helper。三者都不應新增 workflow 階段或吸收其他模組的工作。這讓 SDK 能增加整合便利性，同時保留應用程式對服務認證、部署端點與資料選用的控制權。