# 貢獻指南

本專案接受工業技術研究院各單位與外部團隊的貢獻。這一頁只放送件前必須同意的
授權條件與必跑的檢查；逐步的加入流程另有一份導引。

**第一次貢獻請先讀
[加入貢獻的逐步導引](https://r300-ai.github.io/Agentic-SDK/contributing/)。**
新單位從
[開一張加入申請](https://github.com/R300-AI/Agentic-SDK/issues/new/choose)
開始，歸屬與審查權定好之後再送程式碼。

## 貢獻的授權

送出 Pull Request 即表示同意下列兩項：

1. 貢獻者擁有該修改的著作權，或已取得權利人授權提交。
2. 貢獻者授予工業技術研究院不可撤回的權利，得以任何條款再授權該修改，
   包含技術移轉的商業授權在內。

第二項是必要條件。本專案以 PolyForm Noncommercial 釋出，商業使用另循工研院技轉，
技轉標的必須涵蓋全部原始碼，其中任何一段不可再授權都會使整包無法移轉。

## 提交尾標的寫法

一次提交有多位作者時，尾標一人一行，放在提交訊息最末，前面空一行。

```
Co-authored-by: 姓名 <信箱>
```

信箱要與該人 GitHub 帳號上的信箱一致，圖表才算得到他。單位配發的信箱優於
GitHub 的 noreply 位址：該次提交的隸屬單位因而留在歷史裡，日後人事異動也不影響。

## 送出之前

| 項目 | 指令 |
| --- | --- |
| 全套測試 | `python -m pytest` |
| 文件站建置 | `mkdocs build --strict` |
| 依賴清單 | `python scripts/generate_third_party_notices.py` |
| 歸屬路徑 | `python scripts/verify_ownership_paths.py` |

後兩項在 CI 也會跑，本機先跑過可省一次來回。哪些紀錄需要在這次 PR 更新，
見 Pull Request 模板的檢查清單與導引裡的紀錄分工表。
