# 04: 刪掉編譯文字的讀取路徑

**What to build:** 移除從 Python 文字反推設定的整條路徑，以及所有依 spec 版本分流的判斷。這一步是 contract：確定沒有呼叫者之後才刪。

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] 依 spec 版本分流的判斷全部移除
- [ ] 用語法解析取得設定的模組與其全部輔助函式移除
- [ ] Builder 從程式碼文字推導 spec 的相容路徑移除
- [ ] 以程式碼文字為輸入的 Builder 狀態轉換函式移除
- [ ] 編譯 spec 成 Python 文字的函式保留
- [ ] 測試全綠，行為不變

## Comments

編譯函式一定要留。AI Hub 的兩支公開查詢都要求 `playground_generated_source` 非空，欄位空掉的話 agent 會從公開列表消失，公開載入回 404。

被 02 擋住的原因是：那些版本分流的判斷是唯一擋在舊 agent 前面的東西。查證沒完成就刪，等於賭生產資料裡沒有舊資料。
