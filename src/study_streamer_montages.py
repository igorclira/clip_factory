"""
Clip Factory — Large-Scale Streamer Moments & Montages Deep Study Engine
(YouTube Shorts + TikTok via Apify -> 2-FPS Multimodal Gemini Forensic Audits -> Editing Bible)

Discovers 30-40+ viral 9:16 Streamer Moments / Funny Gaming Edits across BOTH YouTube Shorts
and TikTok (variety streamers: CaseOh, IShowSpeed, Jynxzi, Kai Cenat, WoW, GTA, FPS, horror,
general Twitch/Kick highlights), downloads TikTok .mp4s via Apify, audits EVERY video at 2 fps
with Gemini (video + audio together) using resilient retry/backoff + disk checkpointing,
filters out low-craft reuploads, and synthesizes a comprehensive Streamer Montage Editing Bible.

Usage:
    python src/study_streamer_montages.py --yt-limit 24 --tt-limit 16
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

CORE_ROOT = Path(__file__).resolve().parent.parent
STUDY_DIR = CORE_ROOT / "workspace" / "style_references" / "streamer_study"
AUDITS_DIR = STUDY_DIR / "audits"
TIKTOK_DIR = STUDY_DIR / "tiktok_clips"

YOUTUBE_QUERIES = [
    "twitch streamer funny moments edited shorts",
    "caseoh funny moments edit shorts",
    "ishowspeed funny moments edit shorts",
    "jynxzi funny moments edit shorts",
    "gaming funny moments montage shorts",
    "streamer rage funny edit shorts",
    "lethal company funny moments shorts",
    "valorant funny moments edited shorts",
    "wow classic funny moments shorts",
    "gta funny moments edited shorts",
    "kai cenat funny moments edit shorts",
    "twitch fails compilation shorts",
]

TIKTOK_HASHTAGS = [
    "streamermoments",
    "twitchclips",
    "funnygamingmoments",
    "gamingedits",
    "twitchfails",
    "caseohclips",
    "ishowspeedclips",
    "jynxziclips",
]


class VideoForensicAudit(BaseModel):
    masterpiece_score: int = Field(description="1-10 craft score (1-4 = raw reupload/AI slop, 5-6 = average, 7-10 = genuinely sharp human comedic editing)")
    is_raw_reupload_or_slop: bool = Field(description="True if this is just an unedited repost or low-effort AI slop")
    streamer_or_game: str = Field(description="Streamer(s) and/or game featured")
    editing_archetype: str = Field(description="e.g. 'Facecam Punch-In Comedy', 'Fast Multi-Clip Montage', 'Deadpan Subtitles + Audio Cut', 'Chaos Music Swap'")
    framing_9x16: str = Field(description="Exact 9:16 layout: stacked facecam+gameplay? Full vertical crop? How creator + action stay readable")
    subtitle_craft: str = Field(description="Exact subtitle style: how streamer speech is captioned, word chunking, color coding, size pops on screams, what is skipped, anti-lingering timing")
    zoom_and_camera_work: str = Field(description="Exact zoom timing, scale restraint (e.g. 1.15x-1.4x vs facecam cut), contextual targets, and why it stays readable")
    sfx_and_music_craft: str = Field(description="Specific SFX used, comedic timing, how BGM is used/swapped/muted for punchlines, and audio restraint vs clutter")
    comedic_timing_and_cuts: str = Field(description="How setup -> escalation -> punchline -> out-point works; why cuts land hilariously instead of cutting too early or lingering")
    standout_techniques: list[str] = Field(description="3-5 concrete, reusable Remotion/editing techniques learned from this specific video")
    anti_patterns_to_avoid: list[str] = Field(description="1-3 flaws or overused tricks in this video to avoid")


def parse_iso8601_duration(iso_dur: str) -> float:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_dur or "")
    if not m:
        return 0.0
    h, mins, secs = (int(x or 0) for x in m.groups())
    return float(h * 3600 + mins * 60 + secs)


def discover_youtube_shorts(limit: int) -> list[dict[str, Any]]:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[YouTube] YOUTUBE_API_KEY missing — skipping YouTube discovery")
        return []

    print(f"[YouTube] Discovering up to {limit} high-view Streamer Montage Shorts across {len(YOUTUBE_QUERIES)} queries...")
    seen_ids: set[str] = set()
    raw_ids: list[tuple[str, str]] = []

    for q in YOUTUBE_QUERIES:
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": q,
                    "type": "video",
                    "videoDuration": "short",
                    "order": "viewCount",
                    "relevanceLanguage": "en",
                    "maxResults": 8,
                    "key": api_key,
                },
                timeout=20,
            )
            if resp.status_code != 200:
                print(f"  [YouTube] Query '{q}' HTTP {resp.status_code}")
                continue
            for item in resp.json().get("items", []):
                vid = item.get("id", {}).get("videoId")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    raw_ids.append((vid, q))
        except requests.RequestException as exc:
            print(f"  [YouTube] Query '{q}' failed: {exc}")

    # Batch fetch video stats & durations
    candidates: list[dict[str, Any]] = []
    id_to_query = dict(raw_ids)
    all_ids = [x[0] for x in raw_ids]
    for i in range(0, len(all_ids), 50):
        batch = all_ids[i : i + 50]
        v_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet,statistics,contentDetails", "id": ",".join(batch), "key": api_key},
            timeout=20,
        )
        if v_resp.status_code != 200:
            continue
        for v in v_resp.json().get("items", []):
            vid = v["id"]
            dur = parse_iso8601_duration(v.get("contentDetails", {}).get("duration", ""))
            views = int(v.get("statistics", {}).get("viewCount", 0))
            if dur < 12 or dur > 75 or views < 50_000:
                continue
            snip = v.get("snippet", {})
            candidates.append({
                "id": f"yt_{vid}",
                "platform": "youtube",
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": snip.get("title", ""),
                "author": snip.get("channelTitle", ""),
                "views": views,
                "duration_sec": dur,
                "query": id_to_query.get(vid, ""),
            })

    # Diversify: max 2 videos per channel so we study MANY different editors!
    candidates.sort(key=lambda x: x["views"], reverse=True)
    picked: list[dict[str, Any]] = []
    per_author: dict[str, int] = {}
    for c in candidates:
        a = c["author"].lower()
        if per_author.get(a, 0) >= 2:
            continue
        per_author[a] = per_author.get(a, 0) + 1
        picked.append(c)
        if len(picked) >= limit:
            break

    print(f"[YouTube] Selected {len(picked)} diverse high-view Shorts (across {len(per_author)} channels)")
    return picked


def discover_and_download_tiktoks(limit: int) -> list[dict[str, Any]]:
    TIKTOK_DIR.mkdir(parents=True, exist_ok=True)
    existing_mp4s = sorted(p for p in TIKTOK_DIR.glob("*.mp4") if p.stat().st_size > 10_000)
    if len(existing_mp4s) >= min(limit, 10):
        print(f"[TikTok] Reusing {len(existing_mp4s)} already-downloaded TikTok .mp4s from disk (saving Apify credits)!")
        return [
            {
                "id": p.stem,
                "platform": "tiktok",
                "url": "",
                "title": f"TikTok Streamer Edit ({p.stem})",
                "author": "tiktok_creator",
                "views": 100000,
                "duration_sec": 35.0,
                "local_file": str(p),
            }
            for p in existing_mp4s[:limit]
        ]

    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        print("[TikTok] APIFY_TOKEN missing — skipping TikTok discovery")
        return []
    print(f"[TikTok/Apify] Discovering & downloading up to {limit} high-view Streamer Montage TikToks...")
    endpoint = "https://api.apify.com/v2/acts/clockworks~tiktok-hashtag-scraper/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "hashtags": TIKTOK_HASHTAGS,
        "resultsPerPage": 12,
        "shouldDownloadVideos": True,
    }
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
        items = resp.json()
    except requests.RequestException as exc:
        print(f"[TikTok/Apify] Scraper failed: {exc}")
        return []

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for item in items:
        vid_id = str(item.get("id") or "")
        if not vid_id or vid_id in seen:
            continue
        seen.add(vid_id)
        plays = int(item.get("playCount") or 0)
        dur = float((item.get("videoMeta") or {}).get("duration") or 0)
        media_urls = item.get("mediaUrls") or []
        dl_url = media_urls[0] if isinstance(media_urls, list) and media_urls else None
        if not dl_url or dur < 12 or dur > 75 or plays < 50_000:
            continue
        author = (item.get("authorMeta") or {}).get("name") or "unknown"
        candidates.append({
            "id": f"tt_{vid_id}",
            "platform": "tiktok",
            "url": item.get("webVideoUrl") or "",
            "title": (item.get("text") or "")[:140],
            "author": author,
            "views": plays,
            "duration_sec": dur,
            "direct_media_url": dl_url,
        })

    # Diversify: max 2 per creator
    candidates.sort(key=lambda x: x["views"], reverse=True)
    picked: list[dict[str, Any]] = []
    per_author: dict[str, int] = {}
    for c in candidates:
        a = c["author"].lower()
        if per_author.get(a, 0) >= 2:
            continue
        out_mp4 = TIKTOK_DIR / f"{c['id']}.mp4"
        if not out_mp4.exists():
            try:
                dl_headers = {"Authorization": f"Bearer {token}"} if "api.apify.com" in c["direct_media_url"] else {}
                with requests.get(c["direct_media_url"], headers=dl_headers, stream=True, timeout=90) as r:
                    r.raise_for_status()
                    with out_mp4.open("wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
                if out_mp4.stat().st_size < 10_000:
                    out_mp4.unlink(missing_ok=True)
                    continue
            except requests.RequestException as exc:
                print(f"  [TikTok] Download skipped for {c['id']}: {exc}")
                out_mp4.unlink(missing_ok=True)
                continue
        c["local_file"] = str(out_mp4)
        per_author[a] = per_author.get(a, 0) + 1
        picked.append(c)
        if len(picked) >= limit:
            break

    print(f"[TikTok/Apify] Downloaded {len(picked)} diverse high-view TikTok clips (across {len(per_author)} creators)")
    return picked


AUDIT_PROMPT = """
You are a master short-form gaming video editor studying top-performing 9:16 Streamer Moments &
Montages across YouTube Shorts and TikTok to teach an automated Remotion + Gemini pipeline.

