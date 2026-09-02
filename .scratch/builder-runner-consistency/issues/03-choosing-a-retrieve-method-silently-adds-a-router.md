# 03: 選檢索方式會連帶裝上一個路由模組

**What to build:** 使用者選檢索方式時，知道自己還連帶得到了什麼。

**Blocked by:** 無，可立即開始

**Status:** needs-info

- [ ] 待設計

## Comments

在 Builder 選「關鍵字檢索」時，`apply_builder_step` 除了換掉 retrieve 模組，還會加上 `NextStepPlan`：

```
選 retrieve_policy = keyword 之後，spec 多出：
    plan: {"module": "NextStepPlan", "params": {"strategy": "RouteBySupport", ...}}
```

邏輯上說得通——要檢索就要有人決定何時檢索。問題是使用者以為自己在選「資料從哪裡來」，實際上同時引入了一個會呼叫模型、會影響路由的模組，而 Builder 沒有任何地方提到這件事。

**這是票 01 會被踩到的原因。** 使用者不知道自己裝了 plan，自然不會想到要為它綁模型端點。

逐步 diff 的實測結果（其他選項都只動它該動的）：

| 選擇 | 實際變動 |
|---|---|
| `input_type=text_image` | 只有 perceive |
| **`retrieve_policy=keyword`** | **retrieve，加上 plan** |
| `output_format=free_text` | 只有 action |
| `failure_policy=handoff` | 只有 reflect |

## 缺的資訊：說明它，還是拆開它

**選項 A — 說明它。** Builder 在檢索選項旁講清楚會連帶啟用規劃器，就緒檢查也把 plan 的模型需求列出來（與票 01 的選項 A 合流）。改動小，但保留了「一個選擇改兩件事」的耦合。

**選項 B — 拆成兩個問題。** 檢索方式歸檢索方式，要不要規劃器另外問。使用者對自己的 workflow 有完整的認知，代價是 Builder 多一個步驟，而且沒有規劃器的檢索流程要確認真的可行（`_next_roles` 在沒有 plan_strategy 時 perceive 直接接 retrieve，看起來可行）。

傾向 A，因為「選了檢索就需要規劃」在多數情境下是對的預設，讓使用者自己組容易組出不會檢索的 agent。但這是產品決定。

**與票 01 一起談。** 兩張票的答案互相決定。
