"""
Clip Factory — Scout V1 (Twitch Helix + Reddit + Apify TikTok)

Discovers viral and small-channel breakout clips, deduplicates via local SQLite,
scores by Velocity + Outlier Ratio, downloads top candidates with yt-dlp into
workspace/<channel>/01_inbox_raw/<date>/, and generates an interactive local
review_sheet.html for fast human-in-the-loop curation.

Usage:
    python src/scout_clips.py --channel wow_forever
    python src/scout_clips.py --channel gta6 --limit 15
    python src/scout_clips.py --channel gta6 --sources reddit --no-download
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass
class ClipCandidate:
    platform: str
    clip_id: str
    channel_id: str
    title: str
    url: str
    author: str
    author_followers: int | None
    views_or_score: int
    age_hours: float
    duration_sec: float | None
    created_at: str
    thumbnail_url: str
    velocity: float
    outlier_ratio: float
    scout_score: float
    is_small_creator_outlier: bool
    local_file: str | None = None
    direct_media_url: str | None = None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_clips (
            platform TEXT NOT NULL,
            clip_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            author TEXT,
            views_or_score INTEGER,
            scout_score REAL,
            first_seen_at TEXT NOT NULL,
            local_file TEXT,
            PRIMARY KEY (platform, clip_id)
        )
        """
    )
    conn.commit()
    return conn


def is_seen(conn: sqlite3.Connection, platform: str, clip_id: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM seen_clips WHERE platform = ? AND clip_id = ?",
        (platform, clip_id),
    )
    return cur.fetchone() is not None


def mark_seen(conn: sqlite3.Connection, clip: ClipCandidate) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO seen_clips
        (platform, clip_id, channel_id, title, url, author, views_or_score, scout_score, first_seen_at, local_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            clip.platform,
            clip.clip_id,
            clip.channel_id,
            clip.title,
            clip.url,
            clip.author,
            clip.views_or_score,
            clip.scout_score,
            dt.datetime.now(dt.timezone.utc).isoformat(),
            clip.local_file,
        ),
    )
    conn.commit()


def compute_scores(
    views_or_score: int,
    age_hours: float,
    author_followers: int | None,
    platform: str,
    outlier_rules: dict[str, Any],
) -> tuple[float, float, float, bool]:
    safe_age = max(age_hours, 1.0)
    velocity = views_or_score / safe_age

    is_outlier = False
    if platform == "twitch" and author_followers is not None:
        outlier_ratio = views_or_score / max(author_followers, 100)
        max_f = int(outlier_rules.get("twitch_max_followers", 15000))
        min_v = int(outlier_rules.get("twitch_min_views", 1500))
        is_outlier = author_followers <= max_f and views_or_score >= min_v
    elif platform == "tiktok" and author_followers is not None:
        outlier_ratio = views_or_score / max(author_followers, 100)
        max_f = int(outlier_rules.get("tiktok_max_author_fans", 250000))
        is_outlier = author_followers <= max_f and outlier_ratio >= 3.0
    elif platform == "youtube" and author_followers is not None:
        outlier_ratio = views_or_score / max(author_followers, 100)
        min_ratio = float(outlier_rules.get("youtube_views_to_subs_ratio", 3.0))
        is_outlier = outlier_ratio >= min_ratio and views_or_score >= 2000
    else:
        # Reddit is naturally democratic (unknown players posting raw clips)
        outlier_ratio = 1.0
        is_outlier = views_or_score >= 300 and safe_age <= 24.0

    # Combined score: log-scaled velocity boosted by outlier breakout multiplier
    outlier_boost = 1.0 + min(math.log1p(outlier_ratio), 4.0)
    scout_score = round(math.log1p(velocity) * 10.0 * outlier_boost, 2)
    return round(velocity, 2), round(outlier_ratio, 2), scout_score, is_outlier


