#!/usr/bin/env python3
"""图生图 / 改图：用一张或多张参考图 + prompt 生成新图（OpenAI /v1/images/edits）。

ProductFlow ③首图用：把 ②选中的参考图（或画布上点选的某张已生成图）喂给模型，
成品贴近参考的版式/风格，比纯文生图更可控。和 gen.py 同样的 env（OPENAI_API_KEY /
OPENAI_BASE_URL，可走 api.gjs.ink 网关）与输出约定（out-dir/prompts.json）。

用法：
  python3 edit.py --image ref1.png --image ref2.png \
    --prompt "<风格/产品/平台 + 纯 UI 约束>" --size 1080x2340 --count 2 \
    --model gpt-image-2 --out-dir <dir>
"""
import argparse
import base64
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
    p = argparse.ArgumentParser(description="图生图（/v1/images/edits）")
    p.add_argument("--image", action="append", required=True,
                   help="输入参考图路径，可重复（多张走 image[]）")
    p.add_argument("--mask", default=None,
                   help="蒙版 PNG（局部重绘/inpaint）：透明(alpha=0)区域=重绘，不透明区域=保留")
    p.add_argument("--prompt", required=True)
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--count", type=int, default=1, help="生成几张（n）")
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

    os.makedirs(args.out_dir, exist_ok=True)
    fields = [("model", args.model), ("prompt", args.prompt),
              ("size", args.size), ("n", str(max(1, args.count))),
              ("quality", args.quality)]
    # 多图用 image[]（gpt-image-* 支持多参考图）；单图也用 image[] 兼容
    files = [("image[]", os.path.basename(x), _ctype(x), open(x, "rb").read()) for x in imgs]
    # 局部重绘：mask 透明区域 = 让模型重画，不透明 = 原样保留
    if mask:
        files.append(("mask", os.path.basename(mask), "image/png", open(mask, "rb").read()))
    boundary, body = _multipart(fields, files)

    req = urllib.request.Request(_api_url(), data=body, method="POST", headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        raise SystemExit(f"edits HTTP {e.code}: {raw[:1000]}")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"request failed: {e}")

    items = []
    for i, d in enumerate(data.get("data") or [], 1):
        b64 = d.get("b64_json")
        if not b64:
            continue
        fn = f"edit-{i:02d}-{_slug(args.prompt)}.png"
        with open(os.path.join(args.out_dir, fn), "wb") as f:
            f.write(base64.b64decode(b64))
        items.append({"file": fn, "prompt": args.prompt, "inputs": [os.path.basename(x) for x in imgs],
                      "model": args.model, "size": args.size, "mode": "edit"})
        print(f"wrote {fn}")
    if not items:
        print("no image returned:", json.dumps(data)[:500], file=sys.stderr)
        return 1
    with open(os.path.join(args.out_dir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"out_dir={args.out_dir}  ({len(items)} image(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
