"""在 Action 生成到一半時打斷——這才是 StreamCancelled 那條路徑。"""
import sys, threading, time, os
sys.path.insert(0,'playground'); sys.path.insert(0,'.')
from playground.services.workflow_spec import default_spec, apply_builder_step
from playground.services import runner_service as rs
from agentic_sdk.core.cancellation import CancellationToken

sp = default_spec()
for k,v in [("input_type","text"),("retrieve_policy","none"),("output_format","free_text"),("failure_policy","handoff")]:
    sp = apply_builder_step(sp,k,v)
wf = rs.build_workflow(sp, {"perceive":"gpt-54","action":"gpt-54","reflect":"gpt-54"})

token = CancellationToken()
CANCEL_AT = float(os.environ.get("CANCEL_AT","10"))
marks = {}
t0 = time.monotonic()

def canceller():
    time.sleep(CANCEL_AT)
    marks["cancel"] = time.monotonic()
    token.cancel("interjection", text="等一下，我想先問價格")
    print(f"  [{marks['cancel']-t0:6.2f}s] 送出取消（Action 生成中）")

threading.Thread(target=canceller, daemon=True).start()
seen = []
def cb(ev):
    if ev.get("phase") == "start":
        marks.setdefault(f"start_{ev.get('module')}", time.monotonic())

res = wf.run("請詳細說明如何挑選一雙適合久站工作的鞋子，包含鞋底、鞋墊、材質與尺寸，越詳細越好。",
             cancel=token, event_callback=cb)
t_end = time.monotonic()
print(f"  [{t_end-t0:6.2f}s] run() 返回")
print(f"  取消 → 停止延遲: {(t_end-marks['cancel'])*1000:.0f} ms")
print(f"  interrupted={res.interrupted}  aborted={res.aborted}")
print(f"  abort_reason={res.abort_reason}")
print(f"  payload={res.interrupt_payload}")
print(f"  context entries: {[getattr(e.type,'value',e.type) for e in res.entries]}")
print(f"  final_message 長度: {len(res.final_message or '')}")
