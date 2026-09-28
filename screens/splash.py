"""
Splash screen — fade-in/fade-out, click-to-skip.
"""

from __future__ import annotations

import pygame

from config import WINDOW_W, WINDOW_H
from assets import load_splash_image
from ui import PALETTE


class SplashScreen:
    def __init__(self, data_dir: str) -> None:
        self.image = load_splash_image(data_dir)
        self.font_small = pygame.font.SysFont("georgia,times,serif", 22, bold=True)
        self.timer = 0.0
        self.duration = 3.0

    def update(self, dt: float) -> None:
        self.timer += dt

    def is_done(self) -> bool:
        return self.timer >= self.duration

    def reset(self) -> None:
        self.timer = 0.0

    def skip(self) -> None:
        self.timer = self.duration

    def draw(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()

        if self.image:
            t = self.timer / self.duration
            if t < 0.15:
                alpha = int(255 * (t / 0.15))
            elif t > 0.85:
                alpha = int(255 * max(0, (1 - t) / 0.15))
            else:
                alpha = 255
            self.image.set_alpha(alpha)
            screen.blit(self.image, (0, 0))
        else:
            for y in range(h):
                t = y / h
                pygame.draw.line(screen,
                                 (int(20 + 40 * t), int(10 + 20 * t),
                                  int(40 + 40 * t)), (0, y), (w, y))

        if int(self.timer * 2) % 2 == 0:
            prompt = self.font_small.render(
                "Press any key to continue", True, PALETTE["gold_l"])
            shadow = self.font_small.render(
                "Press any key to continue", True, (0, 0, 0))
            r = prompt.get_rect(center=(w // 2, h - 70))
            screen.blit(shadow, (r.x + 2, r.y + 2))
            screen.blit(prompt, r)