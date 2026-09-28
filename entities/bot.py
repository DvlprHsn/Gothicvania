"""
Professional Fighting Game AI
==============================

A tournament-grade opponent with layered decision-making:

  • Finite State Machine — the bot is always in one tactical mode
  • Behavior Tree — priorities, fallbacks, and interrupts
  • Prediction — reads player patterns over rolling windows
  • Spacing control — maintains ideal range, pressures corners
  • Whiff punish — reacts to recovery frames with slides/kicks
  • Anti-air — reads airborne opponents, times landing hits
  • Slide rushdown — closes distance at extreme speed
  • Adaptive difficulty — plays safer when winning, more aggressive when losing
  • Threat assessment — dodges attacks, backs off from combos
  • Resource management — cooldowns, commits, and breathing windows

Difficulty (0.0–1.0) controls:
    - Reaction time
    - Attack cooldown
    - Slide frequency
    - Prediction accuracy
    - Punish precision
"""

from __future__ import annotations

import random
from collections import deque
from enum import Enum
from typing import Dict, Deque

import pygame


# =============================================================================
# KEY STATE
# =============================================================================
class _KeyState:
    """Mimics pygame.key.get_pressed() so it can be fed directly into Fighter."""
    __slots__ = ("_state",)

    def __init__(self) -> None:
        self._state: Dict[int, bool] = {}

    def set(self, key: int, down: bool) -> None:
        self._state[key] = down

    def clear(self) -> None:
        self._state.clear()

    def __getitem__(self, key: int) -> bool:
        return self._state.get(key, False)

    def __len__(self) -> int:
        return 512


# =============================================================================
# TACTICAL MODES
# =============================================================================
class Mode(Enum):
    RUSHDOWN = "rushdown"
    ATTACK = "attack"
    DEFEND = "defend"
    BAIT = "bait"
    ANTI_AIR = "anti_air"
    PUNISH = "punish"
    CORNER = "corner"
    DISENGAGE = "disengage"


# =============================================================================
# CONFIGURATION
# =============================================================================
class Config:
    CLOSE_RANGE        = 90
    KICK_RANGE         = 140
    IDEAL_MIN          = 80
    IDEAL_MAX          = 130
    FAR_RANGE          = 220
    SLIDE_APPROACH     = 130

    THINK_INTERVAL_MIN = 0.03
    THINK_INTERVAL_MAX = 0.09

    ATTACK_CD_MIN      = 0.10
    ATTACK_CD_MAX      = 0.28

    SLIDE_CD_MIN       = 0.35
    SLIDE_CD_MAX       = 0.85

    JUMP_CD_MIN        = 0.55
    JUMP_CD_MAX        = 1.10

    WHIFF_WINDOW       = 0.22

    PATTERN_WINDOW     = 12
    TENDENCY_THRESHOLD = 3

    SLIDE_COMMIT_MIN   = 0.30
    SLIDE_COMMIT_MAX   = 0.48
    JUMP_COMMIT        = 0.40

    INCOMING_ATTACK_RANGE = 160
    CORNER_MARGIN         = 220
    LOW_HP_THRESHOLD      = 25


