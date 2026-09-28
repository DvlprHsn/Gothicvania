"""
Main menu — choose SinglePlayer or Multiplayer.
"""

from __future__ import annotations

import pygame

from ui import PALETTE, ui_panel


class MenuScreen:
    OPTIONS = [
        ("SinglePlayer", False),
        ("Multiplayer", True),
    ]

    def __init__(self) -> None:
        self.selected = 0
        self.font_title = pygame.font.SysFont("georgia,times,serif", 64, bold=True)
        self.font_opt = pygame.font.SysFont("georgia,times,serif", 34, bold=True)
        self.font_hint = pygame.font.SysFont("georgia,times,serif", 20)

    def handle_event(self, event):
        """Returns True/False (two_players flag) if a choice was made, else None."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            return self.OPTIONS[self.selected][1]

        return None

    def draw(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()

        for y in range(h):
            t = y / h
            r = int(14 + 20 * t)
            g = int(9 + 14 * t)
            b = int(28 + 24 * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (w, y))

        title = self.font_title.render("CHOOSE  YOUR  FIGHT", True,
                                       PALETTE["gold_l"])
        title_shadow = self.font_title.render("CHOOSE  YOUR  FIGHT", True,
                                              (0, 0, 0))
        title_rect = title.get_rect(center=(w // 2, 180))
        screen.blit(title_shadow, (title_rect.x + 3, title_rect.y + 3))
        screen.blit(title, title_rect)

        y0 = 340
        for i, (label, _mode) in enumerate(self.OPTIONS):
            selected = (i == self.selected)
            color = PALETTE["gold_l"] if selected else PALETTE["white"]
            rendered = self.font_opt.render(label, True, color)

            box_w = 420
            box_h = 80
            box_x = w // 2 - box_w // 2
            box_y = y0 + i * 110 - box_h // 2
            box = pygame.Rect(box_x, box_y, box_w, box_h)

            if selected:
                ui_panel(screen, box,
                         fill=PALETTE["bg_panel_l"],
                         border=PALETTE["gold_l"],
                         border_w=4, radius=12)
                pygame.draw.polygon(screen, PALETTE["gold_l"], [
                    (box_x - 30, box_y + box_h // 2),
                    (box_x - 10, box_y + box_h // 2 - 15),
                    (box_x - 10, box_y + box_h // 2 + 15),
                ])
                pygame.draw.polygon(screen, PALETTE["gold_l"], [
                    (box_x + box_w + 30, box_y + box_h // 2),
                    (box_x + box_w + 10, box_y + box_h // 2 - 15),
                    (box_x + box_w + 10, box_y + box_h // 2 + 15),
                ])
            else:
                ui_panel(screen, box,
                         fill=PALETTE["bg_panel"],
                         border=PALETTE["gold_d"],
                         border_w=2, radius=12)

            screen.blit(rendered, rendered.get_rect(center=box.center))

        hint = self.font_hint.render(
            "Up / Down  to choose      SPACE / ENTER  to start      ESC  to quit",
            True, PALETTE["white"])
        screen.blit(hint, hint.get_rect(center=(w // 2, h - 80)))