# ---------------------------------------------------------------------------
# Source 1: Twitch Helix API (Free)
# ---------------------------------------------------------------------------
def fetch_twitch_clips(
    channel_id: str, queries: dict[str, Any]
) -> list[ClipCandidate]:
    client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("[Twitch] Skipped — TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET not set in .env")
        return []

    twitch_cfg = queries.get("twitch", {})
    game_name = twitch_cfg.get("game_name")
    if not game_name:
        return []

    # 1. OAuth App Token
    token_resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=20,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
    }

    # 2. Resolve game_id
    game_resp = requests.get(
        "https://api.twitch.tv/helix/games",
        headers=headers,
        params={"name": game_name},
        timeout=20,
    )
    game_resp.raise_for_status()
    games = game_resp.json().get("data", [])
    if not games:
        print(f"[Twitch] Game not found: {game_name}")
        return []
    game_id = games[0]["id"]

    # 3. Fetch top 100 clips in lookback window
    now = dt.datetime.now(dt.timezone.utc)
    lookback_hours = int(queries.get("lookback_hours", 168))
    started_at = (now - dt.timedelta(hours=lookback_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ended_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    clips_resp = requests.get(
        "https://api.twitch.tv/helix/clips",
        headers=headers,
        params={
            "game_id": game_id,
            "started_at": started_at,
            "ended_at": ended_at,
            "first": 100,
        },
        timeout=25,
    )
    clips_resp.raise_for_status()
    raw_clips = clips_resp.json().get("data", [])

    keywords = [k.lower() for k in twitch_cfg.get("title_keywords", [])]
    outlier_rules = queries.get("outlier_rules", {})
    follower_cache: dict[str, int | None] = {}
    results: list[ClipCandidate] = []

    for item in raw_clips:
        title = item.get("title", "")
        # Boost clips matching channel keywords instead of hard-dropping (many streamers use generic titles)
        keyword_hit = any(k in title.lower() for k in keywords) if keywords else False

        broadcaster_id = item.get("broadcaster_id", "")
        if broadcaster_id and broadcaster_id not in follower_cache:
            try:
                f_resp = requests.get(
                    "https://api.twitch.tv/helix/channels/followers",
                    headers=headers,
                    params={"broadcaster_id": broadcaster_id, "first": 1},
                    timeout=15,
                )
                if f_resp.status_code == 200:
                    follower_cache[broadcaster_id] = int(f_resp.json().get("total", 0))
                else:
                    follower_cache[broadcaster_id] = None
            except requests.RequestException:
                follower_cache[broadcaster_id] = None

        followers = follower_cache.get(broadcaster_id)
        created_str = item.get("created_at", "")
        created_dt = dt.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        age_hours = max((now - created_dt).total_seconds() / 3600.0, 0.25)
        views = int(item.get("view_count", 0))

        vel, ratio, score, is_outlier = compute_scores(
            views, age_hours, followers, "twitch", outlier_rules
        )
        if keyword_hit:
            score = round(score * 1.25, 2)
        results.append(
            ClipCandidate(
                platform="twitch",
                clip_id=item["id"],
                channel_id=channel_id,
                title=title,
                url=item["url"],
                author=item.get("broadcaster_name", "unknown"),
                author_followers=followers,
                views_or_score=views,
                age_hours=round(age_hours, 1),
                duration_sec=float(item.get("duration", 0)) or None,
                created_at=created_str,
                thumbnail_url=item.get("thumbnail_url", ""),
                velocity=vel,
                outlier_ratio=ratio,
                scout_score=score,
                is_small_creator_outlier=is_outlier,
            )
        )

    print(f"[Twitch] Found {len(results)} matching clips for {channel_id}")
    return results


# ---------------------------------------------------------------------------
# Source 2: Reddit (Free — Public JSON with custom User-Agent)
# ---------------------------------------------------------------------------
VIDEO_DOMAINS = (
    "v.redd.it",
    "clips.twitch.tv",
    "twitch.tv",
    "streamable.com",
    "youtu.be",
    "youtube.com",
)
MULTI_GAME_SUBS = {"livestreamfail", "gaming", "classicwow", "wow"}


def fetch_reddit_clips(
    channel_id: str, queries: dict[str, Any]
) -> list[ClipCandidate]:
    reddit_cfg = queries.get("reddit", {})
    subreddits = reddit_cfg.get("subreddits", [])
    if not subreddits:
        return []

    sort = reddit_cfg.get("sort", "top")
    time_filter = reddit_cfg.get("time_filter", "week")
    keywords = [k.lower() for k in reddit_cfg.get("keywords", [])]
    outlier_rules = queries.get("outlier_rules", {})
    user_agent = os.getenv("REDDIT_USER_AGENT", "clip_factory/0.1 (local scout)")
    headers = {"User-Agent": user_agent}
    now = dt.datetime.now(dt.timezone.utc)

    results: list[ClipCandidate] = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/{sort}.json"
        try:
            resp = requests.get(
                url,
                headers=headers,
                params={"t": time_filter, "limit": 50},
                timeout=20,
            )
            if resp.status_code != 200:
                print(f"[Reddit] r/{sub} returned HTTP {resp.status_code} — skipping")
                continue
            children = resp.json().get("data", {}).get("children", [])
        except requests.RequestException as exc:
            print(f"[Reddit] r/{sub} failed: {exc}")
            continue

        for child in children:
            post = child.get("data", {})
            post_url = post.get("url_overridden_by_dest") or post.get("url") or ""
            domain = (post.get("domain") or "").lower()
            is_video = bool(post.get("is_video")) or any(d in domain for d in VIDEO_DOMAINS)
            if not is_video:
                continue

            title = post.get("title", "")
            flair = post.get("link_flair_text") or ""
            haystack = f"{title} {flair}".lower()

            # Require keyword match on broad/multi-game subreddits
            if sub.lower() in MULTI_GAME_SUBS and keywords:
                if not any(k in haystack for k in keywords):
                    continue

            created_utc = float(post.get("created_utc", time.time()))
            created_dt = dt.datetime.fromtimestamp(created_utc, tz=dt.timezone.utc)
            age_hours = max((now - created_dt).total_seconds() / 3600.0, 0.25)
            score_val = int(post.get("score", 0))

            duration = None
            media = post.get("secure_media") or post.get("media") or {}
            if isinstance(media, dict) and "reddit_video" in media:
                duration = float(media["reddit_video"].get("duration", 0)) or None

            # Use permalink for Reddit-hosted videos so yt-dlp merges video+audio cleanly
            download_target = (
                f"https://www.reddit.com{post.get('permalink', '')}"
                if "v.redd.it" in domain or post.get("is_video")
                else post_url
            )
            thumb = post.get("thumbnail", "")
            if not thumb.startswith("http"):
                thumb = ""

            vel, ratio, scout_score, is_outlier = compute_scores(
                score_val, age_hours, None, "reddit", outlier_rules
            )
            results.append(
                ClipCandidate(
                    platform="reddit",
                    clip_id=post.get("id", ""),
                    channel_id=channel_id,
                    title=f"[r/{sub}] {title}",
                    url=download_target,
                    author=post.get("author", "unknown"),
                    author_followers=None,
                    views_or_score=score_val,
                    age_hours=round(age_hours, 1),
                    duration_sec=duration,
                    created_at=created_dt.isoformat(),
                    thumbnail_url=thumb,
                    velocity=vel,
                    outlier_ratio=ratio,
                    scout_score=scout_score,
                    is_small_creator_outlier=is_outlier,
                )
            )
        time.sleep(1.0)  # polite rate limit

    print(f"[Reddit] Found {len(results)} matching video posts for {channel_id}")
    return results


# ---------------------------------------------------------------------------
# Source 3: Apify TikTok Hashtag Actor
# ---------------------------------------------------------------------------
def select_tiktok_hashtags(queries: dict[str, Any]) -> list[str]:
    tt_cfg = queries.get("tiktok_hashtags", {})
    core = list(tt_cfg.get("daily_core", []))
    rotating = list(tt_cfg.get("rotating_niche", []))
    if rotating:
        day_idx = dt.datetime.now(dt.timezone.utc).timetuple().tm_yday
        # Pick 3 rotating niche tags per day to keep Apify spend lean
        start = (day_idx * 3) % len(rotating)
        picked = [rotating[(start + i) % len(rotating)] for i in range(min(3, len(rotating)))]
        return core + picked
    return core


def fetch_apify_tiktok_clips(
    channel_id: str, queries: dict[str, Any]
) -> list[ClipCandidate]:
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        print("[TikTok/Apify] Skipped — APIFY_TOKEN not set in .env")
        return []

    hashtags = select_tiktok_hashtags(queries)
    if not hashtags:
        return []

    actor_id = os.getenv("APIFY_TIKTOK_ACTOR", "clockworks~tiktok-hashtag-scraper")
    endpoint = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "hashtags": hashtags,
        "resultsPerPage": 15,
        "shouldDownloadVideos": True,
    }
    print(f"[TikTok/Apify] Querying hashtags: {', '.join('#' + h for h in hashtags)}")
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        items = resp.json()
    except requests.RequestException as exc:
        print(f"[TikTok/Apify] Actor call failed: {exc}")
        return []

    now = dt.datetime.now(dt.timezone.utc)
    lookback_hours = int(queries.get("lookback_hours", 168))
    outlier_rules = queries.get("outlier_rules", {})
    seen_ids: set[str] = set()
    results: list[ClipCandidate] = []

    for item in items:
        vid_id = str(item.get("id") or "")
        if not vid_id or vid_id in seen_ids:
            continue
        seen_ids.add(vid_id)

        create_ts = item.get("createTime")
        if create_ts:
            created_dt = dt.datetime.fromtimestamp(float(create_ts), tz=dt.timezone.utc)
            age_hours = max((now - created_dt).total_seconds() / 3600.0, 0.25)
            if age_hours > lookback_hours:
                continue
        else:
            created_dt = now
            age_hours = 24.0

        author_meta = item.get("authorMeta") or {}
        fans = author_meta.get("fans")
        fans_int = int(fans) if fans is not None else None
        plays = int(item.get("playCount") or item.get("diggCount") or 0)
        video_meta = item.get("videoMeta") or {}
        duration = float(video_meta.get("duration") or 0) or None

        media_urls = item.get("mediaUrls") or []
        direct_url = media_urls[0] if isinstance(media_urls, list) and media_urls else None

        vel, ratio, score, is_outlier = compute_scores(
            plays, age_hours, fans_int, "tiktok", outlier_rules
        )
        results.append(
            ClipCandidate(
                platform="tiktok",
                clip_id=vid_id,
                channel_id=channel_id,
                title=(item.get("text") or "TikTok Clip")[:140],
                url=item.get("webVideoUrl") or "",
                author=author_meta.get("name") or "unknown",
                author_followers=fans_int,
                views_or_score=plays,
                age_hours=round(age_hours, 1),
                duration_sec=duration,
                created_at=created_dt.isoformat(),
                thumbnail_url=video_meta.get("coverUrl") or "",
                velocity=vel,
                outlier_ratio=ratio,
                scout_score=score,
                is_small_creator_outlier=is_outlier,
                direct_media_url=direct_url,
            )
        )

    print(f"[TikTok/Apify] Found {len(results)} unique clips for {channel_id}")
    return results


# ---------------------------------------------------------------------------
# Source 4: YouTube Data API v3 (Free — Shorts + Outlier Ratio)
# ---------------------------------------------------------------------------
def parse_iso8601_duration(iso_dur: str) -> float | None:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_dur or "")
    if not m:
        return None
    h, mins, secs = (int(x or 0) for x in m.groups())
    total = h * 3600 + mins * 60 + secs
    return float(total) if total > 0 else None


