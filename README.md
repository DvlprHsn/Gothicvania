# Gothicvania Church Fighter

A gothic-themed 2-player fighting game built with **Pygame**. Play solo against a tournament-grade AI or fight a friend on the same keyboard.

```
Splash  →  Menu  →  3-2-1-FIGHT  →  KO  →  Splash
```

---

## Features

- **Two modes** — SinglePlayer (vs Bot) or Multiplayer (2P local)
- **Tournament-grade AI** — Finite State Machine + Behavior Tree + pattern prediction
- **Adaptive difficulty** — bot plays safer when winning, more aggressive when losing
- **TAB toggle** — swap Player 2 between human and bot *mid-match*
- **Gothic purple UI** — ornate health bars, timer, K.O. overlay
- **Real fighting-game physics** — knockback, hitstun, hit-stop, invulnerability windows
- **Input forgiveness** — coyote time, input buffering, jump-cut
- **Crouch slide** with animation speed-up
- **Air kick** with looping hitbox
- **Smooth lead-tracking camera**
- **Debug overlay** — hitboxes, hurtboxes, state labels (F1 / F2)
- **Procedural fallback SFX** — runs even without sound files

---

## Requirements

- **Python 3.9+** (3.11 or 3.12 recommended)
- **pygame 2.5.0+**

Everything else is Python standard library.

---

## Setup

### 1. Get the files

Clone or copy the project folder. The layout should be:

```
gothicvania/
├── main.py
├── config.py
├── audio.py
├── assets.py
├── ui.py
├── camera.py
├── debug_overlay.py
├── requirements.txt
├── README.md
├── .gitignore
├── entities/
│   ├── __init__.py
│   ├── fighter.py
│   └── bot.py
├── screens/
│   ├── __init__.py
│   ├── splash.py
│   └── menu.py
└── data/
    ├── atlas.png
    ├── sprite_boxes.json
    ├── background.png
    ├── background_splash.png
    ├── icon.png
    ├── ground_prop.png
    ├── music/
    │   └── theme.ogg
    └── sounds/
        ├── punch.ogg
        ├── kick.ogg
        ├── hit.ogg
        ├── ko.ogg
        └── jump.ogg
```

### 2. Create a virtual environment (recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If you're on **Python 3.13+** or want better performance, use the Community Edition instead:

```bash
pip install pygame-ce
```

> Do **not** install both `pygame` and `pygame-ce` at the same time.

### 4. Add your assets to `data/`

| File | Purpose | Required? |
|---|---|---|
| `atlas.png` | Fighter sprite sheet | ✅ Yes |
| `sprite_boxes.json` | Hitbox/hurtbox data for the atlas | ✅ Yes |
| `background.png` | Stage backdrop | ⬜ Optional (gradient fallback) |
| `background_splash.png` | Splash screen image | ⬜ Optional |
| `icon.png` | Window icon | ⬜ Optional |
| `ground_prop.png` | **Single tileable ground strip** | ⬜ Optional (solid fallback) |
| `music/theme.ogg` | Looping background music | ⬜ Optional |
| `sounds/*.ogg` | Sound effects | ⬜ Optional (procedural fallback) |

### 5. Run

```bash
python main.py
```

---

## Controls

### Player 1
| Action | Key |
|---|---|
| Move left / right | ← / → |
| Jump | ↑ |
| Crouch | ↓ |
| Light attack (punch) | N |
| Heavy attack (kick) | B |

### Player 2
| Action | Key |
|---|---|
| Move left / right | A / D |
| Jump | W |
| Crouch | S |
| Light attack (punch) | Z |
| Heavy attack (kick) | X |

### Global
| Action | Key |
|---|---|
| Toggle P2 human ↔ bot | **TAB** |
| Toggle music mute | **M** |
| Toggle hitboxes | **F1** |
| Toggle state labels | **F2** |
| Restart (after KO) | **R** |
| Quit | **ESC** |

---

## Gameplay tips

- **Crouch while moving** to trigger a slide — closes distance fast and can pass under high attacks.
- **Heavy attacks** in the air become **flying kicks** — huge horizontal drive, great for cross-ups.
- **Light attacks** are faster and safer; **heavy attacks** launch opponents on impact.
- Landing a hit gives the attacker a **hit-stop freeze** for impact feel, and gives the defender an **invulnerability window** so they can't be chain-locked.
- The bot's **difficulty** can be tuned in `config.py` (`AI_DIFFICULTY = 0.7`). `0.0` = slow and forgiving, `1.0` = tournament-grade reaction speed.

---

## Audio notes

- On minimal Linux installs you may need SDL mixer libraries:
  ```bash
  sudo apt install libsdl2-mixer-2.0-0
  ```
- Missing SFX files are automatically replaced with **procedural square-wave beeps**, so the game remains fully playable without any audio assets.
- Press **M** at any time to toggle music mute.

---

## Project structure explained

| File | Responsibility |
|---|---|
| `main.py` | Entry point — game loop, state machine (splash → menu → fight → ko) |
| `config.py` | Every tuning constant (window size, speeds, keys, paths) |
| `audio.py` | SFX loading, procedural fallback synthesis, music manager |
| `assets.py` | Atlas / background / ground prop / splash / icon loading |
| `ui.py` | Palette, panels, health bars, timer, countdown, KO overlay |
| `camera.py` | Smooth lead-tracking camera clamped to world bounds |
| `debug_overlay.py` | Hitbox/hurtbox/state-label debug renderer |
| `entities/fighter.py` | Sprite-driven fighting character |
| `entities/bot.py` | Tournament-grade AI opponent |
| `screens/splash.py` | Fade-in/out splash screen |
| `screens/menu.py` | Single-player / Multiplayer menu |

Everything is decoupled — you can swap in a new ground prop by replacing `data/ground_prop.png`, tune balance from `config.py`, or rewrite the AI in `entities/bot.py` without touching anything else.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'pygame'`**
Run `pip install -r requirements.txt` inside the same Python environment you're running the game from.

**Window opens and closes immediately**
You're probably missing `data/atlas.png` or `data/sprite_boxes.json`. The game prints a clear error before exiting — check the terminal output.

**No sound**
Either your audio files are missing (procedural fallbacks will still play), or SDL_mixer isn't installed. On Linux: `sudo apt install libsdl2-mixer-2.0-0`.

**Sprite is drawn at the wrong offset**
The atlas JSON uses a `pivot` per frame. If sprites float or sink, re-export `sprite_boxes.json` with the pivot set at the character's feet.

**Game runs slow**
Cap FPS in `config.py` (`FPS = 60`) — the game already clamps `dt` at 0.05s to prevent physics explosions on lag spikes.

---

## License

Personal project. Do whatever you want with it.