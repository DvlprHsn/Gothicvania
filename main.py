"""
Gothicvania Church — Two-Player Fighter
========================================

Splash → Menu → Fight → KO → Splash

  • Splash screen on launch and after KO
  • Menu lets you choose SinglePlayer (vs Bot) or Multiplayer (2P)
  • TAB toggles P2 between bot and human mid-match
  • Background music (data/music/theme.ogg) with M to mute
  • 3-2-1-FIGHT countdown before each round
  • Smooth lead-tracking camera
  • Gothic purple UI
  • Procedural sound effects
  • Real knockback, hitstun, invulnerability

Works both as `python main.py` AND as a PyInstaller-built exe.
"""

from __future__ import annotations

import os
import sys

import pygame

# ---------------------------------------------------------------------------
# PyInstaller-aware resource path
# ---------------------------------------------------------------------------
def resource_path(relative_path: str) -> str:
    """
    Get absolute path to a bundled resource.

    - In development: resolves relative to the current working directory.
    - In a PyInstaller onefile exe: resolves relative to sys._MEIPASS,
      which is the temp folder PyInstaller unpacks assets into at runtime.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ---------------------------------------------------------------------------
# Internal packages
# ---------------------------------------------------------------------------
from config import (
    WINDOW_W, WINDOW_H, FPS, GROUND_Y, ROUND_TIME, COUNTDOWN_TIME,
    MAX_HP, HIT_COOLDOWN,
    DEFAULT_TWO_PLAYERS, AI_DIFFICULTY,
    P1_KEYS, P2_KEYS, DATA_DIR,
)
from audio import build_sfx, build_music, toggle_mute, restart_music
from assets import (
    load_fighter_assets, ScrollingBackground, load_icon,
)
from camera import Camera
from screens.splash import SplashScreen
from screens.menu import MenuScreen

from entities.fighter import Fighter, set_sfx
from entities.bot import Bot

from ui import (
    PALETTE,
    draw_ornate_health_bar, draw_name_plate,
    draw_ornate_timer, draw_countdown, draw_ornate_ko,
)
from debug_overlay import draw_debug_overlay


# =============================================================================
# EMPTY INPUT (used during countdown)
# =============================================================================
class _EmptyInput:
    """Mimics pygame.key.get_pressed() with nothing pressed."""
    def __getitem__(self, key):
        return False


# =============================================================================
# GAME
# =============================================================================
class Game:
    def __init__(self) -> None:
        pygame.init()

        # ---- Data folder (works in dev and in a PyInstaller exe) ----
        data_dir = resource_path(DATA_DIR)

        # ---- Audio ----
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.sfx = build_sfx(data_dir)
            set_sfx(self.sfx)
            print("[Audio] Sound effects ready")

            self.music_path = build_music(data_dir)
            self.music_playing = self.music_path is not None
        except Exception as e:
            print(f"[Audio] mixer failed: {e}")
            self.sfx = {}
            self.music_path = None
            self.music_playing = False

        # ---- Window ----
        pygame.display.set_caption("Gothicvania Church Fight")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        load_icon(data_dir)
        self.clock = pygame.time.Clock()

        # ---- Assets ----
        try:
            self.fighter_assets = load_fighter_assets(data_dir)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            pygame.quit()
            sys.exit(1)

        self.background = ScrollingBackground(data_dir)
        self.splash = SplashScreen(data_dir)
        self.menu = MenuScreen()
        self.camera = Camera()

        # ---- State ----
        self.state = "splash"
        self.menu_lockout = 0.0

        self.show_boxes = False
        self.show_labels = False
        self.font = pygame.font.SysFont("georgia,times,serif", 20, bold=True)
        self.debug_font = pygame.font.SysFont("consolas,courier", 14)

        self.two_players = DEFAULT_TWO_PLAYERS

        self.p1 = None
        self.p2 = None
        self.bot = None

        self.p1_hp = MAX_HP
        self.p2_hp = MAX_HP
        self.timer = ROUND_TIME
        self.countdown = 0.0
        self.ko_winner = ""
        self.p1_hit_cd = 0.0
        self.p2_hit_cd = 0.0

    # -------------------------------------------------------------------------
    def _p2_display_name(self) -> str:
        return "Player 2" if self.two_players else "Gothicvania Bot"

    # -------------------------------------------------------------------------
    def start_match(self, two_players: bool) -> None:
        self.two_players = two_players
        restart_music(self.music_playing)

        spawn_center = self.background.world_width * 0.5
        atlas = self.fighter_assets.atlas
        data = self.fighter_assets.data

        self.p1 = Fighter(atlas, data,
                          spawn_x=spawn_center - 220, spawn_y=GROUND_Y,
                          facing=1)
        self.p2 = Fighter(atlas, data,
                          spawn_x=spawn_center + 220, spawn_y=GROUND_Y,
                          facing=-1)

        self.bot = None
        if not self.two_players:
            self.bot = Bot(keys=P2_KEYS, difficulty=AI_DIFFICULTY)

        self.p1_hp = MAX_HP
        self.p2_hp = MAX_HP
        self.timer = ROUND_TIME
        self.countdown = COUNTDOWN_TIME
        self.ko_winner = ""
        self.p1_hit_cd = 0.0
        self.p2_hit_cd = 0.0

        self.camera.reset()
        self.camera.x = max(
            0.0,
            min(spawn_center - WINDOW_W * 0.5,
                self.background.world_width - WINDOW_W))

        self.state = "fight"

    # -------------------------------------------------------------------------
    def toggle_control_mode(self) -> None:
        self.two_players = not self.two_players
        if self.two_players:
            self.bot = None
            print("[Control] Player 2 is now HUMAN (WASD + Z/X)")
        else:
            self.bot = Bot(keys=P2_KEYS, difficulty=AI_DIFFICULTY)
            print("[Control] Player 2 is now Gothicvania Bot")

    # -------------------------------------------------------------------------
    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            t = pygame.time.get_ticks() / 1000.0

            self.menu_lockout = max(0.0, self.menu_lockout - dt)

            # Music keep-alive
            if (self.music_playing
                    and self.state == "fight"
                    and pygame.mixer.music.get_volume() > 0.0
                    and not pygame.mixer.music.get_busy()):
                restart_music(self.music_playing)

            # ---- Events ----
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                    break

                if self.state == "splash":
                    if event.type == pygame.KEYDOWN:
                        self.splash.skip()

                elif self.state == "menu":
                    if self.menu_lockout <= 0.0:
                        result = self.menu.handle_event(event)
                        if result is not None:
                            self.start_match(result)

                elif self.state in ("fight", "ko"):
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_F1:
                            self.show_boxes = not self.show_boxes
                        elif event.key == pygame.K_F2:
                            self.show_labels = not self.show_labels
                        elif event.key == pygame.K_TAB:
                            self.toggle_control_mode()
                        elif event.key == pygame.K_m:
                            toggle_mute(self.music_playing)
                        elif event.key == pygame.K_r and self.state == "ko":
                            self.splash.reset()
                            self.state = "splash"
                            self.menu_lockout = 0.0

            # ---- Update ----
            if self.state == "splash":
                self.splash.update(dt)
                if self.splash.is_done():
                    self.state = "menu"
                    self.menu_lockout = 0.30

            elif self.state == "fight":
                self._update(dt)

            # ---- Draw ----
            self._draw(t)
            pygame.display.flip()

        pygame.quit()

    # -------------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        pressed = pygame.key.get_pressed()

        # ---- Countdown: no input, fighters still update physics ----
        if self.countdown > 0.0:
            self.countdown -= dt
            no_input = _EmptyInput()

            self.p1.update(dt, no_input, P1_KEYS, GROUND_Y)
            self.p2.update(dt, no_input, P2_KEYS, GROUND_Y)

            mid_x = (self.p1.pos.x + self.p2.pos.x) * 0.5
            self.camera.x = max(
                0.0,
                min(mid_x - WINDOW_W * 0.5,
                    self.background.world_width - WINDOW_W))

            if self.countdown <= 0.0:
                self.p1._prev_pressed.clear()
                self.p2._prev_pressed.clear()
            return

        # ---- Normal gameplay ----
        self.p1.update(dt, pressed, P1_KEYS, GROUND_Y)

        if self.two_players:
            self.p2.update(dt, pressed, P2_KEYS, GROUND_Y)
        else:
            self.bot.think(player=self.p1, me=self.p2, dt=dt)
            self.p2.update(dt, self.bot.key_state, P2_KEYS, GROUND_Y)

        # ---- Camera ----
        self.camera.update(self.p1, self.p2, self.background.world_width)

        # ---- Clamp fighters to visible area ----
        vis_left = self.camera.x + 40
        vis_right = self.camera.x + WINDOW_W - 40
        for f in (self.p1, self.p2):
            if f.pos.x < vis_left:
                f.pos.x = vis_left
                if f.velocity.x < 0:
                    f.velocity.x = 0.0
            elif f.pos.x > vis_right:
                f.pos.x = vis_right
                if f.velocity.x > 0:
                    f.velocity.x = 0.0

        # ---- Push apart if overlapping ----
        dx = self.p2.pos.x - self.p1.pos.x
        if 0 < abs(dx) < 26.0:
            push = (26.0 - abs(dx)) * 0.18
            sign = 1 if dx > 0 else -1
            self.p1.pos.x -= sign * push
            self.p2.pos.x += sign * push

        for f in (self.p1, self.p2):
            f.pos.x = max(vis_left, min(vis_right, f.pos.x))

        # ---- Hit cooldowns + collision ----
        self.p1_hit_cd = max(0.0, self.p1_hit_cd - dt)
        self.p2_hit_cd = max(0.0, self.p2_hit_cd - dt)

        self._check_hits(self.p1, self.p2, is_p1=True)
        self._check_hits(self.p2, self.p1, is_p1=False)

        # ---- Timer / win conditions ----
        self.timer -= dt
        if self.timer <= 0.0:
            self.timer = 0.0
            if self.state == "fight":
                self.state = "ko"
                p2_name = self._p2_display_name()
                if self.p1_hp > self.p2_hp:
                    self.ko_winner = "Player 1 wins by time!"
                elif self.p2_hp > self.p1_hp:
                    self.ko_winner = f"{p2_name} wins by time!"
                else:
                    self.ko_winner = "Draw!"
                if self.music_playing:
                    pygame.mixer.music.fadeout(800)

        if self.state == "fight":
            p2_name = self._p2_display_name()
            if self.p1_hp <= 0:
                self.state = "ko"
                self.ko_winner = f"{p2_name} wins!"
                if "ko" in self.sfx and self.sfx["ko"]:
                    self.sfx["ko"].play()
                if self.music_playing:
                    pygame.mixer.music.fadeout(800)
            elif self.p2_hp <= 0:
                self.state = "ko"
                self.ko_winner = "Player 1 wins!"
                if "ko" in self.sfx and self.sfx["ko"]:
                    self.sfx["ko"].play()
                if self.music_playing:
                    pygame.mixer.music.fadeout(800)

    # -------------------------------------------------------------------------
    def _check_hits(self, attacker, defender, is_p1: bool) -> None:
        if not attacker.attack_active_window:
            return
        cooldown = self.p1_hit_cd if is_p1 else self.p2_hit_cd
        if cooldown > 0:
            return
        if not attacker.debug_hitboxes or not defender.debug_hurtboxes:
            return

        for hb in attacker.debug_hitboxes:
            for hu in defender.debug_hurtboxes:
                if hb.colliderect(hu):
                    dmg = attacker.attack_damage
                    defender.take_damage(dmg, attacker_x=attacker.pos.x)
                    if is_p1:
                        self.p2_hp = max(0, self.p2_hp - dmg)
                        self.p1_hit_cd = HIT_COOLDOWN
                    else:
                        self.p1_hp = max(0, self.p1_hp - dmg)
                        self.p2_hit_cd = HIT_COOLDOWN
                    return

    # -------------------------------------------------------------------------
    def _draw(self, t: float) -> None:
        if self.state == "splash":
            self.splash.draw(self.screen)
            return

        if self.state == "menu":
            self.menu.draw(self.screen)
            return

        if self.p1 is None or self.p2 is None:
            return

        cam = self.camera.x
        self.background.draw(self.screen, cam)
        self._draw_fighter(self.p1, cam)
        self._draw_fighter(self.p2, cam)

        if self.show_boxes or self.show_labels:
            draw_debug_overlay(self.screen, self.p1, "P1",
                               self.show_boxes, self.show_labels, cam)
            p2_name = "P2" if self.two_players else "GVBOT"
            draw_debug_overlay(self.screen, self.p2, p2_name,
                               self.show_boxes, self.show_labels, cam)

        self._draw_ui()

        if self.state == "fight" and self.countdown > 0.0:
            draw_countdown(self.screen, self.countdown)

        if self.state == "ko":
            draw_ornate_ko(self.screen, self.ko_winner, t)

    def _draw_fighter(self, fighter, cam: float) -> None:
        orig = fighter.pos.x
        fighter.pos.x -= cam
        fighter.draw(self.screen, False)
        fighter.pos.x = orig

    # -------------------------------------------------------------------------
    def _draw_ui(self) -> None:
        w = WINDOW_W

        draw_ornate_health_bar(self.screen, 60, 40, 460, 32,
                               self.p1_hp, MAX_HP, is_p1=True)
        draw_ornate_health_bar(self.screen, w - 60 - 460, 40, 460, 32,
                               self.p2_hp, MAX_HP, is_p1=False)

        draw_name_plate(self.screen, 60, 92, "PLAYER  1", is_p1=True)
        p2_label = "PLAYER  2" if self.two_players else "GOTHICVANIA  BOT"
        draw_name_plate(self.screen, w - 60, 92, p2_label, is_p1=False)

        draw_ornate_timer(self.screen, self.timer)

        mode_font = pygame.font.SysFont("georgia,times,serif", 16, bold=True)
        mode_text = "TAB to switch to 2P   |   M to mute"
        if self.two_players:
            mode_text = "TAB to switch to Gothicvania Bot   |   M to mute"
        label = mode_font.render(mode_text, True, PALETTE["purple_l"])
        lb_rect = label.get_rect(center=(w // 2, WINDOW_H - 24))
        bg = pygame.Surface((lb_rect.w + 16, lb_rect.h + 8),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.screen.blit(bg, (lb_rect.x - 8, lb_rect.y - 4))
        self.screen.blit(label, lb_rect)

        if self.show_boxes or self.show_labels:
            lines = [
                "F1: boxes   F2: labels   TAB: toggle P2   M: music   R: restart   Esc: quit",
                f"boxes={'ON' if self.show_boxes else 'OFF'}  "
                f"labels={'ON' if self.show_labels else 'OFF'}  "
                f"mode={'2P' if self.two_players else 'GVBOT'}  "
                f"music={'ON' if self.music_playing and pygame.mixer.music.get_volume() > 0 else 'OFF'}",
            ]
            y = WINDOW_H - 64
            for i, line in enumerate(lines):
                text = self.debug_font.render(line, True, PALETTE["white"])
                bg2 = pygame.Surface(
                    (text.get_width() + 10, text.get_height() + 6),
                    pygame.SRCALPHA)
                bg2.fill((0, 0, 0, 180))
                self.screen.blit(bg2, (12, y + i * 20 - 3))
                self.screen.blit(text, (17, y + i * 20))


# =============================================================================
# ENTRY
# =============================================================================
def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()