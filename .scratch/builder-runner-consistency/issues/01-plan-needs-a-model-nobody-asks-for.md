# 01: Plan 模組需要模型，但沒有人請使用者綁定

**What to build:** 使用者在 Builder 裡選了關鍵字檢索、語意檢索，或把失敗策略設成重試之後，按下執行能得到回覆，而不是「暫時無法產生回覆。」。

**Blocked by:** 無，可立即開始

**Status:** needs-info

- [ ] 待設計

## Comments

原本是兩張票，因為是同一個根因的兩面，合併。分開修會只補到一半。

**這一面：Builder 不知道 plan 需要模型。**

`reachable_openai_roles` 正確回報 `plan` 需要模型端點。但把那個判斷轉成「使用者要填的項目」的 `_deployment_requirements` 只處理 perceive、retrieve、action、reflect——漏掉 plan。所以 Builder 的就緒檢查說「這個設定不需要任何模型」，使用者按下執行才發現不行。

**另一面：plan 只會去借 action 的端點。**

`_plan_from_config` 取端點的方式是 `"action" if "action" in reachable_roles else "perceive"`。action 只要「可達」就會被選中，不管它是不是需要模型的模組。

「失敗策略＝重試」這一格最能說明兩面必須一起修：Builder 明確要求綁定 reflect，使用者也綁了，但 plan 不認 reflect，只找 action，而 action 是 `DirectAnswerAction` 沒有綁定。**使用者照著 Builder 的每一條指示做完，還是失敗。**

## 實測證據（2026-09-02，模型接本機 Ollama）

| 設定 | Builder 要求綁定 | 實際結果 |
|---|---|---|
| keyword 檢索 + 預設 action | （無） | fallback |
| keyword 檢索 + free_text | `['action']` | completed |
| retry 失敗策略 + 預設 action | `['reflect']` | fallback |
| retry 失敗策略 + free_text | `['action', 'reflect']` | completed |

規律：**只要裝了 plan 而 action 又不需要模型，就失敗。**

## 缺的資訊：兩個修法要選一個

**選項 A — 把 plan 加進 `_deployment_requirements`。** Builder 會多問一個「規劃器要用哪個模型」。誠實，因為 plan 真的需要模型；代價是使用者多一個要填的欄位，而他甚至不知道自己裝了 plan（見票 03）。

**選項 B — 讓 plan 借得聰明一點。** 依序找 action、reflect、perceive 裡第一個有綁定的角色。不動 UI，但「規劃器用的是哪個模型」變成隱性行為。

傾向 A：plan 是一個會呼叫模型、會影響路由的真實模組，把它藏起來正是現在出問題的原因。但這會改 Builder 的畫面，是產品決定。

**相關：** 票 03 說明使用者為什麼不知道自己裝了 plan。兩張票的答案會互相影響，建議同一輪 grilling 一起談。

## 觸及範圍

`playground/services/model_endpoints.py` 的 `_deployment_requirements`、`playground/services/runner_service.py` 的 `_plan_from_config`。