Watch this video (BOTH visual frames and audio track carefully):
- Platform: {platform}
- Creator: {author}
- Views: {views:,}
- Duration: {duration_sec:.1f}s
- Title: {title}

Evaluate its REAL editing craft honestly (give a low score 1-4 if it's a lazy raw repost or AI slop;
give 7-10 ONLY if it shows genuinely sharp human comedic editing, captioning, framing, and SFX/music timing).

Focus intensely on:
1. **Streamer Subtitles:** How are the streamer's actual spoken words captioned? Word chunk size, color coding, font pop on screams/laughs, and when subtitles disappear cleanly.
2. **9:16 Framing & Zooms:** How does the editor keep BOTH facecam and gameplay readable? When do they zoom in, how much, and why does it feel funny instead of disorienting?
3. **Music & SFX Timing:** When do they replace/add upbeat or comedic BGM? What exact SFX hit on punchlines? How much raw streamer audio stays untouched?
4. **Comedic Cut Rhythm:** How do they set up the joke, hold just long enough for the payoff to land (NOT cutting on a confusing cliffhanger), and exit cleanly?
"""


def call_gemini_resilient(
    client: genai.Client,
    models: list[str],
    contents: Any,
    schema: Any = None,
    max_attempts: int = 3,
) -> str:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        for m in models:
            try:
                cfg_kwargs: dict[str, Any] = {"temperature": 0.3}
                if schema is not None:
                    cfg_kwargs["response_mime_type"] = "application/json"
                    cfg_kwargs["response_schema"] = schema
                resp = client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=types.GenerateContentConfig(**cfg_kwargs),
                )
                return resp.text or ""
            except Exception as exc:
                last_err = exc
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg or "UNAVAILABLE" in msg:
                    wait_s = 12 * (attempt + 1)
                    print(f"    [Rate/Demand] {m} busy -> trying next/waiting {wait_s}s...")
                    time.sleep(wait_s)
                else:
                    print(f"    [Error] {m}: {msg[:140]}")
                    time.sleep(3)
    raise RuntimeError(f"Gemini calls exhausted: {last_err}")


def audit_single_video(client: genai.Client, models: list[str], item: dict[str, Any]) -> dict[str, Any]:
    prompt = AUDIT_PROMPT.format(
        platform=item["platform"],
        author=item["author"],
        views=item["views"],
        duration_sec=item["duration_sec"],
        title=item["title"],
    )

    uploaded = None
    try:
        if item["platform"] == "youtube":
            contents = types.Content(
                role="user",
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=item["url"]),
                        video_metadata=types.VideoMetadata(fps=2.0),
                    ),
                    types.Part.from_text(text=prompt),
                ],
            )
        else:
            local_mp4 = Path(item["local_file"])
            uploaded = client.files.upload(file=str(local_mp4))
            while uploaded.state.name == "PROCESSING":
                time.sleep(2)
                uploaded = client.files.get(name=uploaded.name)
            if uploaded.state.name != "ACTIVE":
                raise RuntimeError(f"Upload failed: {uploaded.state.name}")
            contents = [uploaded, prompt]

        raw_json = call_gemini_resilient(client, models, contents, schema=VideoForensicAudit)
        parsed = VideoForensicAudit.model_validate_json(raw_json)
        return {**item, "audit": parsed.model_dump()}
    finally:
        if uploaded is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass


def synthesize_bible(client: genai.Client, models: list[str], completed: list[dict[str, Any]]) -> str:
    high_craft = [x for x in completed if x["audit"]["masterpiece_score"] >= 7 and not x["audit"]["is_raw_reupload_or_slop"]]
    slop_examples = [x for x in completed if x["audit"]["masterpiece_score"] <= 4 or x["audit"]["is_raw_reupload_or_slop"]]

    # Fallback if threshold too strict
    if len(high_craft) < 5:
        high_craft = sorted(completed, key=lambda x: x["audit"]["masterpiece_score"], reverse=True)[:15]

    summary_payload = {
        "total_studied": len(completed),
        "youtube_studied": sum(1 for x in completed if x["platform"] == "youtube"),
        "tiktok_studied": sum(1 for x in completed if x["platform"] == "tiktok"),
        "high_craft_winners": [
            {
                "id": x["id"],
                "platform": x["platform"],
                "author": x["author"],
                "views": x["views"],
                "score": x["audit"]["masterpiece_score"],
                **x["audit"],
            }
            for x in high_craft
        ],
        "low_craft_anti_examples": [
            {
                "id": x["id"],
                "platform": x["platform"],
                "score": x["audit"]["masterpiece_score"],
                "anti_patterns": x["audit"]["anti_patterns_to_avoid"],
            }
            for x in slop_examples[:10]
        ],
    }

    prompt = f"""
