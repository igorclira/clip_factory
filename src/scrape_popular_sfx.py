"""
Clip Factory — Bulk Popular & Viral SFX Library Scraper (MyInstants Leaderboards)

Scrapes hundreds of the most popular & trending meme, gaming, reaction, movie, and
sound-effect bites directly from MyInstants category & trending leaderboards into
`shared_assets/sfx_library/`, filters for clean short clips (0.2s - 8.5s), measures
exact `duration_sec` and acoustic `peak_sec` via FFmpeg + numpy, and writes a fast
searchable catalog to `shared_assets/sfx_catalog.json`.

Usage:
    python src/scrape_popular_sfx.py --target 350 --pages 5
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import requests

CORE_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = CORE_ROOT / "shared_assets" / "sfx_library"
CATALOG_PATH = CORE_ROOT / "shared_assets" / "sfx_catalog.json"

# Top popularity & category feeds on MyInstants
FEEDS: list[tuple[str, str]] = [
    ("trending", "https://www.myinstants.com/en/index/us/?page={page}"),
    ("memes", "https://www.myinstants.com/en/categories/memes/?page={page}"),
    ("sound_effects", "https://www.myinstants.com/en/categories/sound%20effects/?page={page}"),
    ("reactions", "https://www.myinstants.com/en/categories/reactions/?page={page}"),
    ("games", "https://www.myinstants.com/en/categories/games/?page={page}"),
    ("movies", "https://www.myinstants.com/en/categories/movies/?page={page}"),
    ("viral", "https://www.myinstants.com/en/categories/viral/?page={page}"),
    ("anime", "https://www.myinstants.com/en/categories/anime%20%26%20manga/?page={page}"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

INSTANT_RE = re.compile(
    r"onclick=\"play\('(/media/sounds/[^']+\.mp3)'[^)]*\)\"[^>]*title=\"Play ([^\"]+) sound\"",
    re.IGNORECASE,
)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return s[:64] or "sound"


def measure_audio_peak(audio_path: Path, sr: int = 16000) -> tuple[float, float]:
    try:
        raw = subprocess.check_output(
            [
                "ffmpeg", "-v", "error", "-i", str(audio_path),
                "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", str(sr), "-",
            ],
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        samples = np.frombuffer(raw, dtype=np.float32)
        if samples.size == 0:
            return 0.0, 0.0
        dur = round(samples.size / sr, 3)
        win = max(1, int(sr * 0.02))
        if samples.size <= win:
            return dur, 0.0
        sq = samples.astype(np.float64) ** 2
        csum = np.cumsum(np.insert(sq, 0, 0.0))
        rms = np.sqrt((csum[win:] - csum[:-win]) / win)
        peak = round(int(np.argmax(rms)) / sr, 3)
        return dur, peak
    except Exception:
        return 0.0, 0.0


def discover_feed(category: str, url_template: str, pages: int) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for p in range(1, pages + 1):
        url = url_template.format(page=p)
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                break
            page_html = html.unescape(r.text)
            matches = INSTANT_RE.findall(page_html)
            if not matches:
                break
            for mp3_rel, title in matches:
                found.append({
                    "category": category,
                    "title": title.strip(),
                    "url": f"https://www.myinstants.com{mp3_rel}",
                })
        except requests.RequestException:
            break
        time.sleep(0.35)
    print(f"  [Discover] {category}: {len(found)} candidates across {pages} page(s)")
    return found


def download_and_measure(item: dict[str, str], existing_tags: set[str]) -> dict[str, Any] | None:
    tag = slugify(item["title"])
    if not tag or tag in existing_tags:
        return None
    out_path = LIB_DIR / f"{tag}.mp3"
    if not out_path.exists():
        try:
            r = requests.get(item["url"], headers=HEADERS, timeout=25)
            if r.status_code != 200 or len(r.content) < 2000:
                return None
            out_path.write_bytes(r.content)
        except requests.RequestException:
            out_path.unlink(missing_ok=True)
            return None

    dur, peak = measure_audio_peak(out_path)
    if dur < 0.18 or dur > 8.5:
        out_path.unlink(missing_ok=True)
        return None

    return {
        "tag": tag,
        "filename": out_path.name,
        "title": item["title"],
        "category": item["category"],
        "duration_sec": dur,
        "peak_sec": peak,
        "source_url": item["url"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape hundreds of popular viral SFX from MyInstants")
    parser.add_argument("--target", type=int, default=400, help="Target total sounds in sfx_library/")
    parser.add_argument("--pages", type=int, default=5, help="Pages to crawl per category feed")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent download workers")
    args = parser.parse_args()

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    catalog: dict[str, dict[str, Any]] = (
        json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.exists() else {}
    )
    print(f"[BulkSFX] Existing catalog entries: {len(catalog)} | Target: {args.target}")

    # 1. Crawl leaderboards
    raw_items: list[dict[str, str]] = []
    seen_urls: set[str] = {v.get("source_url", "") for v in catalog.values()}
    for cat, tmpl in FEEDS:
        for it in discover_feed(cat, tmpl, args.pages):
            if it["url"] not in seen_urls:
                seen_urls.add(it["url"])
                raw_items.append(it)

    print(f"[BulkSFX] Discovered {len(raw_items)} unique new sound candidates. Downloading & peak-syncing...")
    needed = max(0, args.target - len(catalog))
    to_fetch = raw_items[: int(needed * 1.4) + 40]  # buffer for clips filtered out by >8.5s duration

    added = 0
    existing_tags = set(catalog.keys())
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_and_measure, it, existing_tags) for it in to_fetch]
        for fut in as_completed(futures):
            res = fut.result()
            if res and res["tag"] not in catalog:
                tag = res.pop("tag")
                catalog[tag] = res
                existing_tags.add(tag)
                added += 1
                if added % 25 == 0:
                    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"  [Progress] {len(catalog)} total sounds indexed (+{added} new)...")
                if len(catalog) >= args.target:
                    break

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDONE! Library now has {len(catalog)} popular peak-synced SFX (+{added} new) -> {CATALOG_PATH}")


if __name__ == "__main__":
    main()
