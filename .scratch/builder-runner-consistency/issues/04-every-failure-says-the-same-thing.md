# 04: 所有執行失敗都是同一句話

**What to build:** 執行失敗時，使用者看得出是哪裡缺了什麼，而不是每次都收到同一句「暫時無法產生回覆。」。

**Blocked by:** 無，可立即開始

**Status:** ready-for-agent

- [ ] 缺模型端點綁定時，訊息指出缺的是哪一個角色
- [ ] 語意檢索沒有可用知識來源時，訊息指出要上傳檔案
- [ ] 互動元件沒有 API 契約時，訊息指出要設定契約
- [ ] 其餘未預期的例外仍回通用訊息，但 `detail` 欄位帶上例外型別
- [ ] 每一種訊息各有一個測試

## Comments

`run_agent` 的最外層 except 把所有例外收斂成同一個回應：

```
final_message: "暫時無法產生回覆。"
error:         "暫時無法產生回覆。"
detail:        null
```

三種完全不同的原因產生同一個輸出：缺模型端點綁定、語意檢索沒上傳檔案、互動元件沒設 API 契約。使用者沒有任何線索可以自救。

`MissingEndpointCredentials` 有自己的 except 分支且訊息具體，但 `MissingEndpointBinding` 沒有，會落進通用分支——票 01 的失敗就是這樣被吞掉的。

**公平地說**，Builder 的就緒檢查對後兩種情況有擋（`builder_review_ready: false`）。擋不住的是缺綁定那一種，因為 Builder 根本不知道少了什麼（票 01）。所以這張票是把已經知道的原因說出來，不是替代票 01。

## 觸及範圍

`playground/services/runner_service.py` 的 `run_agent`，以及它的兩個串流版本。
