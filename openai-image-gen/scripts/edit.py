#!/usr/bin/env python3
"""图生图 / 改图：用一张或多张参考图 + prompt 生成新图（OpenAI /v1/images/edits）。

ProductFlow ③首图用：把 ②选中的参考图（或画布上点选的某张已生成图）喂给模型，
成品贴近参考的版式/风格，比纯文生图更可控。和 gen.py 同样的 env（OPENAI_API_KEY /
OPENAI_BASE_URL，可走 api.gjs.ink 网关）与输出约定（out-dir/prompts.json）。

批量：`--count N` 出 N 张。图像 edits 端点常把单请求 n 限制为 1，所以这里**像 gen.py 一样
做客户端并发**——发 N 个 n=1 的并行请求（`--concurrency` 控并发），保证真的拿到 N 张、且并行更快。

用法：
  python3 edit.py --image ref1.png --image ref2.png \
    --prompt "<风格/产品/平台 + 纯 UI 约束>" --size 1080x2340 --count 4 \
    --concurrency 4 --model gpt-image-2 --out-dir <dir>
"""
import argparse
import base64
import concurrent.futures
import json
import os
import sys
import urllib.error
import urllib.request


def _api_url() -> str:
    base = (os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("OPENAI_API_BASE")
            or "https://api.openai.com").rstrip("/")
    return f"{base}/images/edits" if base.endswith("/v1") else f"{base}/v1/images/edits"


def _slug(text: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "edit"


def _multipart(fields, files):
    """编码 multipart/form-data。fields: [(name,value)]；files: [(name,filename,ctype,bytes)]。"""
    boundary = "----productflow" + os.urandom(16).hex()
    out = bytearray()
    for name, value in fields:
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += f"{value}\r\n".encode()
    for name, filename, ctype, content in files:
        out += f"--{boundary}\r\n".encode()
        out += (f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n').encode()
        out += f"Content-Type: {ctype}\r\n\r\n".encode()
        out += content + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return boundary, bytes(out)


def _ctype(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp"}.get(ext, "image/png")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="图生图（/v1/images/edits），支持批量并发")
    p.add_argument("--image", action="append", required=True,
                   help="输入参考图路径，可重复（多张走 image[]）")
    p.add_argument("--mask", default=None,
                   help="蒙版 PNG（局部重绘/inpaint）：透明(alpha=0)区域=重绘，不透明区域=保留")
    p.add_argument("--prompt", required=True)
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--count", type=int, default=1, help="生成几张（客户端并发发 N 个 n=1 请求）")
    p.add_argument("--concurrency", type=int, default=4, help="count>1 时并行出图的最大并发")
    p.add_argument("--quality", default="high")
    p.add_argument("--model", default="gpt-image-1.5")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--api-key", default=None)
    args = p.parse_args(argv)

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("missing OPENAI_API_KEY (env 或 --api-key)")

    imgs = [os.path.expanduser(x) for x in args.image]
    missing = [x for x in imgs if not os.path.isfile(x)]
    if missing:
        raise SystemExit("input image(s) not found: " + ", ".join(missing))
    mask = os.path.expanduser(args.mask) if args.mask else None
    if mask and not os.path.isfile(mask):
        raise SystemExit("mask not found: " + mask)

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    # 输入图/蒙版只读一次，并行请求间复用（避免重复读盘 + 句柄泄漏）
    img_files = [(os.path.basename(x), _ctype(x), open(x, "rb").read()) for x in imgs]
    mask_name = os.path.basename(mask) if mask else None
    mask_bytes = open(mask, "rb").read() if mask else None
    n = max(1, args.count)
    url = _api_url()

    def _edit(i: int) -> dict:
        # 一个 worker 线程发一个 n=1 请求；i 是 1-based 序号，保证文件名顺序稳定
        fields = [("model", args.model), ("prompt", args.prompt),
                  ("size", args.size), ("n", "1"), ("quality", args.quality)]
        files = [("image[]", bn, ct, data) for (bn, ct, data) in img_files]
        if mask_bytes is not None:
            files.append(("mask", mask_name, "image/png", mask_bytes))
        boundary, body = _multipart(fields, files)
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:  # noqa: S310
            data = json.loads(resp.read())
        b64 = (data.get("data") or [{}])[0].get("b64_json")
        if not b64:
            raise RuntimeError("no image returned: " + json.dumps(data)[:500])
        fn = f"edit-{i:02d}-{_slug(args.prompt)}.png"
        with open(os.path.join(out_dir, fn), "wb") as f:
            f.write(base64.b64decode(b64))
        print(f"wrote {fn}")
        return {"file": fn, "prompt": args.prompt, "inputs": [bn for bn, _, _ in img_files],
                "model": args.model, "size": args.size, "mode": "edit"}

    results: dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        futs = {ex.submit(_edit, i): i for i in range(1, n + 1)}
        for fut in concurrent.futures.as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except urllib.error.HTTPError as e:
                raw = e.read().decode("utf-8", "replace")
                print(f"failed {i:02d}: HTTP {e.code}: {raw[:300]}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                print(f"failed {i:02d}: {e}", file=sys.stderr)

    items = [results[i] for i in sorted(results)]
    if not items:
        print("no image returned (all requests failed)", file=sys.stderr)
        return 1
    with open(os.path.join(out_dir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"out_dir={out_dir}  ({len(items)} image(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
