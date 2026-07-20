"""Encoding quality presets for Phase 6.2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EncodingProfile:
    """Resolution and bitrate preset."""

    profile_id: str
    display_name: str
    width: int
    height: int
    bitrate_mbps: float
    mp4_crf: int = 18
    webm_crf: int = 30


PROFILES: dict[str, EncodingProfile] = {
    "preview": EncodingProfile(
        profile_id="preview",
        display_name="Preview",
        width=1280,
        height=720,
        bitrate_mbps=2.0,
        mp4_crf=23,
        webm_crf=35,
    ),
    "standard": EncodingProfile(
        profile_id="standard",
        display_name="Standard",
        width=1920,
        height=1080,
        bitrate_mbps=6.0,
        mp4_crf=18,
        webm_crf=30,
    ),
    "high_quality": EncodingProfile(
        profile_id="high_quality",
        display_name="High Quality",
        width=2560,
        height=1440,
        bitrate_mbps=12.0,
        mp4_crf=16,
        webm_crf=28,
    ),
    "4k": EncodingProfile(
        profile_id="4k",
        display_name="4K (Future)",
        width=3840,
        height=2160,
        bitrate_mbps=24.0,
        mp4_crf=14,
        webm_crf=26,
    ),
}


def get_profile(profile_id: str | None = None) -> EncodingProfile:
    if not profile_id:
        return PROFILES["preview"]
    key = profile_id.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "high": "high_quality",
        "hq": "high_quality",
        "std": "standard",
    }
    key = aliases.get(key, key)
    return PROFILES.get(key, PROFILES["preview"])
