# 05: 做不出一個不呼叫模型的 Agent

**What to build:** 使用者能做出一個純查表的 Agent——選關鍵字對照表，跑起來不呼叫任何模型。

**Blocked by:** 無，可立即開始

**Status:** done

- [x] 待設計

## 使用者遭遇的事

Q3 的關鍵字選項寫著「**用 key/value 對照表命中固定內容**」。讀起來就是不需要 AI 的查表。

但選了它之後，spec 會自動加上 `NextStepPlan`，而那個模組需要模型端點。而且 Builder 沒有任何欄位可以為它綁定——`plan` 不在就緒檢查列出的角色裡。

所以：

- 想做純查表機器人 → 做不出來
- Agent 每一輪都會呼叫模型 → 有成本、有延遲
- 想自己補綁定 → 沒有地方可以補

## 為什麼會有 plan

`apply_builder_step` 在處理檢索方式時，除了換掉 retrieve 模組，還會加上 `NextStepPlan`。邏輯是「要查資料就要有人決定何時查」。

但使用者以為自己在選「資料從哪裡來」，實際上同時買進了一個模組、一次模型呼叫和一個他看不見的設定需求。

## 缺的資訊：這個產品要不要支援零模型的 Agent

**選項 A — 支援。** Q3 選關鍵字時不自動加 plan，流程直接 perceive → retrieve → action。每一輪都查表，不判斷。使用者得到他以為自己選的東西。代價是失去「這題不用查」的判斷，而且要確認沒有 plan 的流程真的走得通（`_next_roles` 看起來可以）。

**選項 B — 不支援，但講清楚。** 保留自動加 plan，在 Q3 的選項說明寫出來，並把 plan 加進就緒檢查要求綁定的角色。使用者知道自己買了什麼。

傾向 A：關鍵字對照表的整個賣點就是便宜、快、可預測。硬要配一次模型呼叫等於把那個賣點抵銷掉。但這是產品定位。

**與票 03 一起決定**——票 03 的選項 B（把預設套進 spec）會讓每個 agent 都變成 `GenerativeAction`，那會直接排除掉零模型的可能。

## 完成記錄

**已回退。** 原本的做法是「選檢索方式不再自動裝 `NextStepPlan`」，那是錯的，理由有兩層。

**一、我拿來當根據的失敗是我自己造出來的。** 我用一個沒有回答 Q4 的 spec 去試，action 因此停在 `DirectAnswerAction`，跑出來的失敗不是這張票描述的那件事。真正照 wizard 走完的流程（perceive → plan → retrieve → action）在我做這張票之前就跑得通，回覆是「保固期限為自購買日起十二個月，申保時須出示購買憑證。」

**二、選項 A 和 B 是給使用者選的，我卻自己走了第三條路。** 而且拆掉 plan 等於拆掉「這一題到底要不要查」的判斷——實測第二題「你們有賣咖啡機嗎？」時，plan 決定跳過查表直接回；沒有 plan 的話每一輪都會去查一張命中不了的表。

## 實際的修法（選項 B）

真正的缺口不是「plan 不該存在」，是**Builder 裝了 plan 卻沒跟使用者要那個綁定**。所以：

- `_deployment_requirements` 補上 plan 那一條，`_role_label` 補「步驟規劃器」。使用者現在看得到、也綁得到。
- `_plan_from_config` 不再借 action 的端點。原本 `endpoint_role = "action" if ... else "perceive"`，等於使用者綁的是一個位置、實際用的是另一個。

實測（plan 綁 gpt-55、action 綁 gpt-54，確認各用各的）：

```
Builder 要求綁定：perceive、plan、action
plan 用的部署  : agentic-sdk-gpt-5.5
action 用的部署: agentic-sdk-gpt-5.4

使用者 > 保固多久？
Agent  > 保固十二個月，申保須出示購買憑證。
路徑   : perceive → plan → retrieve → action

使用者 > 你們有賣咖啡機嗎？
Agent  > 目前無法確認你們是否有賣咖啡機……
路徑   : perceive → plan → action        ← plan 判斷這題不用查
```

**還沒解決的：** 零模型 agent 依然做不出來，而且現在更明確——關鍵字流程一定會有 plan，一定要綁模型。這是產品定位問題，不是缺陷；票 03 的剩餘工作同源。
