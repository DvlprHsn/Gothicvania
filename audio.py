"""
Audio: procedural fallback SFX synthesis + music loader.
"""

from __future__ import annotations

import array
import os
import pygame

from config import MUSIC_VOLUME, MUSIC_CANDIDATES, SFX_FILES, SFX_DIR


def _make_sound(freq_start, freq_end, duration, volume=0.4,
                sample_rate=22050) -> pygame.mixer.Sound:
    """Square-wave beep with linear freq sweep + quadratic decay."""
    n = int(sample_rate * duration)
    buf = array.array("h")
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase = (i * freq / sample_rate) % 1.0
        val = 1.0 if phase < 0.5 else -1.0
        env = (1.0 - t) ** 2
        buf.append(int(val * env * volume * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def build_sfx(data_dir: str) -> dict:
    """Load real SFX if present, otherwise synthesize procedural fallbacks."""
    sfx_dir = os.path.join(data_dir, SFX_DIR)
    sounds: dict = {}

    for name, (filename, fallback) in SFX_FILES.items():
        path = os.path.join(sfx_dir, filename)
        loaded = False
        if os.path.exists(path):
            try:
                s = pygame.mixer.Sound(path)
                s.set_volume(0.6)
                sounds[name] = s
                print(f"[SFX] Loaded {filename}")
                loaded = True
            except Exception as e:
                print(f"[SFX] Failed to load {filename}: {e}")
        if not loaded:
            fs, fe, dur, vol = fallback
            sounds[name] = _make_sound(fs, fe, dur, vol)
            print(f"[SFX] {filename} not found — using procedural {name}")

    return sounds


def build_music(data_dir: str):
    """Find and start looping background music. Returns the path or None."""
    for rel in MUSIC_CANDIDATES:
        path = os.path.join(data_dir, rel)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(MUSIC_VOLUME)
                pygame.mixer.music.play(-1)
                print(f"[Music] Playing {os.path.basename(path)} (looping)")
                return path
            except Exception as e:
                print(f"[Music] Failed to load {path}: {e}")
    print("[Music] No music file found — running silently")
    return None


def toggle_mute(music_playing: bool) -> None:
    if not music_playing:
        return
    if pygame.mixer.music.get_volume() > 0.0:
        pygame.mixer.music.set_volume(0.0)
        print("[Music] Muted")
    else:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        print("[Music] Unmuted")


def restart_music(music_playing: bool) -> None:
    if not music_playing:
        return
    try:
        pygame.mixer.music.play(-1)
        if pygame.mixer.music.get_volume() <= 0.0:
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass