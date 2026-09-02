# 03: Builder 說可以開始使用，畫面上的答案卻不是我的 Agent

**What to build:** Builder 畫面上顯示的每一個答案，都是這個 Agent 實際的設定。

**Blocked by:** 無，可立即開始

**Status:** done

- [x] 待設計

## 使用者遭遇的事

使用者只回答他在意的那一題——檢索方式選關鍵字、填好對照內容——其餘留著預設。畫面顯示：

```
Q1 記憶類型      完成 ✓   即時問答
Q2 理解輸入      完成 ✓   直接傳遞文字
Q3 查資料        完成 ✓   關鍵字查詢
Q4 呈現方式      完成 ✓   純文字回覆          ← spec 裡是 DirectAnswerAction
Q5 沒把握時      完成 ✓   先停下來，交給人確認   ← spec 裡沒有 reflect 模組

可以開始使用：True
需要綁定的模型：（不需要）
```

五題全部打勾，其中兩題的答案是編出來的。按下執行：

```
Agent > 暫時無法產生回覆。
```

## 原因

就緒檢查對沒有回答過的題目，會退回「第一個可用選項」當作答案顯示，並標記完成。但 spec 沒有跟著改——`apply_builder_step` 從來沒有為那些題目跑過。

所以畫面說 Q4 是「純文字回覆」（`GenerativeAction`），spec 裡卻是 `DirectAnswerAction`；畫面說 Q5 選了「停下來」，spec 裡連 reflect 都沒有。

Builder 也因此算不出需要綁定模型（它是照 spec 算的），於是說「不需要」，而執行時 `NextStepPlan` 拿不到端點就倒。

## 缺的資訊：兩種對齊方式，各有代價

**選項 A — 沒回答的題目就顯示成沒回答。** 使用者必須逐題確認才會 ready。畫面誠實，但多了幾次點擊，而且「我只想改一件事」變得麻煩。

**選項 B — 把預設答案真的套進 spec。** 畫面不變，ready 也維持 True，而且 spec 與畫面一致。但這代表每個 agent 一開始就是 `GenerativeAction`——**會和票 05「做不出零模型的 agent」直接衝突**，因為預設就把模型需求裝進去了。

兩個選項的差別是「Builder 是一份要填完的表單，還是一組可以只改一格的預設值」。這是產品定位，不是實作細節。

**與票 05 一起決定。**

## 完成記錄

**編造答案的地方不是退回邏輯，是有損的對應。** `spec_to_form_state` 在 spec 是 `DirectAnswerAction` 時回報 Q4 =「純文字回覆」，在沒有 reflect 時回報 Q5 =「先停下來」。兩者都是 spec 表達不了的狀態，卻硬給了一個答案。

而且 `default_spec()` 自己就矛盾：action 是 `DirectAnswerAction`，params 裡卻寫著 `output_format: "free_text"`。

修法：spec 表達不了的狀態就回報空值，畫面顯示「尚未選擇」。預設的 `output_format` 改成 `None`。

**Q2 維持顯示答案是對的，不是漏改。** 它的預設 `PassThroughPerceive` 在 Q2 有對應的選項，而 agent 真的那樣做——顯示它是誠實的。編造的只有 Q4 和 Q5。

**沒有做的事：** 沒有為 Q4 加一個對應 `DirectAnswerAction` 的選項。那會改動產品的問題集，而我看不到 UI 沒辦法驗證渲染結果。現況是誠實的（說「尚未選擇」），但使用者仍然沒辦法明確選擇「直接回傳查到的內容」。這是剩下的工作。