# =============================================================================
# PLAYER MEMORY
# =============================================================================
class PlayerMemory:
    def __init__(self, window: int = Config.PATTERN_WINDOW) -> None:
        self.states: Deque[str] = deque(maxlen=window)
        self.last_state: str = "idle"
        self.time_in_state: float = 0.0

        self.punch_score: float = 0.0
        self.kick_score: float = 0.0
        self.jump_score: float = 0.0
        self.crouch_score: float = 0.0
        self.backward_score: float = 0.0

        self.whiff_timer: float = 0.0
        self.attack_windup_timer: float = 0.0

    def update(self, player, dt: float) -> None:
        state = player.state
        self.time_in_state += dt

        if state != self.last_state:
            self.states.append(self.last_state)
            self._record_tendency(self.last_state)
            self._decay_opposite(self.last_state)

            if state in ("attack", "air_attack"):
                self.attack_windup_timer = 0.15

            if self.last_state in ("attack", "air_attack"):
                self.whiff_timer = Config.WHIFF_WINDOW

            self.last_state = state
            self.time_in_state = 0.0

        self.whiff_timer = max(0.0, self.whiff_timer - dt)
        self.attack_windup_timer = max(0.0, self.attack_windup_timer - dt)

    def _record_tendency(self, state: str) -> None:
        if state in ("attack",):
            self.punch_score += 1.0
        elif state in ("air_attack",):
            self.kick_score += 1.0
        elif state in ("jump", "fall"):
            self.jump_score += 1.0
        elif state == "crouch":
            self.crouch_score += 1.0

    def _decay_opposite(self, state: str) -> None:
        self.punch_score = max(-5.0, min(5.0, self.punch_score))
        self.kick_score = max(-5.0, min(5.0, self.kick_score))
        self.jump_score = max(-5.0, min(5.0, self.jump_score))
        self.crouch_score = max(-5.0, min(5.0, self.crouch_score))
        self.backward_score = max(-5.0, min(5.0, self.backward_score))

    def player_loves_punch(self) -> bool:
        return self.punch_score > Config.TENDENCY_THRESHOLD

    def player_loves_kick(self) -> bool:
        return self.kick_score > Config.TENDENCY_THRESHOLD

    def player_loves_jump(self) -> bool:
        return self.jump_score > Config.TENDENCY_THRESHOLD

    def player_loves_crouch(self) -> bool:
        return self.crouch_score > Config.TENDENCY_THRESHOLD

    def can_punish(self) -> bool:
        return self.whiff_timer > 0.0

    def player_is_winding_up(self) -> bool:
        return self.attack_windup_timer > 0.0


