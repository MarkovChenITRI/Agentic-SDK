# 貢獻指南

歡迎工業技術研究院各單位與外部團隊送出 Pull Request，送出前請先讀完這一頁。

## 目前的貢獻者

| GitHub 帳號 | 單位 | 貢獻範疇 |
| --- | --- | --- |
| [@MarkovChenITRI](https://github.com/MarkovChenITRI) | 電光所 異質整合晶片系統組 | 工作流程核心、五類模組、Playground、文件網站 |
| [@MarkovChenITRI](https://github.com/MarkovChenITRI) | 機械所 機器人技術組 | 即時語音互動 |
| [@Terrykuo20031222](https://github.com/Terrykuo20031222) | 未定 | 合併分支 |

一位貢獻者代表兩個單位時分列兩行，換單位時新增一行而不改寫舊行，那段期間的貢獻歸屬於當時的單位。

## 送出 Pull Request

提交訊息末尾加上 `Co-authored-by: 姓名 <信箱>`，GitHub 的貢獻者圖表依此累積，信箱要與該帳號上的信箱一致；
單位配發的信箱優於 GitHub 的 noreply 位址，該次提交的隸屬單位因而留在歷史裡。第一次貢獻時一併把自己加進上面那張表。

## 送出之前

| 項目 | 指令 |
| --- | --- |
| 全套測試 | `python -m pytest` |
| 文件站建置 | `mkdocs build --strict` |