def fetch_youtube_clips(
    channel_id: str, queries: dict[str, Any]
) -> list[ClipCandidate]:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[YouTube] Skipped — YOUTUBE_API_KEY not set in .env")
        return []

    search_terms = list(queries.get("search_queries", []))[:4]
    if not search_terms:
        return []

    now = dt.datetime.now(dt.timezone.utc)
    lookback_hours = int(queries.get("lookback_hours", 168))
    published_after = (now - dt.timedelta(hours=lookback_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    outlier_rules = queries.get("outlier_rules", {})

    video_ids: list[str] = []
    seen_vids: set[str] = set()
    for term in search_terms:
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": term,
                    "type": "video",
                    "videoDuration": "short",
                    "order": "viewCount",
                    "publishedAfter": published_after,
                    "maxResults": 10,
                    "key": api_key,
                },
                timeout=20,
            )
            if resp.status_code != 200:
                print(f"[YouTube] Search '{term}' returned HTTP {resp.status_code}")
                continue
            for item in resp.json().get("items", []):
                vid = item.get("id", {}).get("videoId")
                if vid and vid not in seen_vids:
                    seen_vids.add(vid)
                    video_ids.append(vid)
        except requests.RequestException as exc:
            print(f"[YouTube] Search '{term}' failed: {exc}")

    if not video_ids:
        print(f"[YouTube] Found 0 matching clips for {channel_id}")
        return []

    # Batch-fetch video stats + duration
    videos_data: list[dict[str, Any]] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        v_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(batch),
                "key": api_key,
            },
            timeout=20,
        )
        if v_resp.status_code == 200:
            videos_data.extend(v_resp.json().get("items", []))

    # Batch-fetch channel subscriber counts for Outlier Ratio
    channel_ids = list({v.get("snippet", {}).get("channelId", "") for v in videos_data if v.get("snippet", {}).get("channelId")})
    subs_map: dict[str, int | None] = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i : i + 50]
        c_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics", "id": ",".join(batch), "key": api_key},
            timeout=20,
        )
        if c_resp.status_code == 200:
            for ch in c_resp.json().get("items", []):
                stats = ch.get("statistics", {})
                if not stats.get("hiddenSubscriberCount") and "subscriberCount" in stats:
                    subs_map[ch["id"]] = int(stats["subscriberCount"])
                else:
                    subs_map[ch["id"]] = None

    results: list[ClipCandidate] = []
    for v in videos_data:
        vid = v["id"]
        snip = v.get("snippet", {})
        stats = v.get("statistics", {})
        details = v.get("contentDetails", {})
        views = int(stats.get("viewCount", 0))
        pub_str = snip.get("publishedAt", "")
        pub_dt = dt.datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        age_hours = max((now - pub_dt).total_seconds() / 3600.0, 0.25)
        ch_id = snip.get("channelId", "")
        subs = subs_map.get(ch_id)
        dur = parse_iso8601_duration(details.get("duration", ""))
        thumb = (snip.get("thumbnails", {}).get("high") or snip.get("thumbnails", {}).get("default") or {}).get("url", "")

        vel, ratio, score, is_outlier = compute_scores(
            views, age_hours, subs, "youtube", outlier_rules
        )
        results.append(
            ClipCandidate(
                platform="youtube",
                clip_id=vid,
                channel_id=channel_id,
                title=snip.get("title", "YouTube Clip"),
                url=f"https://www.youtube.com/watch?v={vid}",
                author=snip.get("channelTitle", "unknown"),
                author_followers=subs,
                views_or_score=views,
                age_hours=round(age_hours, 1),
                duration_sec=dur,
                created_at=pub_str,
                thumbnail_url=thumb,
                velocity=vel,
                outlier_ratio=ratio,
                scout_score=score,
                is_small_creator_outlier=is_outlier,
            )
        )

    print(f"[YouTube] Found {len(results)} matching Shorts/clips for {channel_id}")
    return results