You have just completed a large-scale multimodal study of **{len(completed)} viral 9:16 Streamer Moments &
Montages** across **YouTube Shorts AND TikTok**.

Synthesize ALL findings into the definitive **Streamer Montage Editing & Comedic Timing Bible**
for our automated Remotion + Gemini + Epidemic Sound studio (`clip_factory`, `gta6_clips`, `wow_forever_clips`).

Make every section concrete, technical, and immediately implementable in code:

1. **Executive Summary of What Separates Viral 9/10 Streamer Edits from Forgettable Clips**
   - Cite specific patterns observed across YouTube Shorts vs. TikTok creators we just studied.
2. **The Streamer Subtitle System (Exact Spec for Auto-Whisper + Editorial Popups):**
   - Exactly how top editors caption live streamer speech (1-3 word kinetic chunks, scream/emphasis scaling, color-coding Speaker A vs Speaker B vs funny NPC vs deadpan Editorial popup).
   - How to combine continuous tight Whisper streamer captions with sparse deadpan editorial callouts without visual clutter.
3. **9:16 Framing, Facecam Choreography & Smart Crop Rules:**
   - How top editors handle: (a) native 9:16 streamer clips, (b) 16:9 Twitch clips with facecams, (c) badly letterboxed clips with black bars.
   - Exact rules for contextual zooms (scale, duration, when to zoom facecam vs gameplay, why over-zooming kills comedy).
