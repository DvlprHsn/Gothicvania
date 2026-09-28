"""
Camera: smooth lead-tracking, clamped to world bounds.
"""

from __future__ import annotations

import pygame

from config import WINDOW_W, CAMERA_LEAD, SCREEN_MARGIN


class Camera:
    def __init__(self) -> None:
        self.x: float = 0.0

    def reset(self) -> None:
        self.x = 0.0

    def update(self, p1, p2, world_width: float) -> None:
        """Track the midpoint between two fighters with a velocity lead."""
        mid_x = (p1.pos.x + p2.pos.x) * 0.5
        avg_vx = (p1.velocity.x + p2.velocity.x) * 0.5
        lead = max(-CAMERA_LEAD, min(CAMERA_LEAD,
                                     (avg_vx / 260.0) * CAMERA_LEAD))
        target_cam = mid_x + lead - WINDOW_W * 0.5

        # Keep both fighters inside a comfortable margin
        leftmost = min(p1.pos.x, p2.pos.x)
        rightmost = max(p1.pos.x, p2.pos.x)
        if leftmost - target_cam < SCREEN_MARGIN:
            target_cam = leftmost - SCREEN_MARGIN
        if rightmost - target_cam > WINDOW_W - SCREEN_MARGIN:
            target_cam = rightmost + SCREEN_MARGIN - WINDOW_W

        max_cam = max(0.0, world_width - WINDOW_W)
        target_cam = max(0.0, min(target_cam, max_cam))

        # Smooth lerp
        self.x += (target_cam - self.x) * 0.08