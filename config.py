"""
Central configuration — every tuning constant lives here.
"""

# ---------------------------------------------------------------------------
# Window / core
# ---------------------------------------------------------------------------
WINDOW_W = 1280
WINDOW_H = 720
FPS = 60
GROUND_Y = 620
ROUND_TIME = 60.0
COUNTDOWN_TIME = 3.0
MAX_HP = 100
HIT_COOLDOWN = 0.55

# ---------------------------------------------------------------------------
# Camera / background
# ---------------------------------------------------------------------------
SCREEN_MARGIN = 120
CAMERA_LEAD = 100
BACKGROUND_ZOOM = 0.92

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_TWO_PLAYERS = False
AI_DIFFICULTY = 0.7
MUSIC_VOLUME = 0.4

# ---------------------------------------------------------------------------
# Paths (relative to the data/ folder)
# ---------------------------------------------------------------------------
DATA_DIR = "data"

ATLAS_FILE = "spritesheet.png"
SPRITE_BOXES_FILE = "sprite_boxes.json"
BACKGROUND_FILE = "background.png"
SPLASH_FILE = "background_splash.png"
ICON_FILE = "icon.png"
GROUND_PROP_FILE = "ground_prop.png"

MUSIC_DIR = "music"
SFX_DIR = "sounds"

MUSIC_CANDIDATES = [
    "music/theme.ogg",
    "music/theme.mp3",
    "music/theme.wav",
    "music/bgm.ogg",
    "theme.ogg",
    "music.ogg",
]

SFX_FILES = {
    "punch": ("punch.ogg", (600, 200, 0.08, 0.35)),
    "kick":  ("kick.ogg",  (400, 120, 0.12, 0.40)),
    "hit":   ("hit.ogg",   (180, 60,  0.10, 0.45)),
    "ko":    ("ko.ogg",    (300, 40,  0.60, 0.55)),
    "jump":  ("jump.ogg",  (300, 700, 0.10, 0.30)),
}

# ---------------------------------------------------------------------------
# Input maps
# ---------------------------------------------------------------------------
import pygame

P1_KEYS = {
    pygame.K_LEFT:  "move_left",
    pygame.K_RIGHT: "move_right",
    pygame.K_UP:    "jump",
    pygame.K_DOWN:  "crouch",
    pygame.K_n:     "attack_light",
    pygame.K_b:     "attack_heavy",
}

P2_KEYS = {
    pygame.K_a:  "move_left",
    pygame.K_d:  "move_right",
    pygame.K_w:  "jump",
    pygame.K_s:  "crouch",
    pygame.K_z:  "attack_light",
    pygame.K_x:  "attack_heavy",
}