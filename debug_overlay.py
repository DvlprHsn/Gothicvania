"""
Debug overlay — draws hitboxes, hurtboxes, state labels.
"""

from __future__ import annotations

import pygame

from ui import PALETTE


def draw_debug_overlay(surface, fighter, label,
                       show_boxes, show_labels, cam_x):
    hit_rects = [r.move(-cam_x, 0) for r in fighter.debug_hitboxes]
    hurt_rects = [r.move(-cam_x, 0) for r in fighter.debug_hurtboxes]

    if show_boxes:
        for r in hurt_rects:
            _alpha_rect(surface, (0, 220, 255, 70), r, (0, 220, 255))
        for r in hit_rects:
            _alpha_rect(surface, (255, 40, 40, 110), r, (255, 80, 80))

    if show_labels:
        px = int(fighter.pos.x - cam_x)
        py = int(fighter.pos.y)
        pygame.draw.line(surface, PALETTE["yellow"],
                         (px - 10, py), (px + 10, py), 2)
        pygame.draw.line(surface, PALETTE["yellow"],
                         (px, py - 10), (px, py + 10), 2)

        frame = fighter._current_frame()
        if frame:
            src = frame.source_rect
            fpx, fpy = frame.pivot
            scale = 3
            sw = int(src.w * scale)
            sh = int(src.h * scale)
            if fighter.facing >= 0:
                tlx = px - fpx * scale
            else:
                tlx = px - (src.w - fpx) * scale
            tly = py - fpy * scale
            pygame.draw.rect(surface, PALETTE["white"],
                             pygame.Rect(int(tlx), int(tly), sw, sh), 1)

        font = pygame.font.SysFont("consolas,courier", 14, bold=True)
        invuln = f" INV:{fighter.invuln_timer:.1f}" if fighter.invuln_timer > 0 else ""
        info = f"{label} | {fighter.state.upper()}{invuln}"
        text = font.render(info, True, PALETTE["white"])
        bg = pygame.Surface((text.get_width() + 8, text.get_height() + 4),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        tx = px - bg.get_width() // 2
        ty = py - 160
        surface.blit(bg, (tx, ty))
        surface.blit(text, (tx + 4, ty + 2))
        pygame.draw.circle(surface, PALETTE["purple_l"], (px, py), 3)


def _alpha_rect(screen, fill_color, rect, outline_color):
    if rect.w <= 0 or rect.h <= 0:
        return
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    surf.fill(fill_color)
    screen.blit(surf, rect.topleft)
    pygame.draw.rect(screen, outline_color, rect, 1)