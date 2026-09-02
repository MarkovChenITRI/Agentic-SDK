# 05: 草稿只保存 spec

**What to build:** 編輯中的草稿只保存 spec，Python 文字改為需要時當場計算。這會消除一份會過期的副本，並修好一個現在就在發生的 bug：從其中一條載入路由取得的 agent，執行時用的是過期設定。

**Blocked by:** 04

**Status:** done

- [x] 草稿狀態不再保存 Python 文字
- [x] 需要 Python 文字的兩個地方（原始碼預覽、存回 AI Hub）在當下計算
- [x] 從 AI Hub 載入 agent 之後，執行時使用的設定與該 agent 的 spec 一致，不論走哪一條載入路由
- [x] 新增一個測試，涵蓋原本會產生過期設定的那條載入路由

## Comments

這張票可以實際示範：載入一個 agent，執行，看到的行為與 spec 相符。

修好的 bug 是兩條路由行為不一致——其中一條在載入後重新編譯 Python 文字，另一條沒有。因為執行層讀的是那份文字，沒重新編譯的那條就會執行過期設定。03 之後執行層改讀 spec，這張票再把過期副本本身拿掉。

## 完成記錄

Session 不再保存 `python_source`，18 個寫入點全部移除。需要 Python 文字的兩個地方在需要時計算：原始碼預覽（`routes/source.py`）與存回 AI Hub（`routes/aihub.py` 的存檔路由本來就已經是當下計算）。

**修掉一個在移除過程中造成的新 bug：** `deep_link._clear_loaded_agent_state()` 原本 pop 掉 `python_source`，也就是切換到不同 agent 時清掉舊草稿。我拿掉那一行卻沒改成 pop `workflow_spec`，結果舊草稿會殘留。`test_legacy_aihub_deep_link_does_not_reuse_stale_source_for_different_agent` 抓到了。

**保留 `deep_link` 的 setdefault 語意：** 沒有 agent_id 的 deep link 原本用 `setdefault`，只在 session 沒有草稿時才種。我一度改成 `reset_spec()`（一定重設），會清掉使用者既有的草稿，已改回 `session.setdefault("workflow_spec", default_spec())`。

**測試假資料的一致更正：** 多處假 AI Hub 回應只給 `python_source`，而 session 現在只認 spec。這些假資料補上了 `workflow_spec`，與生產環境實際回傳的內容一致。同時有幾個斷言原本是「session 存的就是 AI Hub 回的原始字串」，這在本票之後不再成立，改成比對 spec 的內容。
