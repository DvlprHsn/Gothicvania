"""
UI palette + drawing widgets.
All HUD elements (health bars, timer, countdown, KO overlay) live here.
"""

from __future__ import annotations

import math
import pygame


# ---------------------------------------------------------------------------
# Gothic palette
# ---------------------------------------------------------------------------
PALETTE = {
    "bg_deep":    (14,  9, 22),
    "bg_panel":   (26, 16, 42),
    "bg_panel_l": (46, 28, 72),
    "gold":       (218, 178, 96),
    "gold_d":     (140, 100, 40),
    "gold_l":     (255, 226, 148),
    "purple":     (124,  62, 176),
    "purple_l":   (188, 116, 232),
    "purple_d":   (66,  28,  98),
    "blood":      (172,  34,  52),
    "blood_l":    (222,  78,  78),
    "green":      (96, 172, 88),
    "green_l":    (140, 220, 120),
    "yellow":     (232, 200, 72),
    "yellow_l":   (255, 236, 130),
    "white":      (238, 232, 220),
    "black":      (0, 0, 0),
}


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------
def ui_panel(surface, rect, fill=None, border=None, border_w=2,
             radius=8, shadow=True):
    fill = fill or PALETTE["bg_panel"]
    border = border or PALETTE["gold_d"]

    if shadow:
        sh = pygame.Surface((rect.w + 6, rect.h + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 140),
                         (0, 0, rect.w + 6, rect.h + 6),
                         border_radius=radius + 2)
        surface.blit(sh, (rect.x + 2, rect.y + 3))

    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, border_w, border_radius=radius)


