# 畫廊分享出去的 Agent 拿得到自己的文件

## 這件事要解決什麼

AI Hub 的畫廊邀請匿名訪客「試用別人的 workflow」。但語意檢索的 Agent 沒有參考文件就試不了——十五個已儲存的 Agent 裡有八個是語意檢索。

匿名路徑載入設定之後就結束，從來沒有去取知識庫。這不是壞掉，是設計沒涵蓋這個情境：`connection-and-responsibility.md` 把唯讀路徑定義成只載入公開 config，`playground-file-save.md` 的 bundle 存取兩條流程都寫「AI Hub 驗證使用者權限後」。

## 使用者故事

**US1** — 我在畫廊點進別人的 Agent，問它文件裡才有的問題，它答得出來。

**US2** — 那個 Agent 的文件如果真的取不到，它老實告訴我，而不是編一個答案，也不是給我一個錯誤頁。

**US3** — 我是維護者，我看得出文件為什麼沒載入，不用重跑一遍探測。

## 邊界

**不新增端點。** `GET /api/playground/agents/{id}/bundle/load` 早就存在，卡的是它一律要求帳密。改的是權限判斷。

**公開判斷沿用現成的。** `read_public_playground_agent` 的 SQL 已經在檢查 `gallery_domain IS NOT NULL AND <> ''`，那就是「有沒有上架 Gallery」。不發明新規則。

**宣稱身分就要驗證。** 只有完全沒有宣稱身分的請求走公開分支。帳密錯誤仍然 401。

**兩個 repo。** AI Hub 那半在 `~/Documents/GitHub/ai-hub-webui`（`R300-AI/ai-hub-webui`），Playground 那半在本 repo。

## 安全性決定

已上架 Gallery 的 Agent，其參考文件可經 API 取得（需帶 Playground 的 Origin）。這是 POC 站的既定取捨：網頁上沒有下載入口即可，後台 API 開著可接受。
