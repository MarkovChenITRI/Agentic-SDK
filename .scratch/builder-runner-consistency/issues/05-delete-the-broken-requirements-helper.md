# 05: 移除一呼叫就會炸的 `openai_requirements_from_spec`

**What to build:** 移除一個永遠不能用的函式，讓下一個想用它的人不會踩到。

**Blocked by:** 無，可立即開始

**Status:** ready-for-agent

- [ ] 移除 `openai_requirements_from_spec`
- [ ] 確認移除後沒有任何呼叫者（含前端 JavaScript）
- [ ] 測試全綠

## Comments

```
playground/services/model_endpoints.py:50
    return [asdict(r) for r in _openai_requirements(spec_to_config(spec))]
                                ^^^^^^^^^^^^^^^^^^^^ 這個名稱不存在
```

一呼叫就 `NameError`。全 repo 零個呼叫者，所以從來沒有人發現。

**這不是近期改動造成的。** 查過 git：本 effort 的起始 commit `67ee934` 版本就已經是壞的（當時叫 `openai_requirements_from_source`），只是被連帶改了名字。

真正需要這個資訊的地方用的是同檔案的 `_deployment_requirements`，那個是好的。所以直接刪，不必修。

要注意的是：**`_deployment_requirements` 正是票 01 漏掉 plan 的那個函式。** 兩張票會動到同一個檔案，但不衝突——這張票只刪東西。
