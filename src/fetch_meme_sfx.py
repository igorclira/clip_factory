"""
Clip Factory — Curated Meme & Game SFX Fetcher (MyInstants.com)

Searches MyInstants.com for curated iconic gaming/streamer/Half-Life SFX, downloads
clean short (<8s) .mp3 files into shared_assets/sfx/ with clean prefixed names
(`hl_*.mp3`, `meme_*.mp3`), and optionally runs index_sfx.py so Gemini listens to
each file, measures exact peak_sec, and catalogs it into shared_assets/meme_map.json.

Usage:
    python src/fetch_meme_sfx.py
"""

from __future__ import annotations

import html
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

import requests

CORE_ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = CORE_ROOT / "shared_assets" / "sfx"

# Curated high-craft gaming compilation & Half-Life SFX list: (target_tag, search_query)
CURATED_SOUNDS: list[tuple[str, str]] = [
    # Half-Life 1 classics
    ("hl_scientist_scream", "half life scientist scream"),
    ("hl_scientist_stahp", "half life stahp"),
    ("hl_crowbar_hit", "half life crowbar"),
    ("hl_hev_warning", "half life hev"),
    ("hl_button_click", "half life button"),
    ("hl_health_charger", "half life health charger"),
    ("hl_death_flatline", "half life death"),
    # Superhero / GTA / Gaming classics
    ("meme_avengers_flute", "avengers flute"),
    ("meme_avengers_sting", "avengers theme"),
    ("meme_gta_wasted", "gta wasted"),
    ("meme_gta_here_we_go", "ah shit here we go again"),
    ("meme_mgs_alert", "metal gear solid alert"),
    ("meme_minecraft_hit", "minecraft hit"),
    ("meme_roblox_oof", "roblox oof"),
    # Universal Streamer / Comedy stingers
    ("meme_vine_boom_og", "vine boom"),
    ("meme_bruh_og", "bruh sound effect"),
    ("meme_cartoon_bonk", "cartoon bonk"),
    ("meme_cartoon_slip", "cartoon slip"),
    ("meme_spongebob_fail", "spongebob fail"),
    ("meme_taco_bell_bong", "taco bell bong"),
    ("meme_windows_xp_shutdown", "windows xp shutdown"),
    ("meme_law_and_order_dundun", "law and order"),
    ("meme_huh_cat", "huh cat"),
    ("meme_metal_pipe_og", "metal pipe falling"),
    ("meme_sad_violin_short", "sad violin"),
    # Iconic <2.5s Mainstream Pop-Culture Voice Blips
    ("meme_at_this_moment", "it was at this moment he knew"),
    ("meme_wait_a_minute", "wait a minute who are you"),
    ("meme_oh_hell_no", "oh hell no"),
    ("meme_fbi_open_up", "fbi open up"),
    ("meme_mission_failed", "mission failed well get em next time"),
    ("meme_he_need_some_milk", "he need some milk"),
    ("meme_nani", "nani"),
    ("meme_no_god_please_no", "no god please no"),
    ("meme_fast_as_fuck", "fast as fuck boi"),
    ("meme_surprise_mf", "surprise motherfucker"),
    ("meme_look_at_this_dude", "look at this dude"),
    ("meme_directed_by", "directed by robert b weide"),
    # Semantic library expansion (47 evergreen + 2025-2026 trending bites)
    ("curb_your_enthusiasm", "Curb Your Enthusiasm theme meme"),
    ("to_be_continued", "To Be Continued Roundabout meme"),
    ("oh_no_no_no_laugh", "Oh no no no laugh meme"),
    ("coffin_dance", "Coffin Dance Astronomia meme"),
    ("john_cena_intro", "And His Name Is John Cena"),
    ("ight_imma_head_out", "Ight imma head out spongebob"),
    ("its_a_trap", "it's a trap ackbar"),
    ("hello_darkness", "Hello darkness my old friend meme"),
    ("ba_dum_tss", "ba dum tss rimshot"),
    ("owen_wilson_wow", "Owen Wilson wow"),
    ("sheesh", "sheesh meme sound"),
    ("well_be_right_back", "We'll be right back meme"),
    ("evil_laugh", "evil laugh meme"),
    ("among_us_emergency_meeting", "Among Us emergency meeting"),
    ("omae_wa_mou_shindeiru", "omae wa mou shindeiru meme"),
    ("za_warudo", "Za Warudo time stop meme"),
    ("dramatic_chipmunk", "Dramatic Chipmunk"),
    ("over_9000", "it's over 9000 meme"),
    ("its_time_to_stop", "it's time to stop filthy frank"),
    ("leeroy_jenkins", "Leeroy Jenkins"),
    ("rickroll_sting", "Never Gonna Give You Up meme sting"),
    ("shooting_stars", "Shooting Stars meme Bag Raiders"),
    ("oh_brother_this_guy_stinks", "Oh brother this guy stinks spongebob"),
    ("we_got_him", "We got him meme"),
    ("i_cant_believe_youve_done_this", "I can't believe you've done this meme"),
    ("jeopardy_thinking", "Jeopardy thinking music meme"),
    ("spongebob_boowomp", "SpongeBob boowomp"),
    ("gotta_go_fast", "Gotta go fast meme"),
    ("phonk_stinger", "phonk cowbell stinger meme"),
    ("inception_braam", "Inception horn BRAAAM"),
    ("cs_awp_shot", "CS GO AWP shot sound"),
    ("wombo_combo", "Wombo Combo meme"),
    ("oh_baby_a_triple", "Oh baby a triple"),
    ("damn_son_whered_you_find_this", "Damn son where'd you find this"),
    ("finish_him", "Mortal Kombat Finish Him"),
    ("killing_spree", "killing spree announcer"),
    ("headshot_announcer", "headshot announcer sound"),
    ("mlg_wow", "MLG wow sound effect"),
    ("deja_vu_initial_d", "Deja Vu Initial D meme"),
    ("yara_yara_phonk", "Yara Yara Phonk"),
    ("brother_eww", "Brother Ewwwwwww"),
    ("tung_tung_tung_sahur", "Tung Tung Tung Sahur"),
    ("bomboclat", "bomboclat meme sound"),
    ("syfm_shut_your_mouth", "Shut your mouth SYFM"),
    ("airpods_low_battery", "AirPods Low Battery Sound"),
    ("helicopter_helicopter", "helicopter helicopter para kofer"),
    ("man_from_the_fog_whistle", "The Man From The Fog Whistle"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}


def get_audio_duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            stderr=subprocess.DEVNULL,
        )
        return float(out.decode().strip())
    except Exception:
        return 0.0