# ---------------------------------------------------------------------------
# Downloader (yt-dlp)
# ---------------------------------------------------------------------------
def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:80]


def download_clip(clip: ClipCandidate, out_dir: Path) -> str | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{clip.platform}_{sanitize_filename(clip.clip_id)}"
    target_template = str(out_dir / f"{stem}.%(ext)s")
    expected_mp4 = out_dir / f"{stem}.mp4"
    if expected_mp4.exists():
        return expected_mp4.name

    # If Apify (or another source) provided a direct MP4 URL, download it directly first
    if clip.direct_media_url:
        try:
            apify_token = os.getenv("APIFY_TOKEN", "").strip()
            dl_headers = (
                {"Authorization": f"Bearer {apify_token}"}
                if apify_token and "api.apify.com" in clip.direct_media_url
                else {}
            )
            with requests.get(clip.direct_media_url, headers=dl_headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                with expected_mp4.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
            if expected_mp4.stat().st_size > 10_000:
                return expected_mp4.name
            expected_mp4.unlink(missing_ok=True)
        except requests.RequestException as exc:
            print(f"  [direct] Fallback to yt-dlp for {clip.platform}/{clip.clip_id}: {exc}")
            expected_mp4.unlink(missing_ok=True)

    # Prefer yt-dlp from the same Python environment if available
    yt_dlp_bin = Path(sys.executable).parent / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    cmd_bin = str(yt_dlp_bin) if yt_dlp_bin.exists() else "yt-dlp"

    fmt = (
        "best"
        if clip.platform == "tiktok"
        else "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
    )
    cmd = [
        cmd_bin,
        "--no-playlist",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "-f",
        fmt,
        "--merge-output-format",
        "mp4",
        "-o",
        target_template,
        clip.url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
    except subprocess.CalledProcessError as exc:
        err_tail = (exc.stderr or b"").decode("utf-8", errors="ignore").strip().splitlines()
        reason = err_tail[-1] if err_tail else str(exc)
        print(f"  [yt-dlp] Skipped {clip.platform}/{clip.clip_id}: {reason[:160]}")
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"  [yt-dlp] Skipped {clip.platform}/{clip.clip_id}: {exc}")
        return None

    for candidate_file in out_dir.glob(f"{stem}.*"):
        if candidate_file.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}:
            return candidate_file.name
    return None


