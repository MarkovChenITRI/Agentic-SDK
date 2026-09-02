# 08: 把草稿狀態收進單一 store

**What to build:** 編輯中的草稿散在多個 session 欄位、由多處寫入，沒有任何介面可以違反，所以也沒有東西攔得住違反。收進單一 store。

**Blocked by:** 05

**Status:** needs-info

- [ ] 待設計

## Comments

**缺的資訊：** 這張票需要自己的 `/grilling`。

**範圍已經縮小：** 原始的架構報告點出 21 個欄位、18 個寫入點，其中最危險的是那份會過期的 Python 文字副本。05 已經把它拿掉，所以這張票剩下的是其餘欄位。設計之前應該重新盤點一次，數字會跟原報告不同。

## 票 05 之後重新盤點

原始架構報告說 21 個欄位、18 個寫入點，其中最危險的是會過期的 `python_source` 副本。票 05 已經把它整個拿掉。

本票剩下的具體形狀，由票 04–06 的 code review 量出來：**`session["workflow_spec"]` 仍被 22 處直接觸碰**（`routes/runner.py` 9、`routes/builder.py` 3、`routes/aihub.py` 3、`services/aihub_bridge.py` 3、`routes/entry.py` 2、`services/deep_link.py` 2）。`session_spec.py` 提供 `current_spec()` / `store_spec()` / `reset_spec()`，但它們被繞過。

一個已知的根因：`current_spec()` 找不到草稿時會自動種入預設值，所以它回答不了「這個 session 有沒有草稿」。多處路由因此改用 `session.get("workflow_spec")` 當閘門。設計時要決定這個存取器缺不缺一個 `has_spec()`。
