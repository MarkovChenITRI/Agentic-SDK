# 02: 選了「沒把握就停下來」，它從來不會停

**What to build:** 語意檢索一筆都沒命中時，「沒把握就停下來」真的會停。

**Blocked by:** 無，可立即開始

**Status:** ready-for-agent

- [ ] 三個 retrieve 模組用同一種方式回報「查到幾筆」
- [ ] `EvidenceCheckReflect` 讀那個統一的欄位，不再猜 metadata 的鍵名
- [ ] 三個 retrieve 模組各有一個測試：空結果時，reflect 真的判定 fail
- [ ] 現有那個手工捏 `ContextEntry` 的測試改成跑真實的 retrieve 模組

## 使用者遭遇的事

選了語意檢索之後，Q5 的「沒把握時先停止，不硬答」給的是 `EvidenceCheckReflect`。

它的工作是看檢索有沒有命中——一筆都沒命中就代表模型在沒有依據的情況下編答案，應該停下來。

**但它永遠回「通過」。**

```
EvidenceCheckReflect 讀的欄位       : hit_count
SemanticRetrieve 實際寫的欄位       : kb_hit_count, memory_hit_count
```

鍵名對不上，所以它拿不到數字，判斷不出「沒查到」，於是一律放行。

## 為什麼這個最陰險

其他問題會失敗、會報錯，使用者知道有事發生。這一個不會——它安靜地什麼都不做。使用者以為自己開了防幻覺的保護，實際上那道保護從來沒有生效過。

而且只有語意檢索會用到這個檢查器（關鍵字檢索配到的是 `ResponseCheckReflect`），所以**唯一會用到它的組合，正好是它失效的組合**。

## 目前的測試為什麼沒抓到

`tests/test_unit_documented_modules.py` 的測試自己手工建了一個 `ContextEntry(metadata={"hit_count": 0})` 餵給 reflect。它從來沒有跑過真實的 retrieve 模組，所以鍵名不一致這件事測不出來。
