# 用 MatrAIx 的角色設定產生不同風格的回覆

一般文字模型可以生成完整回覆，卻不會自然帶入不同使用者的觀點、偏好或表達方式。把角色設定直接混進提示文字看似簡單，但角色資料從哪裡來、是否能使用、是否影響事實陳述，以及相同條件能否重現，往往在第一個原型之後才浮現。

我們將 MatrAIx Persona 1M 當成版本化的角色設定資料，而不是推論模型。部署在 A100 上的文字模型仍負責生成；Agentic SDK 的 Action 只從已核准的資料中選擇角色設定，再將它連同使用者問題與查到的資料放進提示內容。這個分工讓「使用哪個角色」成為可追查的設定，而不是散落在程式裡的一段文字。

本文會說明如何保留角色化回覆的可讀性，同時不讓角色設定凌駕系統安全規則或資料來源中的事實。

## 先把角色設定和模型分開

MatrAIx Persona 1M 是資料集，不是推論模型，也不是模型卡。文字模型卡描述部署的模型、端點與執行環境；角色資料則描述回覆需要採用的觀點、偏好與表達方式。兩者分開版本化，才能在更新資料時不誤以為模型行為已經改變。

```text
使用者問題 -> 選擇已核准的角色設定 -> Persona Action
資料來源與檢索結果 ---------------------------> Persona Action
Persona Action -> AI Hub 文字模型服務 -> 角色化回覆
    -> Reflect 檢查安全與事實
```

## 用 MatrAIx 的角色設定（Persona）資料決定回覆方向

Persona 1M 作為文字模型卡旁的版本化資料資產。部署資料保存資料集版本、授權條件、可用欄位清單、角色識別碼與資料來源分類。這些欄位讓同一個工作流程在不同環境中可以選到相同的角色設定，也讓審查者能知道回覆風格來自哪一版資料。

敏感欄位和模仿真實人物的設定不得使用；篩選與選用規則是整合交付的一部分。

## 讓加速文字模型依角色設定產生回覆

部署在 A100 上的文字模型，以 `api_key`、`base_url` 與 `model` 提供回覆。角色設定只改變受控的提示內容，不改變模型權重，也不改寫從資料來源找到的事實。

模型和角色資料的部署設定分別保存，並在執行時合併：

```python title="matraix_deployment.py"
deployment = {
    "model": {"base_url": chat_url, "api_key": api_key, "model": chat_model},
    "persona": {"revision": "persona-1m-2026-08", "allowlist": "support-v1"},
}
```

這個邊界很重要。更換模型卡時，角色資料的選擇規則不會跟著改；更新角色資料時，也不會悄悄改動文字模型的部署版本。

## 讓 Action 用角色設定引導模型回覆

`MatrAIxPersonaAction` 會合併使用者任務、找到的資料與已核准的角色設定。系統安全規則與資料事實優先，角色設定只影響語氣與偏好。這個模組獨立實作，不依賴 `GenerativeAction` 的內部訊息組裝，因為角色資料的選擇與可追查性本身就是公開行為的一部分。

```python title="matraix_action.py"
class MatrAIxPersonaAction:
    name = "action"

    def __init__(self, client, personas) -> None:
        self.client = client
        self.personas = personas

    def __call__(self, state):
        persona = self.personas.select(
            persona_id=state.lookup("persona_id"),
            allowlist="support-v1",
        )
        response = self.client.complete(
            system=build_system_prompt(persona),
            user=state.latest_user_message(),
            evidence=state.lookup("latest_retrieved_content"),
        )
        return {
            "payload": {"persona_revision": persona.revision, "content": response.content},
            "next_module": "reflect",
        }
```

`build_system_prompt()` 只接收已篩選的欄位。敏感欄位、可能用於模仿真實人物的描述與未授權資料在進入模型之前就被排除，而不是等模型產生回覆後才嘗試清除。

## 匯出可重現角色設定的部署設定

部署設定包含文字模型卡版本、A100 端點、角色資料版本、欄位結構、可用欄位清單與選擇種子值，並直接附加到 `Workflow`：

```python title="app.py"
workflow = Workflow(
    workflow_name="角色化客服回覆",
    retrieve=knowledge_retrieve,
    action=MatrAIxPersonaAction(client, personas),
    reflect=persona_reflect,
)
```

選擇種子值和資料版本會與回覆記錄一起保存。這使得開發者可以回到某次回覆，重新取得相同角色設定、相同模型組態與相同檢索資料，檢查差異究竟出在哪一層。

## 用版本資料與回覆記錄確認角色設定是否生效

我們使用同一組客服問題，分別套用不同的已核准角色設定。驗證時檢查授權測試資料、模型服務輸出、重複選擇的結果、特徵是否正確呈現或排除、事實是否維持一致，以及禁止欄位和不確定回答是否符合規則。

最重要的兩個測試是：角色語氣變化時，產品條款與檢索到的事實不得改寫；指定被排除的欄位時，該欄位不得出現在模型提示內容或回覆記錄。前者確保角色不會取代知識，後者確保資料治理在模型呼叫之前就生效。

## 讓同一個加速端點支援不同角色的回覆

完成整合後，開發者可用同一個加速文字模型產生可重現的角色化回覆。AI Hub 管理角色資料資產，SDK 則透過 `PersonaProvider` 與部署設定載入工具，讓這些資料以一致方式進入不同工作流程。

## 我們學到的事

角色化不是替回覆加上一層文案，而是一個資料選擇與安全約束問題。當角色資料、模型卡、檢索證據和回覆記錄都有版本時，團隊才有能力在維持事實正確的前提下，持續調整不同使用者需要的表達方式。

## 參考資料

- [MatrAIx 論文](https://arxiv.org/abs/2608.04205)
- [MatrAIx Persona 1M 資料集](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M)
- [回覆與動作模組](../modules/action-modules.md)
- [安全控制模組](../modules/reflect-modules.md)