# 02: 每個訪客都重新下載整包知識庫

**What to build:** 同一個 Agent 的知識庫在伺服器上只留一份，不要每個 session 一份。

**Blocked by:** 無，可立即開始

**Status:** ready-for-agent

- [ ] 還原後的目錄以 agent_id 與 bundle 版本命名，不用隨機 upload_id
- [ ] 已經有同版本的解壓結果就跳過下載
- [ ] 有清理機制，或確認 App Service 的磁碟會自己回收

## 為什麼現在才變成問題

票 01 之前，還原 bundle 只有**擁有者**會做，一個人開自己的 Agent 一次。票 01 之後，**每個匿名訪客進畫廊都會觸發**。

Timothy 的 bundle 是 67 MB（13 份 PDF）。`bundle_store.restore_agent_bundle_zip` 每次都呼叫 `new_upload_id()`，解壓到 `/tmp/agentic-sdk-playground/<隨機 id>/`。整個檔案裡找不到任何清理邏輯，只有換檔名時清 vectorstore 那一處。

所以一百個人點過 Timothy，就是一百次 67 MB 下載，加一百份解壓副本躺在 App Service 的磁碟上。

## 還沒查清楚的

**App Service 的 `/tmp` 會不會自己回收。** 如果重啟就清空，風險只是頻寬和延遲，不是磁碟塞爆。這件事沒查，不該假設。

**下載速度。** 本機量到 47 KB/s，但那是台灣連 Azure 的公網速度；App Service 和儲存體同在 southeastasia，實際會快得多。`bundle_store` 的傳輸逾時是 300 秒。擁有者路徑本來就在做同樣的下載且可用，所以線上速度應該可接受——但匿名路徑的**次數**是新的。

## 建議做法

還原目錄改用 agent_id 加 bundle 的 ETag 命名。同一版已經在磁碟上就直接用，不下載也不解壓。ETag 從 blob 的回應標頭取得，Agent 更新文件後自然換一個目錄。
