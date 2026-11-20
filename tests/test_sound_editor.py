"""Unit tests for clip_factory sound_editor guardrails, timing, and compact roster filtering (no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
SHARED_DIR = Path(__file__).resolve().parent.parent / "shared_assets"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import sound_editor  # noqa: E402


@pytest.fixture(scope="module")
def real_sound_lib() -> list[dict]:
    return json.loads((SHARED_DIR / "sound_library.json").read_text(encoding="utf-8"))


@pytest.fixture
def sample_sound_by_file() -> dict[str, dict]:
    return {
        "bruh.mp3": {
            "file": "bruh.mp3",
            "id": "bruh",
            "category": "meme",
            "length_s": 0.82,
            "peak_sec": 0.14,
            "onset_sec": 0.04,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "after_impact",
            "copyright_risk": "low",
            "dedupe_group": "deadpan_disbelief",
            "curated_semantic": True,
        },
        "fah_perfect_sync.mp3": {
            "file": "fah_perfect_sync.mp3",
            "id": "faah",
            "category": "meme",
            "length_s": 1.6,
            "peak_sec": 0.2,
            "onset_sec": 0.05,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "on_impact",
            "copyright_risk": "low",
            "dedupe_group": "deadpan_disbelief",
            "curated_semantic": True,
        },
        "my_leg_spongebob_fish_clear.mp3": {
            "file": "my_leg_spongebob_fish_clear.mp3",
            "id": "spongebob_my_leg",
            "category": "meme",
            "length_s": 2.13,
            "peak_sec": 0.38,
            "onset_sec": 0.31,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "after_impact",
            "copyright_risk": "medium",
            "dedupe_group": "scream_pain",
            "curated_semantic": True,
        },
        "emotional_damage_meme.mp3": {
            "file": "emotional_damage_meme.mp3",
            "id": "emotional_damage",
            "category": "meme",
            "length_s": 3.32,
            "peak_sec": 1.5,
            "onset_sec": 0.5,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "after_impact",
            "copyright_risk": "medium",
            "dedupe_group": "humiliation",
            "curated_semantic": True,
        },
        "tuco_get_out.mp3": {
            "file": "tuco_get_out.mp3",
            "id": "tuco_get_out",
            "category": "meme",
            "length_s": 1.4,
            "peak_sec": 0.2,
            "onset_sec": 0.05,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "on_impact",
            "copyright_risk": "medium",
            "dedupe_group": "angry_eject",
            "curated_semantic": True,
        },
        "meme_directed_by_2s.mp3": {
            "file": "meme_directed_by_2s.mp3",
            "id": "directed_by_robert_b_weide",
            "category": "meme",
            "length_s": 2.35,
            "peak_sec": 0.5,
            "onset_sec": 0.01,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "end_card",
            "copyright_risk": "high",
            "dedupe_group": "curb_end",
            "curated_semantic": True,
        },
        "meme_gta_wasted.mp3": {
            "file": "meme_gta_wasted.mp3",
            "id": "gta_wasted",
            "category": "meme",
            "length_s": 1.8,
            "peak_sec": 0.1,
            "onset_sec": 0.05,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "on_impact",
            "copyright_risk": "medium",
            "dedupe_group": "gta_native",
            "gta_native": True,
            "curated_semantic": True,
        },
        "riser_whoosh.wav": {
            "file": "riser_whoosh.wav",
            "id": "cinematic_riser",
            "category": "transition",
            "length_s": 2.0,
            "peak_sec": 0.1,
            "onset_sec": 0.05,
            "align_mode": "peak",
            "montage_mode": "both",
            "placement": "before_moment",
            "copyright_risk": "low",
            "dedupe_group": "riser_build",
            "curated_semantic": True,
        },
        "curb_bed.mp3": {
            "file": "curb_bed.mp3",
            "id": "curb_your_enthusiasm",
            "category": "meme",
            "length_s": 7.0,
            "peak_sec": 0.2,
            "onset_sec": 0.05,
            "align_mode": "onset",
            "montage_mode": "funny",
            "placement": "bed",
            "copyright_risk": "high",
            "dedupe_group": "curb_end",
            "curated_semantic": True,
        },
    }


def _make_plan(events: list[sound_editor.SoundEvent], mode: str = "funny") -> sound_editor.SoundPlan:
    return sound_editor.SoundPlan(
        montage_mode=mode,  # type: ignore[arg-type]
        music=sound_editor.MusicPlan(file="", start_s=0.0, gain_db=-18.0, duck_under_game_audio_db=-10.0, cut_points=[]),
        events=events,
        final_mix=sound_editor.FinalMix(),
    )


def test_unknown_file_dropped_and_alias_resolved(sample_sound_by_file):
    plan = _make_plan([
        sound_editor.SoundEvent(t=5.0, file="totally_fake.mp3", category="meme", reason="fake"),
        sound_editor.SoundEvent(t=10.0, file="spongebob_my_leg.mp3", category="meme", placement="after_impact", trigger="crash", reason="alias"),
    ])
    res = sound_editor.enforce_rules_and_align(plan, sample_sound_by_file, {}, set(), total_duration=30.0)
    assert [e["file"] for e in res["events"]] == ["my_leg_spongebob_fish_clear.mp3"]
    assert res["events"][0]["max_duration_s"] <= 2.4


def test_dedupe_group_and_5s_spacing(sample_sound_by_file):
    plan = _make_plan([
        sound_editor.SoundEvent(t=5.0, file="bruh.mp3", category="meme", reason="first"),
        sound_editor.SoundEvent(t=12.0, file="fah_perfect_sync.mp3", category="meme", reason="same dedupe_group"),
        sound_editor.SoundEvent(t=8.0, file="tuco_get_out.mp3", category="meme", reason="too close (<5s)"),
        sound_editor.SoundEvent(t=18.0, file="tuco_get_out.mp3", category="meme", reason="ok spacing"),
    ])
    res = sound_editor.enforce_rules_and_align(plan, sample_sound_by_file, {}, set(), total_duration=40.0)
    assert [e["file"] for e in res["events"]] == ["bruh.mp3", "tuco_get_out.mp3"]


def test_gta_native_skipped_unless_allowed(sample_sound_by_file):
    plan = _make_plan([
        sound_editor.SoundEvent(t=10.0, file="meme_gta_wasted.mp3", category="meme", reason="gta"),
    ])
    res_default = sound_editor.enforce_rules_and_align(plan, sample_sound_by_file, {}, set(), total_duration=30.0)
    assert res_default["events"] == []

    res_allowed = sound_editor.enforce_rules_and_align(
        plan, sample_sound_by_file, {}, set(), total_duration=30.0, allow_gta_native=True
    )
    assert [e["file"] for e in res_allowed["events"]] == ["meme_gta_wasted.mp3"]


def test_mode_meme_caps_funny_action_hybrid(sample_sound_by_file):
    events = [
        sound_editor.SoundEvent(t=5.0, file="bruh.mp3", category="meme", reason="m1"),
        sound_editor.SoundEvent(t=15.0, file="tuco_get_out.mp3", category="meme", reason="m2"),
        sound_editor.SoundEvent(t=25.0, file="my_leg_spongebob_fish_clear.mp3", category="meme", reason="m3"),
        sound_editor.SoundEvent(t=35.0, file="emotional_damage_meme.mp3", category="meme", reason="m4"),
    ]
    res_action = sound_editor.enforce_rules_and_align(
        _make_plan(events, mode="action"), sample_sound_by_file, {}, set(), total_duration=40.0, montage_mode="action"
    )
    assert len(res_action["events"]) == 1

    res_funny = sound_editor.enforce_rules_and_align(
        _make_plan(events, mode="funny"), sample_sound_by_file, {}, set(), total_duration=40.0, montage_mode="funny"
    )
    assert len(res_funny["events"]) == 4


def test_hybrid_meme_before_turn_dropped(sample_sound_by_file):
    summaries = [{"beat_tags": [{"t": 40.0, "trigger": "fail"}]}]
    plan = _make_plan([
        sound_editor.SoundEvent(t=20.0, file="bruh.mp3", category="meme", reason="too early in hybrid"),
        sound_editor.SoundEvent(t=41.0, file="tuco_get_out.mp3", category="meme", reason="after turn"),
    ], mode="hybrid")
    res = sound_editor.enforce_rules_and_align(
        plan, sample_sound_by_file, {}, set(), total_duration=50.0, montage_mode="hybrid", segment_summaries=summaries
    )
    assert [e["file"] for e in res["events"]] == ["tuco_get_out.mp3"]


def test_after_impact_before_moment_and_duck_windows(sample_sound_by_file):
    plan = _make_plan([
        sound_editor.SoundEvent(t=10.0, file="riser_whoosh.wav", category="transition", placement="before_moment", reason="riser"),
        sound_editor.SoundEvent(t=12.0, file="emotional_damage_meme.mp3", category="meme", placement="after_impact", trigger="fail", reason="meme"),
    ])
    res = sound_editor.enforce_rules_and_align(plan, sample_sound_by_file, {}, set(), total_duration=30.0)
    riser_ev, meme_ev = res["events"]
    # Riser (length_s=2.0, peak_sec=0.1) leads in ~2.0s before t=10.0
    assert riser_ev["play_at_s"] == pytest.approx(10.0 - 2.0 - 0.1 - 0.033, abs=0.01)
    # after_impact shifts +0.25s then subtracts onset_sec=0.5 -> 11.75s, capped at 2.4s
    assert meme_ev["play_at_s"] == pytest.approx(12.0 + 0.25 - 0.5, abs=0.01)
    assert meme_ev["max_duration_s"] == 2.4
    # Game duck window covers the meme bite and auto-adds a 0.35s pre-meme music cut point
    assert len(res["game_duck_windows"]) == 1
    assert res["game_duck_windows"][0]["start_s"] == meme_ev["play_at_s"]
    assert res["game_duck_windows"][0]["db"] == -10
    assert any(cp["start_s"] == pytest.approx(11.65, abs=0.01) and cp["end_s"] == pytest.approx(12.0, abs=0.01) for cp in res["music"]["cut_points"])


def test_tail_cutoff_drops_truncated_ending_meme(sample_sound_by_file):
    plan = _make_plan([
        sound_editor.SoundEvent(t=81.07, file="meme_directed_by_2s.mp3", category="meme", placement="end_card", reason="tail"),
    ])
    res = sound_editor.enforce_rules_and_align(plan, sample_sound_by_file, {}, set(), total_duration=81.42)
    assert res["events"] == []


def test_extract_clip_events_playback_rate_overlap_and_new_cues():
    props = {
        "fps": 30,
        "segments": [
            {
                "id": "seg_1",
                "author": "alice",
                "startSec": 0.0,
                "endSec": 5.0,
                "playbackRate": 0.5,  # output duration = 10.0s
                "freezes": [{"atSec": 4.0, "durationSec": 1.2}],
                "silences": [{"startSec": 3.5, "endSec": 3.9}],
                "beatTags": [{"atSec": 5.0, "trigger": "fail", "humor_type": "irony", "energy": 3, "note": "wipes out"}],
            },
            {
                "id": "seg_2",
                "author": "bob",
                "startSec": 0.0,
                "endSec": 5.0,
                "transitionIn": "slide",  # 8 frames / 30fps = 0.2667s overlap -> starts at 9.733s
            },
        ],
    }
    total_dur, events, _ = sound_editor.extract_clip_events(props)
    assert total_dur == pytest.approx(14.73, abs=0.02)
    types_found = {e["type"] for e in events}
    assert {"hook", "freeze", "silence", "beat_tag", "cut", "ending"}.issubset(types_found)


def test_compact_filter_includes_long_bed_memes(sample_sound_by_file, real_sound_lib):
    compact_mock = sound_editor.build_compact_sounds(list(sample_sound_by_file.values()), montage_mode="funny")
    ids_mock = {s["id"] for s in compact_mock}
    assert "curb_your_enthusiasm" in ids_mock
    assert "gta_wasted" not in ids_mock

    compact_real = sound_editor.build_compact_sounds(real_sound_lib, montage_mode="hybrid")
    ids_real = {s["id"] for s in compact_real}
    for expected in ("sad_violin", "cricket_chirps", "price_is_right_losing_horn", "baby_laughing", "prowler_sound", "run_vine"):
        assert expected in ids_real, f"Expected {expected} in compact_sounds"
