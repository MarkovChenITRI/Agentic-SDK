# 01: README 教使用者指定版本標籤

**What to build:** README 的安裝說明改成教使用者指定版本標籤，讓他們在破壞性變更抵達之前，先有停留在可用版本的方法。

**Blocked by:** 無，可立即開始

**Status:** ready-for-agent

- [ ] 安裝指令改為指定標籤的形式，並保留不指定標籤的形式作為對照
- [ ] 說明不指定標籤會取得 main 分支的最新內容，因此不受版本保護
- [ ] README 敘述的 Python 版本下限與 `pyproject.toml` 的 `requires-python` 一致

## Comments

現在 README 教的安裝指令不指定標籤，所以使用者永遠拿到 main 的最新內容，沒有任何辦法停在舊行為上。破壞抵達時他們沒有退路。這張票要先落地，保護才會早於破壞。

第三項驗收條件順帶修掉一個既有的矛盾：`requires-python` 之前從 3.10 提高到 3.11，README 沒有跟著改。

這張票本身不破壞任何東西，只是文件。