# ---------------------------------------------------------------------------
# Health bar
# ---------------------------------------------------------------------------
def ui_gradient_bar(surface, rect, top_color, bottom_color, fill_frac, is_p1):
    w, h = rect.w, rect.h
    fill_w = int(w * max(0.0, min(1.0, fill_frac)))
    if fill_w <= 0:
        return

    for i in range(h):
        t = i / max(1, h - 1)
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        if is_p1:
            pygame.draw.line(surface, (r, g, b),
                             (rect.x, rect.y + i),
                             (rect.x + fill_w, rect.y + i))
        else:
            pygame.draw.line(surface, (r, g, b),
                             (rect.x + w - fill_w, rect.y + i),
                             (rect.x + w, rect.y + i))

    gloss = pygame.Surface((fill_w, h // 3), pygame.SRCALPHA)
    gloss.fill((255, 255, 255, 40))
    if is_p1:
        surface.blit(gloss, (rect.x, rect.y))
    else:
        surface.blit(gloss, (rect.x + w - fill_w, rect.y))


def draw_ornate_health_bar(surface, x, y, w, h, hp, max_hp, is_p1):
    frame = pygame.Rect(x - 8, y - 8, w + 16, h + 16)
    ui_panel(surface, frame, fill=PALETTE["bg_deep"],
             border=PALETTE["gold_d"], border_w=3, radius=10)

    trough = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, PALETTE["bg_panel_l"], trough, border_radius=4)

    frac = hp / max_hp
    if frac > 0.55:
        top, bot = PALETTE["green_l"], PALETTE["green"]
    elif frac > 0.25:
        top, bot = PALETTE["yellow_l"], PALETTE["yellow"]
    else:
        top, bot = PALETTE["blood_l"], PALETTE["blood"]

    if frac < 0.2 and pygame.time.get_ticks() % 400 < 120:
        top, bot = (255, 180, 180), (255, 90, 90)

    ui_gradient_bar(surface, trough, top, bot, frac, is_p1)

    pygame.draw.rect(surface, PALETTE["gold"], trough, 1, border_radius=4)
    for cx, cy in ((x - 6, y - 6), (x + w + 6, y - 6),
                   (x - 6, y + h + 6), (x + w + 6, y + h + 6)):
        pygame.draw.circle(surface, PALETTE["gold_l"], (cx, cy), 4)
        pygame.draw.circle(surface, PALETTE["gold_d"], (cx, cy), 4, 1)


# ---------------------------------------------------------------------------
# Name plate
# ---------------------------------------------------------------------------
def draw_name_plate(surface, x, y, text, is_p1):
    font = pygame.font.SysFont("georgia,times,serif", 20, bold=True)
    color = PALETTE["gold_l"] if is_p1 else PALETTE["purple_l"]
    rendered = font.render(text, True, color)
    tw, th = rendered.get_size()
    plate = pygame.Rect(x, y, tw + 28, th + 12)
    if not is_p1:
        plate.x = x - plate.w
    ui_panel(surface, plate, fill=PALETTE["bg_panel"],
             border=PALETTE["gold_d"], border_w=2, radius=6)
    surface.blit(rendered, (plate.x + 14, plate.y + 6))


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------
def draw_ornate_timer(surface, seconds_left):
    w = surface.get_width()
    font = pygame.font.SysFont("georgia,times,serif", 56, bold=True)
    secs = max(0, int(seconds_left))
    danger = secs <= 10
    color = PALETTE["blood_l"] if danger else PALETTE["gold_l"]
    rendered = font.render(f"{secs:02d}", True, color)

    box = pygame.Rect(w // 2 - 70, 20, 140, 88)
    ui_panel(surface, box, fill=PALETTE["bg_deep"],
             border=PALETTE["gold_d"], border_w=3, radius=12)

    inner = pygame.Rect(box.x + 8, box.y + 8, box.w - 16, box.h - 16)
    pygame.draw.rect(surface, (8, 4, 14), inner, border_radius=6)

    for cx, cy in ((box.x, box.y), (box.x + box.w, box.y),
                   (box.x, box.y + box.h), (box.x + box.w, box.y + box.h)):
        pygame.draw.circle(surface, PALETTE["purple"], (cx, cy), 6)
        pygame.draw.circle(surface, PALETTE["gold_l"], (cx, cy), 6, 2)

    surface.blit(rendered,
                 rendered.get_rect(center=(w // 2, box.y + box.h // 2)))


# ---------------------------------------------------------------------------
# Countdown
# ---------------------------------------------------------------------------
def draw_countdown(surface, seconds_left):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2

    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((12, 4, 24, 120))
    surface.blit(dim, (0, 0))

    if seconds_left > 2.0:
        text, color = "3", PALETTE["white"]
    elif seconds_left > 1.0:
        text, color = "2", PALETTE["gold_l"]
    elif seconds_left > 0.0:
        text, color = "1", PALETTE["gold_l"]
    else:
        text, color = "FIGHT!", PALETTE["blood_l"]

    frac = seconds_left - math.floor(seconds_left)
    if text == "FIGHT!":
        pulse = 1.0 + 0.15 * abs(math.sin((1.0 - abs(seconds_left)) * 6.0))
    else:
        pulse = 1.0 + 0.25 * (1.0 - frac)

    font_size = 200 if text != "FIGHT!" else 150
    font = pygame.font.SysFont("georgia,times,serif", font_size, bold=True)
    rendered = font.render(text, True, color)
    kw, kh = rendered.get_size()
    scaled = pygame.transform.smoothscale(
        rendered, (int(kw * pulse), int(kh * pulse)))

    glow = font.render(text, True, (150, 80, 220))
    glow.set_alpha(80)
    glow_scaled = pygame.transform.smoothscale(
        glow, (int(kw * pulse) + 10, int(kh * pulse) + 10))
    surface.blit(glow_scaled, glow_scaled.get_rect(center=(cx, cy)))

    surface.blit(scaled, scaled.get_rect(center=(cx, cy)))


# ---------------------------------------------------------------------------
# KO overlay
# ---------------------------------------------------------------------------
def draw_ornate_ko(surface, winner_text, time):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2

    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((12, 4, 24, 210))
    surface.blit(dim, (0, 0))

    edge = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(0, 6):
        alpha = int(40 - i * 6)
        pygame.draw.rect(edge, (0, 0, 0, max(0, alpha)),
                         (i * 8, i * 8, w - i * 16, h - i * 16),
                         width=16)
    surface.blit(edge, (0, 0))

    if int(time * 1.6) % 2 == 0:
        font_hint = pygame.font.SysFont("georgia,times,serif", 22, bold=True)
        hint = font_hint.render("PRESS  R  TO  CONTINUE", True,
                                (215, 200, 240))
        surface.blit(hint, hint.get_rect(center=(cx, 180)))

    pulse = 1.0 + 0.02 * math.sin(time * 3.0)
    font_ko = pygame.font.SysFont("georgia,times,serif", 200, bold=True)
    ko_render = font_ko.render("K.O.", True, PALETTE["gold_l"])
    kw, kh = ko_render.get_size()
    scaled = pygame.transform.smoothscale(
        ko_render, (int(kw * pulse), int(kh * pulse)))

    glow = font_ko.render("K.O.", True, (150, 80, 220))
    glow.set_alpha(60)
    glow_scaled = pygame.transform.smoothscale(
        glow, (int(kw * pulse) + 8, int(kh * pulse) + 8))
    surface.blit(glow_scaled, glow_scaled.get_rect(center=(cx, cy)))
    surface.blit(scaled, scaled.get_rect(center=(cx, cy)))

    line_w = int(scaled.get_width() * 0.9)
    line_color = PALETTE["gold_d"]
    top_y = cy - scaled.get_height() // 2 - 22
    bot_y = cy + scaled.get_height() // 2 + 22

    pygame.draw.line(surface, line_color,
                     (cx - line_w // 2, top_y),
                     (cx + line_w // 2, top_y), 2)
    pygame.draw.line(surface, line_color,
                     (cx - line_w // 2, bot_y),
                     (cx + line_w // 2, bot_y), 2)

    for lx in (cx - line_w // 2, cx + line_w // 2):
        pygame.draw.polygon(surface, PALETTE["purple"], [
            (lx, bot_y - 5), (lx + 5, bot_y),
            (lx, bot_y + 5), (lx - 5, bot_y),
        ])

    wt = winner_text.lower()
    if "player 1" in wt:
        accent = PALETTE["gold_l"]
    elif "player 2" in wt:
        accent = PALETTE["purple_l"]
    elif "bot" in wt:
        accent = (230, 130, 220)
    else:
        accent = PALETTE["white"]

    font_win = pygame.font.SysFont("georgia,times,serif", 34, bold=True)
    win_render = font_win.render(winner_text, True, accent)
    surface.blit(win_render, win_render.get_rect(center=(cx, bot_y + 70)))