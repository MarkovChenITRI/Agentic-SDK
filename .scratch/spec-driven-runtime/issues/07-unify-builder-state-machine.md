# 07: 統一 Builder 的狀態機

**What to build:** Builder 把使用者的每個選擇轉成設定變更，這個轉換目前有兩套實作——一套改 spec，一套改 Python 文字——而且兩套已經不一致。統一成一套。

**Blocked by:** 04

**Status:** done

- [x] 重複的狀態機隨票 04 消失
- [x] 跨模組的 29 個私有名稱改成公開名稱

## Comments

**缺的資訊：** 這張票需要自己的 `/grilling`。要決定的至少有三件事：統一之後的介面形狀、兩套實作行為不同時哪一套是對的、以及已知的差異要往哪一邊收斂。

**已知事實（票 01 期間更正）：** 原本記載「改 Python 文字那一套處理六種 failure policy，改 spec 那一套只處理兩種」，並暗示 spec 那一套有缺陷。方向相反。Builder 介面只提供兩個選項：`retry` 與 `handoff`。另外四個（`clarify`、`re_retrieve`、`safe_answer`、`escalate`）只存在於程式碼文字那一套，使用者到不了，是死分支。這反而支持票 04 的刪除。

兩個模組之間沒有接縫——其中一個從另一個匯入的名稱有 26 個是私有的。這一項未變。

04 完成之後這張票的範圍會縮小，因為程式碼文字那條路徑屆時已經消失。

## 完成記錄

**票 04 解決了重複，不是靠統一，是靠刪除。** 兩套狀態機裡以程式碼文字為輸入的那一套（`build_python_source_from_builder_choice`、`get_builder_form_state`）已經沒有呼叫者，隨編譯文字讀取路徑一起移除。現在只剩 `apply_builder_step` 與 `spec_to_form_state` 一套。

**剩下的另一半是缺接縫，本票處理掉了。** `workflow_spec.py` 從 `source_builder.py` 匯入 31 個名稱，其中 29 個以底線開頭。那些名稱就是這兩個模組之間實際的介面，底線只是在宣稱一件不成立的事——它們不是私有的。全部改成公開名稱，邊界不再說謊，之後有人改動它們時也知道有跨模組的呼叫者。

`routes/builder.py` 裡一個函式內的私有匯入（`_string_items_from_lines`）與 `routes/runner.py` 的 `_DEFAULT_RUNNER_DESCRIPTION` 一併處理。

**沒有做的事：** 沒有把兩個模組合併。它們合起來會是 1500 行，比現在難讀，而且刪掉檔案邊界不會讓任何複雜度消失——只是換個地方放。真正的問題是邊界在說謊，那個已經修好了。
