"""
Asset loading — atlas, background, ground prop, splash, icon.
Everything loads once at startup and is cached.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import pygame

from config import (
    WINDOW_W, WINDOW_H, GROUND_Y, BACKGROUND_ZOOM,
    ATLAS_FILE, SPRITE_BOXES_FILE, BACKGROUND_FILE,
    SPLASH_FILE, ICON_FILE, GROUND_PROP_FILE,
)


@dataclass
class FighterAssets:
    atlas: pygame.Surface
    data: dict


@dataclass
class GroundAssets:
    """Single ground prop image, tiled across the world."""
    image: Optional[pygame.Surface]   # None if missing → draw a fallback strip
    tile_w: int = 0
    tile_h: int = 0


# ---------------------------------------------------------------------------
# Fighter atlas + hitbox json
# ---------------------------------------------------------------------------
def load_fighter_assets(data_dir: str) -> FighterAssets:
    atlas_path = os.path.join(data_dir, ATLAS_FILE)
    json_path = os.path.join(data_dir, SPRITE_BOXES_FILE)

    if not os.path.exists(atlas_path):
        raise FileNotFoundError(f"atlas.png not found at {atlas_path}")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"sprite_boxes.json not found at {json_path}")

    atlas = pygame.image.load(atlas_path).convert_alpha()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[Atlas] Loaded {atlas.get_size()}")
    return FighterAssets(atlas=atlas, data=data)


# ---------------------------------------------------------------------------
# Ground prop — a single tiling image
# ---------------------------------------------------------------------------
def load_ground_prop(data_dir: str) -> GroundAssets:
    path = os.path.join(data_dir, GROUND_PROP_FILE)
    if not os.path.exists(path):
        print(f"[Ground] {GROUND_PROP_FILE} not found — using fallback strip")
        return GroundAssets(image=None)

    try:
        img = pygame.image.load(path).convert_alpha()
        print(f"[Ground] Loaded ground_prop.png ({img.get_width()}x{img.get_height()})")
        return GroundAssets(image=img, tile_w=img.get_width(), tile_h=img.get_height())
    except Exception as e:
        print(f"[Ground] Failed to load ground_prop.png: {e}")
        return GroundAssets(image=None)


# ---------------------------------------------------------------------------
# Background — a single wide image, scaled to fit the world
# ---------------------------------------------------------------------------
class ScrollingBackground:
    """
    Scrolling background using a single image.
    Ground is drawn separately from the ground prop.
    """

    def __init__(self, data_dir: str) -> None:
        self.image: Optional[pygame.Surface] = None
        self.world_width: float = WINDOW_W
        self.ground: GroundAssets = load_ground_prop(data_dir)

        path = os.path.join(data_dir, BACKGROUND_FILE)
        if not os.path.exists(path):
            print(f"[Background] {BACKGROUND_FILE} not found — using gradient")
            return

        try:
            raw = pygame.image.load(path).convert()
            iw, ih = raw.get_size()
            print(f"[Background] Loaded ({iw}x{ih})")

            target_h = int(WINDOW_H * BACKGROUND_ZOOM)
            scale_h = target_h / ih
            scale_w_min = (WINDOW_W + 800) / iw
            scale = max(scale_h, scale_w_min)

            new_w = int(iw * scale)
            new_h = int(ih * scale)
            self.image = pygame.transform.smoothscale(raw, (new_w, new_h))
            self.world_width = float(new_w)
            print(f"[Background] Scaled to {new_w}x{new_h}")
        except Exception as e:
            print(f"[Background] Failed to load: {e}")

    # -----------------------------------------------------------------------
    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        w, h = screen.get_size()

        # ---- Sky / background image ----
        if self.image is None:
            for y in range(h):
                t = y / h
                pygame.draw.line(screen,
                                 (int(14 + 20 * t), int(9 + 14 * t),
                                  int(28 + 24 * t)), (0, y), (w, y))
        else:
            bg_h = self.image.get_height()
            y = GROUND_Y - bg_h
            x = -camera_x
            screen.blit(self.image, (x, y))
            if x > 0:
                pygame.draw.rect(screen, (14, 9, 22), (0, 0, x, h))
            img_right = x + self.image.get_width()
            if img_right < w:
                pygame.draw.rect(screen, (14, 9, 22),
                                 (img_right, 0, w - img_right, h))

        # ---- Ground prop strip (single image, tiled) ----
        self._draw_ground(screen, camera_x)

    # -----------------------------------------------------------------------
    def _draw_ground(self, screen: pygame.Surface, camera_x: float) -> None:
        """
        Draw the single ground prop image repeatedly across the visible
        viewport. If it's missing, draw a simple purple strip as fallback.
        """
        w, h = screen.get_size()

        if self.ground.image is None:
            # Fallback strip
            pygame.draw.rect(screen, (14, 9, 22),
                             (0, GROUND_Y, w, h - GROUND_Y))
            pygame.draw.rect(screen, (66, 28, 98),
                             (0, GROUND_Y, w, 5))
            pygame.draw.rect(screen, (124, 62, 176),
                             (0, GROUND_Y, w, 1))
            return

        tile = self.ground.image
        tw = tile.get_width()
        th = tile.get_height()

        # Anchor the top of the tile so its top edge sits at GROUND_Y.
        y = GROUND_Y
        # How far into the first tile are we (based on camera)?
        offset = -camera_x % tw if tw > 0 else 0
        x = -offset

        # Fill below with a solid color in case the tile doesn't reach bottom
        if y + th < h:
            pygame.draw.rect(screen, (14, 9, 22),
                             (0, y + th, w, h - (y + th)))

        while x < w:
            screen.blit(tile, (int(x), int(y)))
            x += tw

        # Thin accent line at the very top for that gothic look
        pygame.draw.rect(screen, (66, 28, 98), (0, GROUND_Y, w, 2))
        pygame.draw.rect(screen, (124, 62, 176), (0, GROUND_Y, w, 1))


# ---------------------------------------------------------------------------
# Splash image
# ---------------------------------------------------------------------------
def load_splash_image(data_dir: str) -> Optional[pygame.Surface]:
    path = os.path.join(data_dir, SPLASH_FILE)
    if not os.path.exists(path):
        print(f"[Splash] {SPLASH_FILE} not found at {path}")
        return None

    try:
        raw = pygame.image.load(path).convert()
        iw, ih = raw.get_size()
        scale = max(WINDOW_W / iw, WINDOW_H / ih)
        new_w = int(iw * scale)
        new_h = int(ih * scale)
        scaled = pygame.transform.smoothscale(raw, (new_w, new_h))
        canvas = pygame.Surface((WINDOW_W, WINDOW_H))
        cx = (new_w - WINDOW_W) // 2
        cy = (new_h - WINDOW_H) // 2
        canvas.blit(scaled, (-cx, -cy))
        print(f"[Splash] Loaded background_splash.png ({iw}x{ih})")
        return canvas
    except Exception as e:
        print(f"[Splash] Failed to load: {e}")
        return None


# ---------------------------------------------------------------------------
# Icon
# ---------------------------------------------------------------------------
def load_icon(data_dir: str) -> None:
    path = os.path.join(data_dir, ICON_FILE)
    if not os.path.exists(path):
        return
    try:
        pygame.display.set_icon(pygame.image.load(path))
    except Exception as e:
        print(f"[Icon] Failed to load window icon: {e}")