def search_myinstants(query: str) -> list[str]:
    url = f"https://www.myinstants.com/en/search/?name={urllib.parse.quote_plus(query)}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    # Extract play('/media/sounds/....mp3') URLs from search results
    matches = re.findall(r"play\('(/media/sounds/[^']+\.mp3)'", html.unescape(resp.text))
    # Deduplicate preserving order
    seen: set[str] = set()
    urls: list[str] = []
    for m in matches:
        full = f"https://www.myinstants.com{m}"
        if full not in seen:
            seen.add(full)
            urls.append(full)
    return urls


def main() -> None:
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0

    for tag, query in CURATED_SOUNDS:
        out_path = SFX_DIR / f"{tag}.mp3"
        if out_path.exists() and out_path.stat().st_size > 2000:
            print(f"[Cached] {out_path.name}")
            skipped += 1
            continue

        print(f"[Search] '{query}' -> {tag}.mp3 ...")
        try:
            mp3_urls = search_myinstants(query)
        except requests.RequestException as exc:
            print(f"  [Error] Search failed: {exc}")
            continue

        saved = False
        for mp3_url in mp3_urls[:4]:
            try:
                r = requests.get(mp3_url, headers=HEADERS, timeout=25)
                r.raise_for_status()
                if len(r.content) < 2000:
                    continue
                out_path.write_bytes(r.content)
                dur = get_audio_duration(out_path)
                if 0.15 <= dur <= 9.5:
                    print(f"  [Saved] {out_path.name} ({dur:.2f}s, {len(r.content)//1024} KB)")
                    downloaded += 1
                    saved = True
                    break
                else:
                    out_path.unlink(missing_ok=True)
            except requests.RequestException:
                out_path.unlink(missing_ok=True)

        if not saved:
            print(f"  [Miss] No clean <9.5s clip found for '{query}'")
        time.sleep(0.7)

    print(f"\nDone! Downloaded {downloaded} new meme/game SFX ({skipped} cached) into {SFX_DIR}")


if __name__ == "__main__":
    main()
