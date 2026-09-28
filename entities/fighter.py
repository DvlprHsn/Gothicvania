"""
Fighter — Pygame fighting character driven by SpriteSlicer JSON.

Features:
  - Per-fighter input routing (two players, one keyboard)
  - Input buffering, coyote time, jump cut
  - Variable gravity, terminal velocity
  - Hit-stop, landing recovery
  - Looping air kick
  - Crouch slide with animation speed-up
  - Facing lock during attacks
  - Real knockback with hitstun + invulnerability window
  - Procedural sound hooks
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, Callable

import pygame


# =============================================================================
# ANIMATION MAP
# =============================================================================
ANIM_MAP = {
    "idle":          "Idle",
    "walk":          "Walk",
    "jump":          "Jump",
    "fall":          "Fall",
    "crouch":        "Crouch",
    "attack_light":  "Punch",
    "attack_heavy":  "Kick",
    "crouch_attack": "Crouch Kick",
    "air_attack":    "Flying Kick",
    "hit":           "Hurt",
}


# =============================================================================
# SOUND HOOKS (populated by main from audio.build_sfx)
# =============================================================================
_sfx: Dict[str, Any] = {
    "punch": None, "kick": None, "hit": None, "ko": None, "jump": None,
}


def set_sfx(sounds: Dict[str, Any]) -> None:
    _sfx.update(sounds)


def play_sfx(name: str) -> None:
    snd = _sfx.get(name)
    if snd is not None:
        try:
            snd.play()
        except Exception:
            pass


# =============================================================================
# TUNING
# =============================================================================
MOVE_SPEED             = 260.0
CROUCH_SPEED_MULT      = 0.4
GROUND_FRICTION        = 2600.0
AIR_DRAG               = 0.02

CROUCH_SLIDE_SPEED     = 700.0
CROUCH_SLIDE_FRICTION  = 180.0
CROUCH_SLIDE_MIN       = 120.0
CROUCH_SLIDE_ANIM_MULT = 1.8

JUMP_VELOCITY          = -700.0
GRAVITY                = 1350.0
GRAVITY_FALL_MULT      = 1.30
MAX_FALL_SPEED         = 1100.0
JUMP_CUT_MULT          = 0.45

COYOTE_TIME            = 0.10
JUMP_BUFFER            = 0.12
ATTACK_BUFFER          = 0.15

LIGHT_DAMAGE           = 6
HEAVY_DAMAGE           = 14
AIR_DAMAGE             = 12
CROUCH_DAMAGE          = 9
HITSTUN_TIME           = 0.55
HITSTOP_TIME           = 0.08
LANDING_RECOVERY       = 0.08

KNOCKBACK_BASE         = 500.0
KNOCKBACK_PER_DAMAGE   = 22.0
KNOCKBACK_LAUNCH_DMG   = 12
KNOCKBACK_LAUNCH_VY    = -260.0
INVULN_AFTER_HIT       = 0.35

AIR_KICK_LAUNCH_BOOST  = -140.0
AIR_KICK_H_DRIVE       = 320.0

SPRITE_SCALE           = 3


# =============================================================================
# STATES
# =============================================================================
STATE_IDLE       = "idle"
STATE_WALK       = "walk"
STATE_CROUCH     = "crouch"
STATE_JUMP       = "jump"
STATE_FALL       = "fall"
STATE_ATTACK     = "attack"
STATE_AIR_ATTACK = "air_attack"
STATE_HIT        = "hit"
STATE_LANDING    = "landing"


# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float


@dataclass
class Frame:
    source_rect: Box
    pivot: Tuple[float, float]
    duration: float
    hitboxes: List[Box] = field(default_factory=list)
    hurtboxes: List[Box] = field(default_factory=list)


# =============================================================================
# FIGHTER
# =============================================================================
class Fighter:
    def __init__(self, atlas: pygame.Surface, data: Dict[str, Any],
                 spawn_x: int, spawn_y: int, facing: int = 1) -> None:
        self.atlas = atlas
        self.animations: Dict[str, List[Frame]] = {}
        self._parse_json(data)

        self.pos = pygame.Vector2(spawn_x, spawn_y)
        self.velocity = pygame.Vector2(0, 0)
        self.facing = facing
        self.on_ground = True

        self.state = STATE_IDLE
        self.state_time = 0.0
        self.current_anim = ""
        self.current_frame_idx = 0
        self.frame_timer = 0.0
        self.anim_finished = False
        self._anim_speed_bias = 1.0
        self._was_crouching_last_frame = False
        self._facing_locked = False

        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.attack_buffer_timer = 0.0
        self.attack_buffer_action = ""

        self.attack_key = ""
        self.attack_damage = 0
        self.attack_active_window = False
        self.hit_timer = 0.0
        self.hitstop_timer = 0.0
        self.invuln_timer = 0.0
        self.landing_timer = 0.0

        self._prev_pressed: Dict[int, bool] = {}
        self._keymap: Dict[int, str] = {}

        self.debug_hitboxes: List[pygame.Rect] = []
        self.debug_hurtboxes: List[pygame.Rect] = []

        self._anim_events: Dict[str, Dict[int, Callable[[], None]]] = {}
        self._last_fired_frame = -1

        self._play_anim("idle")

    # =========================================================================
    # JSON PARSING
    # =========================================================================
    def _parse_json(self, data: Dict[str, Any]) -> None:
        for anim in data.get("animations", []):
            name = anim.get("name", "")
            frames: List[Frame] = []
            for fr in anim.get("frames", []):
                src = fr.get("sourceRect", {})
                pv = fr.get("pivot", {"x": 0, "y": 0})
                dur_ms = float(fr.get("duration_ms", 100))
                hb = [Box(b["x"], b["y"], b["w"], b["h"])
                      for b in fr.get("hitboxes", [])]
                hu = [Box(b["x"], b["y"], b["w"], b["h"])
                      for b in fr.get("hurtboxes", [])]
                frames.append(Frame(
                    source_rect=Box(src.get("x", 0), src.get("y", 0),
                                    src.get("w", 0), src.get("h", 0)),
                    pivot=(float(pv.get("x", 0)), float(pv.get("y", 0))),
                    duration=dur_ms / 1000.0,
                    hitboxes=hb,
                    hurtboxes=hu,
                ))
            self.animations[name] = frames

    def register_anim_event(self, anim_name: str, frame_index: int,
                            callback: Callable[[], None]) -> None:
        self._anim_events.setdefault(anim_name, {})[frame_index] = callback

    # =========================================================================
    # INPUT LOOKUP
    # =========================================================================
    def _is_action_pressed(self, action: str, pressed) -> bool:
        for key, mapped in self._keymap.items():
            if mapped == action and pressed[key]:
                return True
        return False

    def _input_dir(self, pressed) -> int:
        d = 0
        if self._is_action_pressed("move_left", pressed):
            d -= 1
        if self._is_action_pressed("move_right", pressed):
            d += 1
        return d

    # =========================================================================
    # ANIMATION CONTROL
    # =========================================================================
    def _play_anim(self, key: str, restart: bool = False) -> None:
        anim_name = ANIM_MAP.get(key, key)
        if anim_name not in self.animations:
            return
        if not restart and self.current_anim == anim_name and not self.anim_finished:
            return
        self.current_anim = anim_name
        self.current_frame_idx = 0
        self.frame_timer = 0.0
        self.anim_finished = False
        self._last_fired_frame = -1

    def _current_frame(self) -> Optional[Frame]:
        frames = self.animations.get(self.current_anim, [])
        if not frames:
            return None
        return frames[self.current_frame_idx % len(frames)]

    def _advance_frame(self, dt: float) -> None:
        frames = self.animations.get(self.current_anim, [])
        if not frames:
            return

        bias = self._anim_speed_bias
        self._anim_speed_bias = 1.0
        effective_dt = dt * bias

        frame = frames[self.current_frame_idx % len(frames)]
        self.frame_timer += effective_dt
        while self.frame_timer >= frame.duration:
            self.frame_timer -= frame.duration
            self.current_frame_idx += 1
            if self.current_frame_idx >= len(frames):
                if self.current_anim in (ANIM_MAP["idle"], ANIM_MAP["walk"],
                                         ANIM_MAP["crouch"], ANIM_MAP["fall"]):
                    self.current_frame_idx = 0
                else:
                    self.current_frame_idx = len(frames) - 1
                    self.anim_finished = True
                    return
            frame = frames[self.current_frame_idx % len(frames)]
            self._fire_anim_events_if_needed()

    def _fire_anim_events_if_needed(self) -> None:
        if self._last_fired_frame == self.current_frame_idx:
            return
        self._last_fired_frame = self.current_frame_idx
        events = self._anim_events.get(self.current_anim, {})
        cb = events.get(self.current_frame_idx)
        if cb:
            cb()

    # =========================================================================
    # MAIN UPDATE
    # =========================================================================
    def update(self, dt: float, pressed, keymap: Dict[int, str],
               ground_y: float) -> None:
        self._keymap = keymap

        if self.hitstop_timer > 0.0:
            self.hitstop_timer = max(0.0, self.hitstop_timer - dt)
            self._advance_frame(dt * 0.15)
            return

        self.invuln_timer = max(0.0, self.invuln_timer - dt)

        just_pressed = set()
        just_released = set()
        for key, action in keymap.items():
            now = pressed[key]
            before = self._prev_pressed.get(key, False)
            if now and not before:
                just_pressed.add(action)
            elif before and not now:
                just_released.add(action)

        self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.attack_buffer_timer = max(0.0, self.attack_buffer_timer - dt)

        if "attack_light" in just_pressed:
            self.attack_buffer_timer = ATTACK_BUFFER
            self.attack_buffer_action = "attack_light"
        if "attack_heavy" in just_pressed:
            self.attack_buffer_timer = ATTACK_BUFFER
            self.attack_buffer_action = "attack_heavy"
        if "jump" in just_pressed:
            self.jump_buffer_timer = JUMP_BUFFER

        if "jump" in just_released and self.velocity.y < 0:
            self.velocity.y *= JUMP_CUT_MULT

        if not self.on_ground:
            g = GRAVITY * (GRAVITY_FALL_MULT if self.velocity.y > 0 else 1.0)
            self.velocity.y = min(self.velocity.y + g * dt, MAX_FALL_SPEED)

        self.state_time += dt
        if self.state in (STATE_IDLE, STATE_WALK, STATE_CROUCH):
            self._handle_grounded(dt, pressed, just_pressed, keymap)
        elif self.state in (STATE_JUMP, STATE_FALL):
            self._handle_air(dt, pressed, just_pressed, keymap)
        elif self.state == STATE_ATTACK:
            self._handle_attack(dt)
        elif self.state == STATE_AIR_ATTACK:
            self._handle_air_attack(dt)
        elif self.state == STATE_HIT:
            self._handle_hit(dt)
        elif self.state == STATE_LANDING:
            self._handle_landing(dt)

        self.pos.x += self.velocity.x * dt
        self.pos.y += self.velocity.y * dt

        if self.pos.y >= ground_y:
            if not self.on_ground:
                self._on_land()
            self.pos.y = ground_y
            self.velocity.y = 0.0
            self.on_ground = True
        else:
            if self.on_ground:
                self.coyote_timer = COYOTE_TIME
            self.on_ground = False

        self._advance_frame(dt)
        self._compute_debug_shapes()

        for key in keymap:
            self._prev_pressed[key] = pressed[key]

    # =========================================================================
    # GROUNDED
    # =========================================================================
    def _handle_grounded(self, dt, pressed, just_pressed, keymap) -> None:
        crouching = self._is_action_pressed("crouch", pressed)
        d_input = self._input_dir(pressed)

        if self.attack_buffer_timer > 0.0:
            if d_input != 0:
                self.facing = 1 if d_input > 0 else -1

            if self.attack_buffer_action == "attack_light" and not crouching:
                self._enter_ground_attack("attack_light", LIGHT_DAMAGE)
                self.attack_buffer_timer = 0.0
                return
            elif self.attack_buffer_action == "attack_heavy":
                if crouching:
                    self._enter_ground_attack("crouch_attack", CROUCH_DAMAGE)
                else:
                    self._enter_ground_attack("attack_heavy", HEAVY_DAMAGE)
                self.attack_buffer_timer = 0.0
                return

        if self.jump_buffer_timer > 0.0 and not crouching:
            self._do_jump()
            self.jump_buffer_timer = 0.0
            return

        if crouching:
            self._set_state(STATE_CROUCH)
            self._play_anim("crouch")

            was_crouching = self._was_crouching_last_frame
            self._was_crouching_last_frame = True

            if d_input != 0:
                self.facing = 1 if d_input > 0 else -1

                if not was_crouching and abs(self.velocity.x) > 20:
                    slide_dir = 1 if self.velocity.x > 0 else -1
                    self.velocity.x = slide_dir * CROUCH_SLIDE_SPEED

                if abs(self.velocity.x) > CROUCH_SLIDE_MIN:
                    if self.velocity.x > 0:
                        self.velocity.x = max(
                            CROUCH_SLIDE_MIN,
                            self.velocity.x - CROUCH_SLIDE_FRICTION * dt)
                    else:
                        self.velocity.x = min(
                            -CROUCH_SLIDE_MIN,
                            self.velocity.x + CROUCH_SLIDE_FRICTION * dt)
                    self._apply_slide_anim_speed()
                else:
                    self.velocity.x = d_input * MOVE_SPEED * CROUCH_SPEED_MULT
            else:
                if abs(self.velocity.x) > CROUCH_SLIDE_MIN:
                    if self.velocity.x > 0:
                        self.velocity.x = max(
                            0, self.velocity.x - CROUCH_SLIDE_FRICTION * dt)
                    else:
                        self.velocity.x = min(
                            0, self.velocity.x + CROUCH_SLIDE_FRICTION * dt)
                    self._apply_slide_anim_speed()
                else:
                    self.velocity.x = self._apply_friction(self.velocity.x, dt)
            return

        self._was_crouching_last_frame = False

        if d_input != 0:
            self.velocity.x = d_input * MOVE_SPEED
            self.facing = 1 if d_input > 0 else -1
            self._set_state(STATE_WALK)
            self._play_anim("walk")
        else:
            self.velocity.x = self._apply_friction(self.velocity.x, dt)
            self._set_state(STATE_IDLE)
            self._play_anim("idle")

    def _apply_slide_anim_speed(self) -> None:
        if self.current_anim != ANIM_MAP["crouch"]:
            return
        speed_factor = abs(self.velocity.x) / max(1.0, MOVE_SPEED)
        factor = max(1.0, min(2.5, speed_factor * CROUCH_SLIDE_ANIM_MULT))
        self._anim_speed_bias = factor

    def _do_jump(self) -> None:
        self.velocity.y = JUMP_VELOCITY
        self.on_ground = False
        self.coyote_timer = 0.0
        self._set_state(STATE_JUMP)
        self._play_anim("jump", restart=True)
        play_sfx("jump")

    # =========================================================================
    # AIRBORNE
    # =========================================================================
    def _handle_air(self, dt, pressed, just_pressed, keymap) -> None:
        if self.jump_buffer_timer > 0.0 and self.coyote_timer > 0.0:
            self._do_jump()
            self.jump_buffer_timer = 0.0
            return

        if self.attack_buffer_timer > 0.0 and self.attack_buffer_action == "attack_heavy":
            d_input = self._input_dir(pressed)
            if d_input != 0:
                self.facing = 1 if d_input > 0 else -1
            self._enter_air_kick()
            self.attack_buffer_timer = 0.0
            return

        d = self._input_dir(pressed)
        if d != 0:
            target = d * MOVE_SPEED
            self.velocity.x += (target - self.velocity.x) * 0.08
            self.facing = 1 if d > 0 else -1
        else:
            self.velocity.x *= (1.0 - AIR_DRAG)

        if self.velocity.y < 0:
            self._set_state(STATE_JUMP)
            self._play_anim("jump")
        else:
            self._set_state(STATE_FALL)
            self._play_anim("fall")

    # =========================================================================
    # ATTACKS
    # =========================================================================
    def _enter_ground_attack(self, key: str, dmg: int) -> None:
        self.attack_key = key
        self.attack_damage = dmg
        self.attack_active_window = True
        self._facing_locked = True
        self._set_state(STATE_ATTACK)
        self._play_anim(key, restart=True)
        if key == "attack_light":
            play_sfx("punch")
        else:
            play_sfx("kick")

    def _handle_attack(self, dt) -> None:
        self.attack_active_window = True
        self.velocity.x = self._apply_friction(self.velocity.x, dt, strong=True)
        if self.anim_finished:
            self._end_attack()

    def _end_attack(self) -> None:
        self.attack_active_window = False
        self._facing_locked = False
        self._set_state(STATE_IDLE if self.on_ground else STATE_FALL)
        self._play_anim("idle" if self.on_ground else "fall")

    def _enter_air_kick(self) -> None:
        self.attack_key = "air_attack"
        self.attack_damage = AIR_DAMAGE
        self.attack_active_window = True
        self._facing_locked = True
        self.velocity.y = min(self.velocity.y + AIR_KICK_LAUNCH_BOOST, 0.0)
        self.velocity.x = self.facing * AIR_KICK_H_DRIVE
        self._set_state(STATE_AIR_ATTACK)
        self._play_anim("air_attack", restart=True)
        play_sfx("kick")

    def _handle_air_attack(self, dt) -> None:
        self.attack_active_window = True
        self.velocity.x = self.facing * AIR_KICK_H_DRIVE
        g = GRAVITY * 1.15
        self.velocity.y = min(self.velocity.y + g * dt, MAX_FALL_SPEED)
        if self.on_ground:
            self._end_air_kick()

    def _end_air_kick(self) -> None:
        self.attack_active_window = False
        self._facing_locked = False
        self._set_state(STATE_LANDING)
        self.landing_timer = LANDING_RECOVERY
        self._play_anim("idle")
        self.velocity.x *= 0.3

    # =========================================================================
    # HIT
    # =========================================================================
    def _handle_hit(self, dt) -> None:
        self.velocity.x *= 0.85
        self.hit_timer -= dt
        if self.hit_timer <= 0:
            self._set_state(STATE_IDLE if self.on_ground else STATE_FALL)
            self._play_anim("idle" if self.on_ground else "fall")

    def take_damage(self, amount: int, attacker_x: float = None) -> None:
        if self.invuln_timer > 0.0:
            return
        if self.state == STATE_HIT:
            return

        self.hitstop_timer = HITSTOP_TIME
        self.hit_timer = HITSTUN_TIME
        self.invuln_timer = INVULN_AFTER_HIT

        if attacker_x is not None:
            self.facing = 1 if attacker_x > self.pos.x else -1

        push_dir = -self.facing
        knockback_speed = KNOCKBACK_BASE + amount * KNOCKBACK_PER_DAMAGE

        if amount >= KNOCKBACK_LAUNCH_DMG:
            self.velocity.x = push_dir * knockback_speed
            self.velocity.y = KNOCKBACK_LAUNCH_VY
            self.on_ground = False
        else:
            self.velocity.x = push_dir * knockback_speed

        self._facing_locked = False
        self._set_state(STATE_HIT)
        self._play_anim("hit", restart=True)
        play_sfx("hit")

    # =========================================================================
    # LANDING
    # =========================================================================
    def _handle_landing(self, dt) -> None:
        self.landing_timer -= dt
        if self.jump_buffer_timer > 0.0 or self.landing_timer <= 0.0:
            self._set_state(STATE_IDLE)
            self._play_anim("idle")

    def _on_land(self) -> None:
        if self.state == STATE_AIR_ATTACK:
            self._end_air_kick()
        elif self.state in (STATE_JUMP, STATE_FALL):
            if self.velocity.y > 400:
                self._set_state(STATE_LANDING)
                self.landing_timer = LANDING_RECOVERY
                self._play_anim("idle")
            else:
                self._set_state(STATE_IDLE)
                self._play_anim("idle")

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _set_state(self, new_state: str) -> None:
        if new_state == self.state:
            return
        self.state = new_state
        self.state_time = 0.0

    def _apply_friction(self, vx: float, dt: float, strong: bool = False) -> float:
        rate = GROUND_FRICTION * (4.0 if strong else 1.0)
        if abs(vx) <= rate * dt:
            return 0.0
        return vx - math.copysign(rate * dt, vx)

    # =========================================================================
    # DEBUG SHAPES
    # =========================================================================
    def _compute_debug_shapes(self) -> None:
        self.debug_hitboxes.clear()
        self.debug_hurtboxes.clear()
        frame = self._current_frame()
        if frame is None:
            return

        if self.attack_active_window:
            for hb in frame.hitboxes:
                self.debug_hitboxes.append(self._box_to_world(hb))

        if self.invuln_timer > 0.0:
            return

        for hu in frame.hurtboxes:
            self.debug_hurtboxes.append(self._box_to_world(hu))

    def _box_to_world(self, box: Box) -> pygame.Rect:
        frame = self._current_frame()
        if frame is None:
            return pygame.Rect(0, 0, 0, 0)
        px, py = frame.pivot
        cx = box.x + box.w / 2.0
        cy = box.y + box.h / 2.0
        rel_x = cx - px
        rel_y = cy - py
        if self.facing < 0:
            rel_x = -rel_x
        rel_x *= SPRITE_SCALE
        rel_y *= SPRITE_SCALE
        w = box.w * SPRITE_SCALE
        h = box.h * SPRITE_SCALE
        return pygame.Rect(
            int(self.pos.x + rel_x - w / 2),
            int(self.pos.y + rel_y - h / 2),
            int(w), int(h)
        )

    # =========================================================================
    # DRAW
    # =========================================================================
    def draw(self, screen: pygame.Surface, debug: bool = False) -> None:
        frame = self._current_frame()
        if frame is None:
            return
        src = frame.source_rect
        sx, sy, sw, sh = int(src.x), int(src.y), int(src.w), int(src.h)
        sub = self.atlas.subsurface(pygame.Rect(sx, sy, sw, sh))
        w = int(sw * SPRITE_SCALE)
        h = int(sh * SPRITE_SCALE)
        scaled = pygame.transform.scale(sub, (w, h))
        px, py = frame.pivot
        if self.facing >= 0:
            top_left_x = self.pos.x - px * SPRITE_SCALE
            scaled_draw = scaled
        else:
            top_left_x = self.pos.x - (src.w - px) * SPRITE_SCALE
            scaled_draw = pygame.transform.flip(scaled, True, False)
        top_left_y = self.pos.y - py * SPRITE_SCALE
        screen.blit(scaled_draw, (int(top_left_x), int(top_left_y)))

        if self.invuln_timer > 0.0 and int(self.invuln_timer * 20) % 2 == 0:
            flash = scaled_draw.copy()
            flash.fill((160, 160, 160), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(flash, (int(top_left_x), int(top_left_y)))

        if debug:
            for r in self.debug_hurtboxes:
                _draw_rect_alpha(screen, (0, 220, 255, 80), r, (0, 220, 255))
            for r in self.debug_hitboxes:
                _draw_rect_alpha(screen, (255, 40, 40, 120), r, (255, 40, 80))
            bounds = pygame.Rect(int(top_left_x), int(top_left_y), w, h)
            _draw_rect_outline(screen, (255, 255, 255), bounds, 1)
            pygame.draw.line(screen, (255, 255, 0),
                             (self.pos.x - 8, self.pos.y),
                             (self.pos.x + 8, self.pos.y), 2)
            pygame.draw.line(screen, (255, 255, 0),
                             (self.pos.x, self.pos.y - 8),
                             (self.pos.x, self.pos.y + 8), 2)


# =============================================================================
# DRAW HELPERS
# =============================================================================
def _draw_rect_alpha(screen, color, rect, outline):
    if rect.w <= 0 or rect.h <= 0:
        return
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    surf.fill(color)
    screen.blit(surf, rect.topleft)
    pygame.draw.rect(screen, outline, rect, 1)


def _draw_rect_outline(screen, color, rect, width):
    pygame.draw.rect(screen, color, rect, width)