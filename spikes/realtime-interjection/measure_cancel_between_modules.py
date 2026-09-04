"""量核心取消延遲：Action 生成到一半打斷，多久真的停？狀態乾不乾淨？"""
import sys, threading, time
sys.path.insert(0,'playground'); sys.path.insert(0,'.')
from playground.services.workflow_spec import default_spec, apply_builder_step
from playground.services import runner_service as rs
from agentic_sdk.core.cancellation import CancellationToken

sp = default_spec()
for k,v in [("input_type","text"),("retrieve_policy","none"),("output_format","free_text"),("failure_policy","handoff")]:
    sp = apply_builder_step(sp,k,v)
sel = {"perceive":"gpt-54","action":"gpt-54","reflect":"gpt-54"}
wf = rs.build_workflow(sp, sel)

token = CancellationToken()
seen = []
wf_state_holder = {}

def on_delta(module, content, meta):
    seen.append((time.monotonic(), module, content))

wf.__dict__

import os
CANCEL_AFTER = float(os.environ.get("CANCEL_AFTER","1.5"))
def canceller():
    time.sleep(CANCEL_AFTER)
    t = time.monotonic()
    token.cancel("interjection", text="等一下")
    wf_state_holder["cancel_at"] = t
    print(f"  [{t-t0:5.2f}s] 送出取消訊號")

t0 = time.monotonic()
threading.Thread(target=canceller, daemon=True).start()
result = wf.run("請詳細說明如何挑選一雙適合久站工作的鞋子，包含鞋底、鞋墊、材質與尺寸，越詳細越好。",
                cancel=token,
                event_callback=lambda e: None)
t_end = time.monotonic()

print(f"  [{t_end-t0:5.2f}s] run() 返回")
if "cancel_at" in wf_state_holder:
    print(f"  取消 → 停止延遲: {(t_end - wf_state_holder['cancel_at'])*1000:.0f} ms")
print(f"  interrupted={result.interrupted}  aborted={result.aborted}")
print(f"  abort_reason={result.abort_reason}")
print(f"  payload={result.interrupt_payload}")
print(f"  已產生的 token 片段數: {len(seen)}")
print(f"  context entries: {[e.type.value if hasattr(e.type,'value') else e.type for e in result.entries]}")