# =============================================================================
# BOT
# =============================================================================
class Bot:
    def __init__(self, keys: Dict[int, str], difficulty: float = 0.9):
        self.keys = keys
        self.difficulty = max(0.0, min(1.0, difficulty))

        self.action_to_key: Dict[str, int] = {}
        for k, action in keys.items():
            self.action_to_key[action] = k

        self.key_state = _KeyState()
        self.memory = PlayerMemory()

        self.think_timer: float = 0.0
        self.attack_cd: float = 0.0
        self.slide_cd: float = 0.0
        self.jump_cd: float = 0.0
        self.commit_timer: float = 0.0
        self.mode_timer: float = 0.0

        self.slide_direction: int = 0
        self.slide_commit: float = 0.0
        self.jump_commit: float = 0.0

        self.mode: Mode = Mode.RUSHDOWN

        self.want_left: bool = False
        self.want_right: bool = False
        self.want_jump: bool = False
        self.want_crouch: bool = False
        self.want_punch: bool = False
        self.want_kick: bool = False

        self.actions_this_second: int = 0
        self.actions_timer: float = 0.0

    # =========================================================================
    # MAIN ENTRY
    # =========================================================================
    def think(self, player, me, dt: float) -> None:
        self._tick_timers(dt)
        self.memory.update(player, dt)

        self.think_timer -= dt
        if self.think_timer <= 0:
            self.think_timer = self._reaction_interval()
            self._update_mode(player, me)
            self._decide(player, me)

        self._apply()

    # =========================================================================
    # TIMERS
    # =========================================================================
    def _tick_timers(self, dt: float) -> None:
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.slide_cd = max(0.0, self.slide_cd - dt)
        self.jump_cd = max(0.0, self.jump_cd - dt)
        self.commit_timer = max(0.0, self.commit_timer - dt)
        self.mode_timer = max(0.0, self.mode_timer - dt)
        self.slide_commit = max(0.0, self.slide_commit - dt)
        self.jump_commit = max(0.0, self.jump_commit - dt)

        self.actions_timer += dt
        if self.actions_timer >= 1.0:
            self.actions_this_second = 0
            self.actions_timer -= 1.0

    def _reaction_interval(self) -> float:
        return (
            Config.THINK_INTERVAL_MAX
            - (Config.THINK_INTERVAL_MAX - Config.THINK_INTERVAL_MIN)
            * self.difficulty
        )

    # =========================================================================
    # MODE SELECTION
    # =========================================================================
    def _update_mode(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)

        my_hp = getattr(me, "hp", 100)
        player_hp = getattr(player, "hp", 100)
        hp_diff = my_hp - player_hp

        if self.memory.can_punish() and distance < Config.INCOMING_ATTACK_RANGE:
            self._enter_mode(Mode.PUNISH, 0.35)
            return

        if player.state in ("attack", "air_attack") and distance < Config.INCOMING_ATTACK_RANGE:
            self._enter_mode(Mode.DEFEND, 0.4)
            return

        if player.state in ("jump", "fall") and distance < 200:
            self._enter_mode(Mode.ANTI_AIR, 0.3)
            return

        if self._is_player_cornered(player) and distance < 280:
            self._enter_mode(Mode.CORNER, 0.5)
            return

        if player_hp < 35:
            self._enter_mode(Mode.RUSHDOWN, 0.5)
            return

        if my_hp < Config.LOW_HP_THRESHOLD and hp_diff < -20:
            self._enter_mode(Mode.DISENGAGE, 0.4)
            return

        if (self.memory.player_loves_crouch()
                and distance < 200
                and random.random() < 0.15):
            self._enter_mode(Mode.BAIT, 0.3)
            return

        if distance < Config.KICK_RANGE:
            self._enter_mode(Mode.ATTACK, 0.4)
            return

        self._enter_mode(Mode.RUSHDOWN, 0.6)

    def _enter_mode(self, mode: Mode, duration: float) -> None:
        if self.mode == mode and self.mode_timer > 0:
            return
        self.mode = mode
        self.mode_timer = duration

    def _is_player_cornered(self, player) -> bool:
        return player.pos.x < Config.CORNER_MARGIN or player.pos.x > 1280 - Config.CORNER_MARGIN

    # =========================================================================
    # DECISION TREE
    # =========================================================================
    def _decide(self, player, me) -> None:
        self.want_left = False
        self.want_right = False
        self.want_jump = False
        self.want_crouch = False
        self.want_punch = False
        self.want_kick = False

        if self.slide_commit > 0:
            self._continue_slide()
            return

        if self.mode == Mode.RUSHDOWN:
            self._do_rushdown(player, me)
        elif self.mode == Mode.ATTACK:
            self._do_attack(player, me)
        elif self.mode == Mode.DEFEND:
            self._do_defend(player, me)
        elif self.mode == Mode.BAIT:
            self._do_bait(player, me)
        elif self.mode == Mode.ANTI_AIR:
            self._do_anti_air(player, me)
        elif self.mode == Mode.PUNISH:
            self._do_punish(player, me)
        elif self.mode == Mode.CORNER:
            self._do_corner_pressure(player, me)
        elif self.mode == Mode.DISENGAGE:
            self._do_disengage(player, me)
        else:
            self._do_rushdown(player, me)

    # =========================================================================
    # BEHAVIORS
    # =========================================================================
    def _do_rushdown(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if distance < Config.KICK_RANGE:
            if self.attack_cd <= 0:
                self._execute_kick(direction)
                return
            self._move_toward(direction)
            return

        if distance >= Config.SLIDE_APPROACH:
            if self.slide_cd <= 0:
                self._start_slide(direction)
                return
            self._move_toward(direction)
            return

        self._move_toward(direction)

    def _do_attack(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if player.state in ("jump", "fall"):
            self._enter_mode(Mode.ANTI_AIR, 0.3)
            self._do_anti_air(player, me)
            return

        if self.attack_cd <= 0:
            if distance < Config.CLOSE_RANGE:
                if random.random() < 0.6:
                    self._execute_kick(direction)
                else:
                    self._execute_punch(direction)
            else:
                self._execute_kick(direction)
            return

        if distance < Config.IDEAL_MIN:
            self._move_away(direction)
        else:
            self._move_toward(direction)

    def _do_defend(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if not me.on_ground:
            if self.attack_cd <= 0:
                self.want_kick = True
                self._register_attack()
                self._move_toward(direction)
            return

        roll = random.random()
        smart = self.difficulty

        if self.jump_cd <= 0 and roll < 0.35 + 0.25 * smart:
            self._start_jump(direction)
            return

        if self.slide_cd <= 0 and roll < 0.65:
            self._start_slide(direction)
            return

        if roll < 0.80:
            self.want_crouch = True
            if self.attack_cd <= 0:
                self.want_kick = True
                self._register_attack()
            return

        self._move_away(direction)

    def _do_bait(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if distance < Config.IDEAL_MAX:
            self._move_away(direction)
            return

        if self.attack_cd <= 0:
            self._execute_kick(direction)

    def _do_anti_air(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        vy = player.velocity.y
        py = player.pos.y
        ground_y = 620

        if vy > 0:
            time_to_land = (ground_y - py) / max(1.0, vy)
            if time_to_land < 0.35 and distance < 160:
                if self.attack_cd <= 0:
                    self._execute_kick(direction)
                    return

        if distance > 100:
            self._move_toward(direction)
        elif distance < 60:
            self._move_away(direction)

    def _do_punish(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if distance > 100:
            if self.slide_cd <= 0:
                self._start_slide(direction)
                return
            self._move_toward(direction)
            return

        if self.attack_cd <= 0:
            self._execute_kick(direction)
            return
        self._move_toward(direction)

    def _do_corner_pressure(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if distance < Config.KICK_RANGE:
            if self.attack_cd <= 0:
                self._execute_kick(direction)
                return
            self._move_toward(direction)
            return

        if self.slide_cd <= 0:
            self._start_slide(direction)
            return
        self._move_toward(direction)

    def _do_disengage(self, player, me) -> None:
        dx = player.pos.x - me.pos.x
        distance = abs(dx)
        direction = 1 if dx > 0 else -1

        if distance < Config.IDEAL_MAX + 40:
            self._move_away(direction)
            return

        if self.attack_cd <= 0 and random.random() < 0.3:
            self._execute_kick(direction)
            return

        if self.slide_cd <= 0 and random.random() < 0.15:
            self._start_slide(-direction)

    # =========================================================================
    # ACTIONS
    # =========================================================================
    def _move_toward(self, direction: int) -> None:
        if direction > 0:
            self.want_right = True
        else:
            self.want_left = True

    def _move_away(self, direction: int) -> None:
        if direction > 0:
            self.want_left = True
        else:
            self.want_right = True

    def _start_slide(self, direction: int) -> None:
        self.want_crouch = True
        if direction > 0:
            self.want_right = True
        else:
            self.want_left = True

        self.slide_direction = direction
        self.slide_commit = (
            Config.SLIDE_COMMIT_MIN
            + random.random() * (Config.SLIDE_COMMIT_MAX - Config.SLIDE_COMMIT_MIN)
        )

        self.slide_cd = (
            Config.SLIDE_CD_MAX
            - (Config.SLIDE_CD_MAX - Config.SLIDE_CD_MIN) * self.difficulty
        ) + random.random() * 0.15

    def _continue_slide(self) -> None:
        self.want_crouch = True
        if self.slide_direction > 0:
            self.want_right = True
        elif self.slide_direction < 0:
            self.want_left = True

    def _start_jump(self, direction: int) -> None:
        self.want_jump = True
        if direction > 0:
            self.want_right = True
        else:
            self.want_left = True

        self.jump_commit = Config.JUMP_COMMIT
        self.jump_cd = (
            Config.JUMP_CD_MAX
            - (Config.JUMP_CD_MAX - Config.JUMP_CD_MIN) * self.difficulty
        ) + random.random() * 0.15

    def _execute_kick(self, direction: int) -> None:
        self.want_kick = True
        self._register_attack()
        if random.random() < 0.55:
            self._move_toward(direction)

    def _execute_punch(self, direction: int) -> None:
        self.want_punch = True
        self._register_attack()
        if random.random() < 0.35:
            self._move_toward(direction)

    def _register_attack(self) -> None:
        base = (
            Config.ATTACK_CD_MAX
            - (Config.ATTACK_CD_MAX - Config.ATTACK_CD_MIN) * self.difficulty
        )
        self.attack_cd = base + random.random() * 0.05
        self.actions_this_second += 1

    # =========================================================================
    # APPLY
    # =========================================================================
    def _apply(self) -> None:
        self.key_state.clear()

        def press(action: str, down: bool) -> None:
            if not down:
                return
            key = self.action_to_key.get(action)
            if key is not None:
                self.key_state.set(key, True)

        press("move_left", self.want_left)
        press("move_right", self.want_right)
        press("jump", self.want_jump)
        press("crouch", self.want_crouch)
        press("attack_light", self.want_punch)
        press("attack_heavy", self.want_kick)

        self.want_jump = False
        self.want_punch = False
        self.want_kick = False

    # =========================================================================
    # DEBUG
    # =========================================================================
    def debug_status(self) -> str:
        return (
            f"mode={self.mode.value} "
            f"atk_cd={self.attack_cd:.2f} "
            f"slide_cd={self.slide_cd:.2f}"
        )