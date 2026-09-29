#!/usr/bin/env python3
"""ComfyUI 冒烟测试：载入 API 格式工作流，走 /prompt 生成并校验输出。
用法: python scripts/test_gen.py [--workflow 路径] [--prompt 文本] [--w 832] [--h 480] [--frames 81] [--steps 20]
"""
import argparse, json, os, sys, time, urllib.request
from pathlib import Path

BASE = os.environ.get("COMFYUI_HOST", "http://127.0.0.1:8188")
ROOT = Path(__file__).resolve().parent.parent


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", default=str(ROOT / "workflows" / "wan22_t2v_api.json"))
    ap.add_argument("--prompt", default=None, help="正向提示词/台词；不传则使用工作流 JSON 里的原文")
    ap.add_argument("--neg", default=None, help="负向提示词（仅 Wan 类工作流有负向节点）")
    ap.add_argument("--pos-id", default="7", help="正向提示词节点 id")
    ap.add_argument("--neg-id", default="8", help="负向提示词节点 id")
    ap.add_argument("--latent-id", default="9", help="EmptyHunyuanLatentVideo 节点 id")
    ap.add_argument("--w", type=int, default=832)
    ap.add_argument("--h", type=int, default=480)
    ap.add_argument("--frames", type=int, default=81)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()

    wf = json.load(open(a.workflow))
    if a.prompt is not None:
        has_clip = any(n.get("class_type") == "CLIPTextEncode" for n in wf.values())
        # H3 类工作流没有 CLIPTextEncode，prompt 是节点内嵌控件；此时自动定位唯一带 prompt 输入的节点
        auto_prompt_id = None
        if not has_clip:
            cands = [nid for nid, n in wf.items() if "prompt" in n.get("inputs", {})]
            if len(cands) == 1:
                auto_prompt_id = cands[0]
        for nid, node in wf.items():
            if nid == a.pos_id and node.get("class_type") == "CLIPTextEncode":
                node["inputs"]["text"] = a.prompt
            if nid == auto_prompt_id or (nid == a.pos_id and "prompt" in node.get("inputs", {})):
                node["inputs"]["prompt"] = a.prompt
    if a.neg is not None:
        for nid, node in wf.items():
            if nid == a.neg_id and node.get("class_type") == "CLIPTextEncode":
                node["inputs"]["text"] = a.neg
    for nid, node in wf.items():
        if nid == a.latent_id and "width" in node.get("inputs", {}):
            node["inputs"]["width"], node["inputs"]["height"] = a.w, a.h
            node["inputs"]["length"] = a.frames
        # 调整步数：双专家工作流按 1:1 拆分（阶段1: 0~half；阶段2: half~steps）
        if node.get("class_type") == "KSamplerAdvanced":
            node["inputs"]["steps"] = a.steps
            if node["inputs"]["add_noise"] == "enable":
                node["inputs"]["start_at_step"] = 0
                node["inputs"]["end_at_step"] = a.steps // 2
            else:
                node["inputs"]["start_at_step"] = a.steps // 2
                node["inputs"]["end_at_step"] = a.steps
        if node.get("class_type") == "KSampler":
            node["inputs"]["steps"] = a.steps

    t0 = time.time()
    try:
        res = post("/prompt", {"prompt": wf})
    except urllib.error.HTTPError as e:
        print("PROMPT REJECTED:", e.code, e.read().decode()[:1000])
        sys.exit(4)
    pid = res["prompt_id"]
    print(f"queued prompt_id={pid}")

    while time.time() - t0 < a.timeout:
        time.sleep(10)
        h = get("/history/" + pid)
        rec = h.get(pid)
        if rec and rec.get("status", {}).get("completed"):
            outs = rec["outputs"]
            files = [f for o in outs.values() for f in o.get("images", [])] + \
                    [f for o in outs.values() for f in o.get("gifs", [])]
            print(f"DONE in {time.time()-t0:.0f}s")
            print(json.dumps(outs, ensure_ascii=False)[:600])
            sys.exit(0 if files else 2)
        if rec and rec.get("status", {}).get("status_str") == "error":
            print("ERROR:", json.dumps(rec["status"].get("messages", []), ensure_ascii=False)[:1200])
            sys.exit(1)
        print(f"  ... {time.time()-t0:.0f}s")
    print("TIMEOUT")
    sys.exit(3)


if __name__ == "__main__":
    main()