4. **Comedic Timing, Setup-to-Payoff Arcs & Never Cutting on a Cliffhanger:**
   - Exact timing rules for comedic rhythm: when to hard-cut right on an impact ("perfectly cut scream") vs. when to let the reaction/consequence play out 1.5–3.0s so the joke actually lands.
5. **Music Swaps & Studio SFX Playbook (Epidemic Sound Strategy):**
   - Exact scenarios where replacing bad/awkward clip audio with an upbeat or ironic track elevates the joke.
   - Specific comedy/meme/hero/tension SFX categories we should add to `shared_assets/sfx/` beyond our current 18 (especially comedic/superhero/cartoon/reaction stingers!).
   - Audio balance & restraint rules (the 85%+ raw audio rule, avoiding bass-drop fatigue).
6. **Concrete Code Upgrades for `analyze_gemini.py` and `remotion_studio/`:**
   - Exact JSON fields, Whisper caption auto-builder logic, and Remotion component upgrades needed so Video #1 v5 (and every future GTA 6 & WoW Forever video) hits genuine viral quality on the first render.

STUDY DATASET:
{json.dumps(summary_payload, indent=2, ensure_ascii=False)}
"""
    return call_gemini_resilient(client, models, prompt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deep Study: Streamer Moments & Montages (YouTube Shorts + TikTok)")
    parser.add_argument("--yt-limit", type=int, default=22, help="Max YouTube Shorts to audit")
    parser.add_argument("--tt-limit", type=int, default=14, help="Max TikToks to audit")
    args = parser.parse_args()

    load_dotenv(CORE_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing in clip_factory/.env")

    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    AUDITS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = STUDY_DIR / "study_manifest.json"
    if manifest_path.exists():
        items = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"[Study] Loaded cached manifest with {len(items)} videos.")
    else:
        yt_items = discover_youtube_shorts(args.yt_limit)
        tt_items = discover_and_download_tiktoks(args.tt_limit)
        items = yt_items + tt_items
        manifest_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Study] Saved manifest with {len(items)} videos ({len(yt_items)} YT + {len(tt_items)} TikTok)")

    client = genai.Client(api_key=api_key)
    avail = {m.name.replace("models/", "") for m in client.models.list()}
    models = [m for m in ("gemini-3.8-flash", "gemini-3.5-flash-lite") if m in avail]
    print(f"[Study] Auditing {len(items)} videos with models: {models}")

    completed: list[dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        audit_file = AUDITS_DIR / f"{item['id']}.json"
        if audit_file.exists():
            data = json.loads(audit_file.read_text(encoding="utf-8"))
            completed.append(data)
            print(f"[{idx}/{len(items)}] Cached: {item['id']} (score={data['audit']['masterpiece_score']}/10)")
            continue

        print(f"[{idx}/{len(items)}] Watching {item['platform'].upper()} @{item['author']} ({item['views']:,} views, {item['duration_sec']:.0f}s)...")
        try:
            res = audit_single_video(client, models, item)
            audit_file.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
            completed.append(res)
            sc = res["audit"]["masterpiece_score"]
            arch = res["audit"]["editing_archetype"]
            print(f"  -> Score {sc}/10 | {arch}")
            time.sleep(3)  # polite pacing to stay comfortably under RPM quotas
        except Exception as exc:
            print(f"  -> Skipped {item['id']}: {exc}")

    if not completed:
        raise SystemExit("No videos were audited.")

    print(f"\n[Study] Synthesizing STREAMER_EDITING_BIBLE.md from {len(completed)} audited videos...")
    bible = synthesize_bible(client, models, completed)
    bible_path = STUDY_DIR / "STREAMER_EDITING_BIBLE.md"
    bible_path.write_text(bible, encoding="utf-8")

    high_cnt = sum(1 for x in completed if x["audit"]["masterpiece_score"] >= 7 and not x["audit"]["is_raw_reupload_or_slop"])
    print(f"\nDONE! Studied {len(completed)} videos ({high_cnt} high-craft 7+/10 winners).")
    print(f"Bible saved -> {bible_path}")


if __name__ == "__main__":
    main()
