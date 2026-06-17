#!/usr/bin/env python3
"""抓取 App Store / Google Play 上架页的**官方特色截图**——Phase 1 市场调研给 APP 类项目用。

为什么：对 APP 产品，竞品的"落地页"其实是商店上架页，开发者上传的截图就是这个 App
最核心的几屏真实界面，比 Dribbble 设计稿直观得多。本脚本把这些官方截图拉到本地，
作为①调研素材、并供②找参考当真实参考来源。

数据来源（都免鉴权）：
- iOS：Apple iTunes Search/Lookup API（JSON 直出 `screenshotUrls` / `ipadScreenshotUrls`）——干净稳。
- Android：Google Play 上架页 HTML 里抓 `play-lh.googleusercontent.com` 截图——best-effort，较脆。

用法：
  python3 appstore_shots.py --platform ios   --term "habit tracker"   --out artifacts/phase-1/appstore --limit 3
  python3 appstore_shots.py --platform android --term "habit tracker"  --out <dir> --limit 3
  python3 appstore_shots.py --platform both   --term "..." --out <dir>
  python3 appstore_shots.py --platform ios    --id 1234567890 --out <dir>     # 指定某个 App

只下载 + 写 manifest.json；登记成 ProductFlow 产物由调用方（agent）用 pf_state artifact 完成。
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ---- HTTP（测试里 monkeypatch 这三个，避免真实联网）-------------------------
def _open(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=timeout)


def _http_json(url: str, timeout: int = 15):
    with _open(url, timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _http_text(url: str, timeout: int = 15) -> str:
    with _open(url, timeout) as r:
        return r.read().decode("utf-8", "replace")


def _download(url: str, path: str, timeout: int = 30) -> int:
    with _open(url, timeout) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# ---- 解析 ----------------------------------------------------------------
def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "app"


def _ext_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ".png"


def ios_search(term: str, country: str = "us", limit: int = 3, timeout: int = 15):
    """iTunes Search API → 候选 App 列表（含官方截图 URL）。"""
    qs = urllib.parse.urlencode({"term": term, "country": country,
                                 "entity": "software", "limit": max(1, limit)})
    data = _http_json("https://itunes.apple.com/search?" + qs, timeout)
    return _ios_results(data, limit)


def ios_lookup(app_id: str, country: str = "us", timeout: int = 15):
    """按 App id 精确查一个 App。"""
    qs = urllib.parse.urlencode({"id": app_id, "country": country})
    data = _http_json("https://itunes.apple.com/lookup?" + qs, timeout)
    return _ios_results(data, 1)


def _ios_results(data: dict, limit: int):
    out = []
    for r in (data.get("results") or [])[:limit]:
        shots = r.get("screenshotUrls") or r.get("ipadScreenshotUrls") or []
        out.append({"platform": "ios",
                    "name": r.get("trackName") or "app",
                    "seller": r.get("sellerName") or "",
                    "url": r.get("trackViewUrl") or "",
                    "shots": list(shots)})
    return out


def android_search(term: str, hl: str = "en", gl: str = "us",
                   limit: int = 3, timeout: int = 15):
    """Google Play 搜索页 → 前 N 个 app 的 package id。"""
    qs = urllib.parse.urlencode({"q": term, "c": "apps", "hl": hl, "gl": gl})
    html = _http_text("https://play.google.com/store/search?" + qs, timeout)
    pkgs = []
    for m in re.finditer(r"/store/apps/details\?id=([a-zA-Z0-9._]+)", html):
        p = m.group(1)
        if p not in pkgs:
            pkgs.append(p)
        if len(pkgs) >= limit:
            break
    return pkgs


def android_details(pkg: str, hl: str = "en", gl: str = "us", timeout: int = 15):
    """Google Play 上架页 → app 名 + 截图 URL（best-effort，过滤掉明显的图标/小图）。"""
    qs = urllib.parse.urlencode({"id": pkg, "hl": hl, "gl": gl})
    html = _http_text("https://play.google.com/store/apps/details?" + qs, timeout)
    name = pkg
    m = re.search(r"<title[^>]*>([^<]+)</title>", html)
    if m:
        name = re.sub(r"\s*[-–]\s*Apps on Google Play.*$", "", m.group(1)).strip() or pkg
    shots, seen = [], set()
    # 截图带 =w<宽>-h<高>，过滤掉小图标（宽高都要够大）
    for m in re.finditer(r"https://play-lh\.googleusercontent\.com/[\w\-]+=w(\d+)-h(\d+)[\w\-]*", html):
        url, w, h = m.group(0), int(m.group(1)), int(m.group(2))
        base = url.split("=w")[0]
        if w >= 300 and h >= 300 and base not in seen:
            seen.add(base)
            shots.append(url)
    return {"platform": "android", "name": name, "seller": "",
            "url": "https://play.google.com/store/apps/details?id=" + pkg,
            "shots": shots}


# ---- 编排 ----------------------------------------------------------------
def collect(platform: str, out_dir: str, term=None, app_ids=None,
            limit: int = 3, max_shots: int = 8, country: str = "us",
            hl: str = "en", timeout: int = 15):
    """抓取 → 下载 → 写 manifest。返回 manifest 列表。出错的单个 App/截图跳过、不中断。"""
    apps = []
    if platform in ("ios", "both"):
        try:
            if app_ids:
                for i in app_ids:
                    apps += ios_lookup(i, country, timeout)
            elif term:
                apps += ios_search(term, country, limit, timeout)
        except Exception as e:  # noqa: BLE001 — best-effort，整源失败也别炸
            print(f"[appstore] iOS 抓取失败：{e}", file=sys.stderr)
    if platform in ("android", "both"):
        try:
            pkgs = list(app_ids) if (app_ids and platform == "android") else \
                (android_search(term, hl, country, limit, timeout) if term else [])
            for p in pkgs:
                try:
                    apps.append(android_details(p, hl, country, timeout))
                except Exception as e:  # noqa: BLE001
                    print(f"[appstore] Android {p} 详情失败：{e}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[appstore] Android 搜索失败：{e}", file=sys.stderr)

    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for app in apps:
        shots = app.get("shots") or []
        if not shots:
            print(f"[appstore] {app['platform']} {app['name']}：无截图，跳过", file=sys.stderr)
            continue
        sub = os.path.join(out_dir, app["platform"] + "-" + _slug(app["name"]))
        os.makedirs(sub, exist_ok=True)
        saved = []
        for idx, url in enumerate(shots[:max_shots], 1):
            path = os.path.join(sub, f"{idx}{_ext_from_url(url)}")
            try:
                _download(url, path, timeout)
                saved.append(os.path.relpath(path, out_dir))
            except Exception as e:  # noqa: BLE001
                print(f"[appstore] 下载失败 {url}: {e}", file=sys.stderr)
        if saved:
            manifest.append({"platform": app["platform"], "name": app["name"],
                             "seller": app.get("seller", ""), "store_url": app.get("url", ""),
                             "dir": os.path.relpath(sub, out_dir), "files": saved})
            print(f"[appstore] {app['platform']} {app['name']}：存 {len(saved)} 张", file=sys.stderr)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description="抓取 App Store / Google Play 官方特色截图")
    ap.add_argument("--platform", required=True, choices=["ios", "android", "both"])
    ap.add_argument("--term", help="按品类/关键词搜竞品 App（如 'habit tracker'）")
    ap.add_argument("--id", action="append", dest="app_ids",
                    help="指定 App：iOS 用数字 trackId，Android 用 package 名；可重复")
    ap.add_argument("--out", required=True, help="输出目录（如 artifacts/phase-1/appstore）")
    ap.add_argument("--limit", type=int, default=3, help="搜多少个 App（默认 3）")
    ap.add_argument("--max-shots", type=int, default=8, help="每个 App 最多存几张（默认 8）")
    ap.add_argument("--country", default="us", help="iOS country / Android gl（默认 us）")
    ap.add_argument("--hl", default="en", help="Android 语言（默认 en）")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args(argv)
    if not args.term and not args.app_ids:
        ap.error("需要 --term 或 --id 至少一个")
    manifest = collect(args.platform, args.out, term=args.term, app_ids=args.app_ids,
                       limit=args.limit, max_shots=args.max_shots,
                       country=args.country, hl=args.hl, timeout=args.timeout)
    total = sum(len(a["files"]) for a in manifest)
    print(f"✅ 抓到 {len(manifest)} 个 App、共 {total} 张官方截图 → {args.out}/")
    print(f"   manifest: {os.path.join(args.out, 'manifest.json')}")
    return 0 if manifest else 1


if __name__ == "__main__":
    sys.exit(main())