# ---------------------------------------------------------------------------
# Local Interactive Review Sheet (review_sheet.html)
# ---------------------------------------------------------------------------
def generate_review_sheet(
    channel_id: str,
    clips: list[ClipCandidate],
    out_dir: Path,
    run_date: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "review_sheet.html"
    copyright_hint = (
        "CRITICAL: Check for GTA 6 car radio music!"
        if channel_id == "gta6"
        else "Check for streamer Spotify / background music"
    )

    cards_html = []
    for idx, c in enumerate(clips):
        esc_title = html.escape(c.title)
        esc_author = html.escape(c.author)
        esc_url = html.escape(c.url)
        followers_str = (
            f"{c.author_followers:,} followers" if c.author_followers is not None else "community post"
        )
        dur_str = f"{c.duration_sec:.1f}s" if c.duration_sec else "?"
        badge = (
            '<span class="badge outlier">BREAKOUT OUTLIER</span>'
            if c.is_small_creator_outlier
            else '<span class="badge viral">VIRAL HIT</span>'
        )

        if c.local_file:
            media_block = f"""
                <video id="vid-{idx}" preload="metadata" src="{html.escape(c.local_file)}"
                  ontimeupdate="onTime({idx})" onloadedmetadata="onMeta({idx})" onclick="togglePlay({idx})"></video>
                <div class="timeline-box">
                  <div class="tl-row">
                    <button type="button" class="mini" onclick="step({idx}, -1)">-1s</button>
                    <button type="button" class="mini" id="play-{idx}" onclick="togglePlay({idx})">▶</button>
                    <button type="button" class="mini" onclick="step({idx}, 1)">+1s</button>
                    <input type="range" class="scrubber" id="scrub-{idx}" min="0" max="100" step="0.1" value="0" oninput="seek({idx}, this.value)" />
                    <span class="timecode" id="tc-{idx}">00:00.0 / 00:00.0</span>
                  </div>
                  <div class="tag-row">
                    <button type="button" class="tag-btn" onclick="stampMarker({idx}, 'START')">[ Start</button>
                    <button type="button" class="tag-btn" onclick="stampMarker({idx}, 'END')">End ]</button>
                    <button type="button" class="tag-btn zoom" onclick="stampMarker({idx}, 'ZOOM')">+ Zoom</button>
                    <button type="button" class="tag-btn meme" onclick="stampMarker({idx}, 'MEME')">+ Meme/SFX</button>
                    <select id="meme-trig-{idx}" title="Meme trigger" style="font-size:11px;padding:2px 4px;background:#1a1d26;color:#e5e7eb;border:1px solid #374151;border-radius:4px;">
                      <option value="fail">fail</option>
                      <option value="crash">crash</option>
                      <option value="anticlimax">anticlimax</option>
                      <option value="overkill">overkill</option>
                      <option value="chase">chase</option>
                      <option value="flex">flex</option>
                      <option value="awkward_silence">awkward_silence</option>
                      <option value="betrayal">betrayal</option>
                      <option value="escape">escape</option>
                      <option value="kill">kill</option>
                      <option value="near_miss">near_miss</option>
                      <option value="cliffhanger">cliffhanger</option>
                    </select>
                    <select id="meme-hum-{idx}" title="Humor type" style="font-size:11px;padding:2px 4px;background:#1a1d26;color:#e5e7eb;border:1px solid #374151;border-radius:4px;">
                      <option value="reaction">reaction</option>
                      <option value="irony">irony</option>
                      <option value="escalation">escalation</option>
                      <option value="anticlimax">anticlimax</option>
                      <option value="absurd">absurd</option>
                      <option value="none">none</option>
                    </select>
                    <select id="meme-eng-{idx}" title="Energy 1-5" style="font-size:11px;padding:2px 4px;background:#1a1d26;color:#e5e7eb;border:1px solid #374151;border-radius:4px;">
                      <option value="1">E1</option>
                      <option value="2">E2</option>
                      <option value="3" selected>E3</option>
                      <option value="4">E4</option>
                      <option value="5">E5</option>
                    </select>
                    <span class="vol-wrap">
                      <button type="button" class="mini" id="mute-{idx}" onclick="toggleMute({idx})" title="Mute / Unmute">🔊</button>
                      <input type="range" class="vol-slider" id="vol-{idx}" min="0" max="1" step="0.05" value="1" oninput="setVol({idx}, this.value)" title="Volume" />
                    </span>
                    <button type="button" class="mini" onclick="goFullscreen({idx})" title="Fullscreen">⛶</button>
                  </div>
                </div>
            """
        elif c.platform == "tiktok" and c.clip_id:
            media_block = (
                f'<iframe class="tt-embed" src="https://www.tiktok.com/embed/v2/{html.escape(c.clip_id)}" '
                f'allow="encrypted-media;" allowfullscreen></iframe>'
                f'<a class="open-hint" href="{esc_url}" target="_blank" rel="noopener">Open on TikTok ↗</a>'
            )
        elif c.thumbnail_url:
            media_block = (
                f'<a href="{esc_url}" target="_blank" rel="noopener">'
                f'<img class="thumb" src="{html.escape(c.thumbnail_url)}" alt="preview" />'
                f'<div class="open-hint">Open source clip ↗</div></a>'
            )
        else:
            media_block = f'<a class="open-link" href="{esc_url}" target="_blank" rel="noopener">Open source clip ↗</a>'

        cards_html.append(
            f"""
            <article class="card" data-idx="{idx}">
              <div class="media">{media_block}</div>
              <div class="meta">
                <div class="badges">
                  <span class="badge platform">{html.escape(c.platform.upper())}</span>
                  {badge}
                  <span class="badge score">Score {c.scout_score}</span>
                </div>
                <h3><a href="{esc_url}" target="_blank" rel="noopener">{esc_title}</a></h3>
                <p class="stats">
                  <strong>{esc_author}</strong> ({followers_str}) ·
                  <strong>{c.views_or_score:,}</strong> views/upvotes ·
                  {c.age_hours}h ago · {dur_str} · Outlier {c.outlier_ratio}x
                </p>
                <div class="controls">
                  <label class="pick-label">
                    <input type="checkbox" class="pick-cb" data-idx="{idx}" onchange="updateSummary()" />
                    Pick for montage
                  </label>
                  <label class="music-label" title="{html.escape(copyright_hint)}">
                    <input type="checkbox" class="music-cb" data-idx="{idx}" />
                    Has copyrighted music (isolate vocals)
                  </label>
                  <label class="reject-label">
                    <input type="checkbox" class="reject-cb" data-idx="{idx}" onchange="onRejectToggle({idx})" />
                    Reject / don't want more like this
                  </label>
                </div>
                <input type="text" class="note-input" data-idx="{idx}"
                  placeholder="Directorial note (if picked) OR rejection reason (if skipped — e.g. 'already edited CapCut clip', 'spoiler cutscene', 'block creator')" />
              </div>
            </article>
            """
        )

    clips_json = json.dumps([asdict(c) for c in clips], ensure_ascii=False)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Clip Factory Review — {html.escape(channel_id)} ({run_date})</title>
  <style>
    :root {{ color-scheme: dark; --bg: #0f1115; --card: #181c24; --border: #2a3140; --text: #e8ecf3; --muted: #98a2b3; --accent: #4f8cff; --green: #22c55e; --amber: #f59e0b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ position: sticky; top: 0; z-index: 10; background: rgba(15,17,21,.95); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); padding: 14px 20px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; }}
    header h1 {{ margin: 0; font-size: 18px; }}
    .toolbar {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .counter {{ padding: 6px 12px; border-radius: 999px; background: var(--card); border: 1px solid var(--border); font-size: 13px; }}
    .counter.ready {{ border-color: var(--green); color: var(--green); }}
    button {{ cursor: pointer; border: 1px solid var(--border); background: var(--card); color: var(--text); padding: 8px 14px; border-radius: 8px; font-weight: 600; }}
    button.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    main {{ max-width: 1200px; margin: 20px auto; padding: 0 16px 60px; display: grid; gap: 16px; }}
    .card {{ display: grid; grid-template-columns: 420px 1fr; gap: 16px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }}
    @media (max-width: 900px) {{ .card {{ grid-template-columns: 1fr; }} }}
    .media video, .media .thumb {{ width: 100%; max-height: 280px; border-radius: 8px; background: #000; object-fit: contain; cursor: pointer; }}
    .media .tt-embed {{ width: 100%; height: 340px; border: 0; border-radius: 8px; background: #000; }}
    .timeline-box {{ margin-top: 8px; padding: 8px; border-radius: 8px; background: #0f1115; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 6px; }}
    .tl-row {{ display: flex; align-items: center; gap: 6px; }}
    .scrubber {{ flex: 1; accent-color: var(--accent); cursor: pointer; }}
    .timecode {{ font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: #cbd5e1; white-space: nowrap; min-width: 112px; text-align: right; }}
    .tag-row {{ display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }}
    .vol-wrap {{ display: inline-flex; align-items: center; gap: 4px; margin-left: auto; }}
    .vol-slider {{ width: 68px; accent-color: var(--accent); cursor: pointer; }}
    button.mini {{ padding: 4px 8px; font-size: 12px; border-radius: 6px; }}
    button.tag-btn {{ padding: 4px 9px; font-size: 12px; border-radius: 6px; background: #1e2430; }}
    button.tag-btn.zoom {{ border-color: #3b82f6; color: #93c5fd; }}
    button.tag-btn.meme {{ border-color: #f59e0b; color: #fcd34d; }}
    .open-hint, .open-link {{ display: inline-block; margin-top: 6px; color: var(--accent); text-decoration: none; font-size: 13px; }}
    .badges {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }}
    .badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; background: #262c3a; }}
    .badge.outlier {{ background: rgba(34,197,94,.2); color: #86efac; }}
    .badge.viral {{ background: rgba(79,140,255,.2); color: #93c5fd; }}
    .badge.score {{ background: rgba(245,158,11,.2); color: #fcd34d; }}
    h3 {{ margin: 4px 0 6px; font-size: 16px; line-height: 1.3; }}
    h3 a {{ color: var(--text); text-decoration: none; }}
    h3 a:hover {{ text-decoration: underline; }}
    .stats {{ margin: 0 0 12px; font-size: 13px; color: var(--muted); }}
    .controls {{ display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 10px; font-size: 14px; }}
    .music-label {{ color: #fca5a5; }}
    .reject-label {{ color: #94a3b8; }}
    .card.rejected {{ opacity: 0.65; border-color: #7f1d1d; }}
    .note-input {{ width: 100%; padding: 9px 11px; border-radius: 8px; border: 1px solid var(--border); background: #0f1115; color: var(--text); font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Clip Factory Review — {html.escape(channel_id)} ({run_date})</h1>
      <div style="font-size:12px;color:var(--muted)">Target: 62–70s total · {html.escape(copyright_hint)}</div>
    </div>
    <div class="toolbar">
      <span id="summary" class="counter">0 clips selected (~0s)</span>
      <button onclick="setSpeed(1.5)">1.5x Speed</button>
      <button onclick="setSpeed(1.0)">1.0x Speed</button>
      <button onclick="copySelection()">Copy JSON</button>
      <button class="primary" onclick="exportSelection()">Export curated_selection.json</button>
    </div>
  </header>
  <main>
    {''.join(cards_html) if cards_html else '<p>No new clips found in this run.</p>'}
  </main>
  <script>
    const CLIPS = {clips_json};
    const MARKERS = {{}};
    function fmtTime(sec) {{
      if (!isFinite(sec) || sec < 0) sec = 0;
      const m = Math.floor(sec / 60);
      const s = (sec % 60).toFixed(1).padStart(4, '0');
      return `${{String(m).padStart(2, '0')}}:${{s}}`;
    }}
    function onMeta(i) {{
      const v = document.getElementById(`vid-${{i}}`);
      const s = document.getElementById(`scrub-${{i}}`);
      if (v && s && isFinite(v.duration)) {{
        s.max = v.duration.toFixed(1);
        document.getElementById(`tc-${{i}}`).textContent = `${{fmtTime(v.currentTime)}} / ${{fmtTime(v.duration)}}`;
      }}
    }}
    function onTime(i) {{
      const v = document.getElementById(`vid-${{i}}`);
      const s = document.getElementById(`scrub-${{i}}`);
      if (v && s) {{
        s.value = v.currentTime;
        document.getElementById(`tc-${{i}}`).textContent = `${{fmtTime(v.currentTime)}} / ${{fmtTime(v.duration)}}`;
      }}
    }}
    function togglePlay(i) {{
      const v = document.getElementById(`vid-${{i}}`);
      const btn = document.getElementById(`play-${{i}}`);
      if (!v) return;
      if (v.paused) {{ v.play(); if (btn) btn.textContent = '⏸'; }}
      else {{ v.pause(); if (btn) btn.textContent = '▶'; }}
    }}
    function step(i, delta) {{
      const v = document.getElementById(`vid-${{i}}`);
      if (!v) return;
      v.currentTime = Math.max(0, Math.min(v.duration || 999, v.currentTime + delta));
    }}
    function seek(i, val) {{
      const v = document.getElementById(`vid-${{i}}`);
      if (v) v.currentTime = Number(val);
    }}
    function setVol(i, val) {{
      const v = document.getElementById(`vid-${{i}}`);
      const btn = document.getElementById(`mute-${{i}}`);
      if (!v) return;
      v.volume = Number(val);
      v.muted = v.volume === 0;
      if (btn) btn.textContent = v.muted ? '🔇' : '🔊';
    }}
    function toggleMute(i) {{
      const v = document.getElementById(`vid-${{i}}`);
      const btn = document.getElementById(`mute-${{i}}`);
      const slider = document.getElementById(`vol-${{i}}`);
      if (!v) return;
      v.muted = !v.muted;
      if (btn) btn.textContent = v.muted ? '🔇' : '🔊';
      if (slider) slider.value = v.muted ? 0 : (v.volume || 1);
    }}
    function goFullscreen(i) {{
      const v = document.getElementById(`vid-${{i}}`);
      if (v && v.requestFullscreen) v.requestFullscreen();
    }}
    function stampMarker(i, kind) {{
      const v = document.getElementById(`vid-${{i}}`);
      if (!v) return;
      const t = Number(v.currentTime.toFixed(1));
      if (!MARKERS[i]) MARKERS[i] = [];
      const noteEl = document.querySelector(`.note-input[data-idx="${{i}}"]`);
      if (kind === 'MEME') {{
        const trigger = document.getElementById(`meme-trig-${{i}}`)?.value || 'fail';
        const humor_type = document.getElementById(`meme-hum-${{i}}`)?.value || 'reaction';
        const energy = Number(document.getElementById(`meme-eng-${{i}}`)?.value || 3);
        MARKERS[i].push({{ type: 'MEME', sec: t, trigger, humor_type, energy, note: (noteEl?.value || '').trim() }});
      }} else {{
        MARKERS[i].push({{ type: kind, sec: t }});
      }}
      const tag = `${{kind}}@${{fmtTime(t)}}`;
      noteEl.value = noteEl.value ? `${{noteEl.value}}, ${{tag}}` : tag;
      const cb = document.querySelector(`.pick-cb[data-idx="${{i}}"]`);
      if (cb && !cb.checked) {{ cb.checked = true; updateSummary(); }}
    }}
    function setSpeed(rate) {{
      document.querySelectorAll('video').forEach(v => v.playbackRate = rate);
    }}
    function onRejectToggle(i) {{
      const rej = document.querySelector(`.reject-cb[data-idx="${{i}}"]`);
      const pick = document.querySelector(`.pick-cb[data-idx="${{i}}"]`);
      const card = document.querySelector(`.card[data-idx="${{i}}"]`);
      if (rej && rej.checked && pick) {{ pick.checked = false; }}
      if (card) {{ card.classList.toggle('rejected', Boolean(rej && rej.checked)); }}
      updateSummary();
    }}
    function gatherSelection() {{
      const picked = [];
      const rejected = [];
      CLIPS.forEach((clip, i) => {{
        const isPicked = document.querySelector(`.pick-cb[data-idx="${{i}}"]`)?.checked || false;
        const isRejected = document.querySelector(`.reject-cb[data-idx="${{i}}"]`)?.checked || false;
        const music = document.querySelector(`.music-cb[data-idx="${{i}}"]`)?.checked || false;
        const note = document.querySelector(`.note-input[data-idx="${{i}}"]`)?.value.trim() || '';
        if (isPicked) {{
          picked.push({{ ...clip, isolate_vocals: music, directorial_note: note, markers: MARKERS[i] || [] }});
        }} else if (isRejected || note.length > 0) {{
          rejected.push({{
            platform: clip.platform,
            clip_id: clip.clip_id,
            author: clip.author,
            title: clip.title,
            url: clip.url,
            rejected: true,
            feedback_note: note || 'rejected without note'
          }});
        }}
      }});
      return {{
        channel_id: "{html.escape(channel_id)}",
        run_date: "{run_date}",
        exported_at: new Date().toISOString(),
        selected_clips: picked,
        rejected_feedback: rejected
      }};
    }}
    function updateSummary() {{
      const sel = gatherSelection().selected_clips;
      const est = sel.reduce((acc, c) => acc + (c.duration_sec || 16), 0);
      const el = document.getElementById('summary');
      el.textContent = `${{sel.length}} clips selected (~${{Math.round(est)}}s raw)`;
      el.classList.toggle('ready', est >= 62);
    }}
    function exportSelection() {{
      const payload = JSON.stringify(gatherSelection(), null, 2);
      const blob = new Blob([payload], {{ type: 'application/json' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'curated_selection_{html.escape(channel_id)}_{run_date}.json';
      a.click();
    }}
    async function copySelection() {{
      await navigator.clipboard.writeText(JSON.stringify(gatherSelection(), null, 2));
      alert('Copied curated_selection JSON to clipboard!');
    }}
  </script>
</body>
</html>
"""
    html_path.write_text(page, encoding="utf-8")
    return html_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Clip Factory — Daily Viral & Outlier Clip Scout (V1)")
    parser.add_argument("--channel", required=True, choices=["wow_forever", "gta6"], help="Channel profile to scout")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Optional standalone channel project directory containing config/ and workspace/",
    )
    parser.add_argument("--limit", type=int, default=15, help="Max top candidates to keep & download")
    parser.add_argument(
        "--sources",
        default="twitch,youtube,tiktok,reddit",
        help="Comma-separated sources to query (twitch,youtube,tiktok,reddit)",
    )
    parser.add_argument("--no-download", action="store_true", help="Skip yt-dlp downloads (links + review sheet only)")
    parser.add_argument("--include-seen", action="store_true", help="Include clips already stored in SQLite")
    args = parser.parse_args()

    # Load .env from project dir if present, otherwise shared clip_factory/.env
    if args.project_dir and (args.project_dir / ".env").exists():
        load_dotenv(args.project_dir / ".env")
    load_dotenv(ROOT_DIR / ".env")

    if args.project_dir:
        project_root = args.project_dir.resolve()
        queries_path = project_root / "config" / "scout_queries.json"
        workspace_dir = project_root / "workspace"
    else:
        queries_path = ROOT_DIR / "config" / args.channel / "scout_queries.json"
        workspace_dir = ROOT_DIR / "workspace" / args.channel

    queries = load_json(queries_path)
    sources = {s.strip().lower() for s in args.sources.split(",") if s.strip()}

    db_conn = init_db(workspace_dir / "seen_clips.sqlite")

    all_candidates: list[ClipCandidate] = []
    if "twitch" in sources:
        all_candidates.extend(fetch_twitch_clips(args.channel, queries))
    if "youtube" in sources:
        all_candidates.extend(fetch_youtube_clips(args.channel, queries))
    if "reddit" in sources:
        all_candidates.extend(fetch_reddit_clips(args.channel, queries))
    if "tiktok" in sources:
        all_candidates.extend(fetch_apify_tiktok_clips(args.channel, queries))

    # Deduplicate in-memory and against SQLite
    unique: dict[tuple[str, str], ClipCandidate] = {}
    for c in all_candidates:
        key = (c.platform, c.clip_id)
        if key in unique:
            continue
        if not args.include_seen and is_seen(db_conn, c.platform, c.clip_id):
            continue
        unique[key] = c

    # Balanced round-robin selection across platforms so high-view TikToks
    # don't crowd out Twitch & YouTube Shorts candidates
    by_platform: dict[str, list[ClipCandidate]] = {}
    for c in sorted(unique.values(), key=lambda x: x.scout_score, reverse=True):
        by_platform.setdefault(c.platform, []).append(c)

    ranked: list[ClipCandidate] = []
    platform_order = [p for p in ("twitch", "youtube", "tiktok", "reddit") if p in by_platform]
    while len(ranked) < args.limit and platform_order:
        next_order = []
        for p in platform_order:
            bucket = by_platform[p]
            if bucket and len(ranked) < args.limit:
                ranked.append(bucket.pop(0))
            if bucket:
                next_order.append(p)
        platform_order = next_order

    run_date = dt.datetime.now().strftime("%Y-%m-%d")
    inbox_dir = workspace_dir / "01_inbox_raw" / run_date
    inbox_dir.mkdir(parents=True, exist_ok=True)

    if not args.no_download and ranked:
        print(f"[Downloader] Fetching top {len(ranked)} clips into {inbox_dir} ...")
        for c in ranked:
            c.local_file = download_clip(c, inbox_dir)

    for c in ranked:
        mark_seen(db_conn, c)

    # Save raw JSON manifest alongside review_sheet.html
    manifest_path = inbox_dir / "scout_candidates.json"
    manifest_path.write_text(
        json.dumps([asdict(c) for c in ranked], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    html_path = generate_review_sheet(args.channel, ranked, inbox_dir, run_date)

    print(f"\nDone! Ranked {len(ranked)} candidates for '{args.channel}'.")
    print(f"  Manifest:     {manifest_path}")
    print(f"  Review sheet: {html_path}")
    print("Next: open review_sheet.html, pick 3-5 clips, add directorial notes, and Export curated_selection.json.")


if __name__ == "__main__":
    main()
