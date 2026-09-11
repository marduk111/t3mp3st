# THEATRE OF SORROW - Marduk vs The Beast

The debut-album-as-a-game from the band Belligerent Dickhead: a horror RPG where their singer, Marduk, falls through the floor during a gig and must fight through hell to finish the set.

---

# FOR TESTERS

## Quick Start

Clone it, run one command, play:

```
git clone https://github.com/marduk111/theatre-of-sorrow.git
cd theatre-of-sorrow
```

- **Windows, no terminal needed:** double-click **`run.bat`** (full game) or **`run_demo.bat`** (repeatable battle-sandbox). It creates a private environment and installs pygame-ce for you on first launch.
- **Linux/macOS, same one-command bootstrap:** `bash run.sh` (full game) or `bash run_demo.sh` (battle sandbox). On Linux with executable permissions set you can also run `./run.sh`.

**Why a private environment?** On modern Debian/Ubuntu (and many other distros), Python is marked **"externally managed" (PEP 668)** and refuses system-wide `pip install` on purpose — that protects your OS tools. The launchers above create a `.venv` folder inside the game folder and install everything there, so your other Python apps stay untouched and you never hit dependency hell.

### Manual steps (Python-savvy)

The launchers do exactly this:

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

(On Windows: `.venv\Scripts\python ...` with `python` instead of `python3`.)

If `python3 -m venv` itself fails with "ensurepip is not available", install the venv module first: `sudo apt install python3-venv` (Debian/Ubuntu; the game needs a system Python 3.11, which the distro package `python3.11-venv` or `python3-full` provides). On Fedora/Arch/macOS the venv module ships with Python.

### Requirements

- **Python 3.11** and **pygame-ce** (`pip install -r requirements.txt` installs it).
- Verified working combo on Windows: `python 3.11` + `pygame-ce 2.5.8`.
- The game saves to `save.json` in the same folder (freely deletable for a clean start).
- Fullscreen toggle: **F11** (works anywhere, even mid-battle).
- Mute audio: **M**.

**Found a bug?** Record how you got there (keys pressed, what you saw) — the developer would love a minimal repro.

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move |
| SPACE / ENTER | Interact / Talk / Advance dialogue |
| I | Inventory |
| H | Help guide (controls + mechanics) |
| F | Scream (heal when GRIT is full) |
| M | Mute audio |
| F11 | Toggle fullscreen |
| F5 | Save game |
| ESC | Menu / Back |

Combat (stage-defense battle mode):

| Key | Action |
|-----|--------|
| Mouse | Click a band member to select them; click an enemy to attack; use the panel buttons for END TURN, towers, groupies, and Azrael's skills |
| ESC | Pause / resume |
| R | Restart the current battle |
| Q | Retreat back to the room |
| ENTER | Confirm when a battle ends (win / loss / retreat) |

A hints bar at the bottom of the battle screen always shows these keys.

## The Game

You roam a 7-room hell-venue trying to escape. Fights use **Stage Fright Tactics**, a turn-based stage-defense battler (AP per unit, GRIT economy, watchtowers, groupies, band XP, Azrael's line-blaster skills) — the same engine also runs standalone as `rts_demo.py`. Rooms, story beats, and every system are described in detail below the Developer sections.

Everything is procedurally generated — there are **no asset downloads**; a fresh clone boots straight to the menu. Drop-in custom portraits, music, and animations are documented in the **Customizing assets** section.

Press **H** in-game for the full cheat sheet.

---

# FOR DEVELOPERS

Everything a tester doesn't need. Most of this assumes you're editing `main.py`.

## Code Layout

| File | Purpose |
|------|---------|
| `main.py` | The RPG: menu, rooms, NPCs, dialogue, cutscenes, portraits, audio slots, asset manifest generation |
| `rts_demo.py` | Standalone Stage Fright Tactics battler (also the battle engine) |
| `battle_bridge.py` | Wires the RPG combat into the demo (`BattleBridge`) |
| `fxkit.py` | Small screen-effects helpers |
| `requirements.txt` | Only dependency: `pygame-ce>=2.5` |
| `ASSET_MANIFEST.md` | Auto-generated asset checklist (see Customizing assets) |
| `run.bat`/`run.sh`, `run_demo.bat`/`run_demo.sh` | One-click venv bootstrap launchers |

Key objects: `Game` (world + flow), `CutsceneSystem` (dialogue + reels), `SoundManager` (music/voice slots), `PortraitSystem`, `Reel` (frame-sequence player), `battle_bridge.BattleBridge`.

## Adding Content

Edit `setup_rooms()` in `main.py`. Each room is a 20x15 tile grid:
- `enemies`: list of `{"x", "y", "type", "hp", "defense", "interact", "boss"(optional)}`
- `items`: list of `{"x", "y", "type", "active", "interact"}`
- `npcs`: list of `{"x", "y", "color", "name", "interact"}`
- `doors`: list of `{"x", "y", "target", "spawn_x", "spawn_y", "requires_flag"(optional), "requires_item"(optional), "locked_msg"(optional)}`
- `objective`: string shown at top of screen as current room objective

Enemy types: `demon`, `zombie`, `corpse`, `shadow`, `engineer`, `beast` (final boss)
Item types: `beer`, `microphone`, `key`, `weapon`, `health`, `blood`, `tome`
Door requirements: `requires_flag` (story flag must be True), `requires_item` (item must be in inventory)

**Progression data**: enemies accept an optional `xp` override (defaults from the built-in table per type). The `Player` tracks `level`, `xp`, `xp_to_next`, and `skills`. Ability definitions live in the `SKILLS` dict near the top of `main.py`. Skills cost `grit` or `sanity`. To add a new ability, add it to `SKILLS` (with `unlock_level` = auto-tier or `None` for tome-only), add a `tome_<id>` handler in `interact_item`, and drop the items/NPCs that grant it.

To add dialogue, create new interaction handlers in the `Game` class following the pattern of `_roadie_choice` or `interact_item`.

## Adding a New Animation Moment (Reel)

1. Add an entry to `REEL_MOMENTS` near the top of `main.py`: `"<key>": "When this plays"`.
2. Add the same key to `SoundManager.MUSIC_SLOTS` if you also want a song/voice slot, and to `SoundManager.BATTLE_SLOTS` if it's a pre-fight beat.
3. Add a row to the manifest moment dict (the one passed to `generate_asset_manifest`).
4. Wire the cutscene trigger where the moment should fire — `after_intro` for `fall`, `_engage_enemy` for fights, `transition_to` callback for room-entry, etc. See `CutsceneSystem.start` for the reel options below.
5. Drop frames into `assets/animations/<key>/` and (optionally) a clip into `assets/music/<key>.<ext>`.
6. Launch and check `ASSET_MANIFEST.md` — the new row flips to `READY` once files are detected.

### Cutscene reel options (`CutsceneSystem.start`)

- **Default** (`reel_lines=(...)`): the reel runs *under* the dialogue text at the given line indexes — used by `fall`, `chamber`, `ending`.
- **`reel_after=True`**: dialogue first (with per-speaker portraits), then a **fullscreen reel phase** with no text, then the `callback` fires (typical: the battle starts). Used by every pre-battle cutscene. Room music **stops when the cutscene begins**; `reel_voice="<slot>"` (optional) plays the matching music-slot clip **once on its own channel** during the reel — it never loops and is cut off when `stop_music()` runs at battle start. A clip whose length matches the animation (~frames ÷ 30) lands in near-perfect sync (e.g. the 240-frame zombie reel is 8.0 s and the shipped `zombie.mp3` is ~7.9 s).
- ENTER/SPACE skips the reel phase early.

**Pre-battle flow today:** engage enemy → room music stops → dialogue with portraits (silent, focused) → click past the last page → fullscreen reel + one-shot voice → battle starts with the combat playlist. Each enemy type and both bosses (`beast`, `pit_lord`) have their own reel key and voice slot waiting for your clips.

## Adding a New Music Slot

Music is **moment-based**: each event looks for `assets/music/<slot>.<ext>`. Add the slot name to `SoundManager.MUSIC_SLOTS`, and to `BATTLE_SLOTS` if it's a pre-fight beat, then wire a play/`reel_voice` call where it should fire. Numbered names work: `01-stage.mp3` = `stage.mp3`.

- Files found → played from disk.
- `menu`/`intro`/visual beats with no file → built-in procedural audio or silence. The game never crashes on a missing track.
- **`play_ambient`** loops a file on the main music stream (rooms, menus).
- **`play_voice`** plays a slot clip **once on its own channel**, layered over whatever's already playing (reel voices — see above).
- **Combat playlists**: drop `combat1.mp3`, `combat2.mp3`, ... (and `boss1.mp3`, ...) to rotate battle music so no fight sounds identical.

A "Now Playing" readout shows the current file at the top of the screen when a track changes.

## Save System

Press F5 to save. Progress is written to `save.json` inside the project folder. Load from the main menu. Tutorial flags and story flags persist across saves, along with level, XP, unlocked abilities, upgraded stats, and inventory.

## Converting MP4 to Animation Frames

Drop an MP4 anywhere and convert it to a numbered PNG sequence the game picks up automatically:

```
mkdir assets\animations\<key>
ffmpeg -i myclip.mp4 -vf "fps=30,scale=1024:768:flags=lanczos" assets\animations\<key>\%04d.png
```

`<key>` is any moment from the Animations table below. Frames are read in numeric order (`0001.png`, `0002.png`, ...) and played one per tick at 30 FPS. Omit `scale=1024:768:flags=lanczos` to keep the source size — the game auto-stretches whatever you give it.

## Sharing with Testers

Push to `https://github.com/marduk111/theatre-of-sorrow`, then send the link. Testers run the Quick Start steps above. Save files (`save.json`) and per-user custom art/music they drop into `assets/` are local — they're not committed unless you choose to commit them. Tester feedback lives in the conversation / issue tracker, not in the repo docs.

---

# GAME & ASSET REFERENCE

## Customizing assets (everyone can do this)

There's a **live asset manifest**: launch once and check **`ASSET_MANIFEST.md`** in the project folder. It regenerates on every start/load and lists every portrait, music slot, and animation clip with live status (`missing`/`found`, `PLACEHOLDER`/`CUSTOM`, `READY (N frames)`/`NO FRAMES`). **You never edit it by hand** — it's a checklist your files fill in.

### Portraits (Placeholder Art)

Every character, enemy, and item has a portrait that appears beside dialogue, in battle, and on objective reveals — currently **generated placeholder pixel art**, so the game looks complete with zero external files. Drop in real artwork as `<key>.png`:

- `player.png` — Marduk, the band's singer
- `azrael.png` — AZRAEL D DESTROYER, the band's cat-god narrator and ranged weapon
- `zombie.png`, `corpse.png`, `shadow.png`, `demon.png`, `engineer.png`, `beast.png` — enemies
- `roadie.png`, `last_roadie.png`, `sketchy_vendor.png` — NPCs
- `beer.png`, `mic.png`, `crypt_key.png`, `broken_bottle.png`, `guitaraxe.png`, `tome_double_down.png`, etc. — items (full list in **ASSET_MANIFEST.md**)

Any PNG matching a portrait key replaces the placeholder automatically. Recommended size: 160x160 (any source resolution works; larger masters downscale cleanly). Keys are lowercased with spaces replaced by underscores (e.g. NPC "Last Roadie" → `last_roadie.png`).

### Music slots

Folder: `assets/music/`.  File: `<slot>.mp3` (or `.ogg` / `.wav`).  Numbered variants work: `01-stage.mp3` = `stage.mp3`.

**Prefer `.ogg` for anything that loops** (rooms + battles): MP3 carries roughly 25-50 ms of encoder padding that re-applies at each loop and can cause an audible hiccup. OGG Vorbis stores sample-accurate tags, so it loops seamlessly under pygame. If you must export MP3, encode gapless (LAME `--nogap`), trim leading/trailing silence, and cut the loop at a zero crossing. `.wav` also loops cleanly but is much larger.

| Slot | File | Plays when |
|---|---|---|
| menu | `menu.mp3` | Main menu |
| intro | `intro.mp3` | Opening cutscene |
| stage | `stage.mp3` | The Stage of Sin |
| backstage | `backstage.mp3` | Backstage Gore |
| merch | `merch.mp3` | The Merch Table of Madness |
| pit | `pit.mp3` | The Mosh Pit of Souls |
| greenroom | `greenroom.mp3` | The Green Room of Vile |
| booth | `booth.mp3` | The Sound Booth of Despair |
| chamber | `chamber.mp3` | The Pit Lord's Chamber |
| combat | `combat.mp3` | Any normal fight (playlist: `combat1/2/3...`) |
| zombie | `zombie.mp3` | Zombie Fan pre-battle reel voice (room music stops; plays once) |
| corpse | `corpse.mp3` | Reanimated Roadie pre-battle reel voice (room music stops; plays once) |
| shadow | `shadow.mp3` | Stage Ninja pre-battle reel voice (room music stops; plays once) |
| demon | `demon.mp3` | Enforcer (non-boss) pre-battle reel voice (room music stops; plays once) |
| engineer | `engineer.mp3` | Sound Engineer pre-battle reel voice (room music stops; plays once) |
| boss | `boss.mp3` | Boss pre-battle reel voice (both bosses; room music stops; plays once) |
| levelup | `levelup.mp3` | LEVEL UP banner (one-shot sting) |
| discovery | `discovery.mp3` | Unlocking a new ability tome (one-shot sting) |
| victory | `victory.mp3` | Beast defeated (one-shot sting) |
| ending | `ending.mp3` | Ending cutscene |
| credits | `credits.mp3` | Credits roll |

Missing files fall back to the built-in procedural audio (menu drone / combat riff) or silence — the game never crashes on a missing track.

### Animated Reels (Short Cinematics)

The engine's recommended path for short authored clips is **PNG frame sequences, not video files**. These are the game's "reels" — full-screen animated cutscenes at key story beats.

**Where they play (drop-in by key):**

| Key | Plays when | With no frames |
|-----|------------|----------------|
| `fall` | Opening cutscene: the stage gives way under Marduk | Built-in procedural fall scene (always visible out-of-the-box) |
| `chamber` | Entering the Pit Lord's Chamber for the first time | Plain text cutscene |
| `pit_lord` | Right before the Enforcer boss fight | Plain text banter cutscene |
| `beast` | Right before the final battle with the Pit Lord | Plain text banter cutscene |
| `zombie` | Right before the Zombie Fan fight | Plain text banter cutscene |
| `corpse` | Right before the Reanimated Roadie fight | Plain text banter cutscene |
| `shadow` | Right before the Stage Ninja fight | Plain text banter cutscene |
| `demon` | Right before the Enforcer fight (non-boss) | Plain text banter cutscene |
| `engineer` | Right before the Sound Engineer fight | Plain text banter cutscene |
| `ending` | Ending cutscene: climbing back onto the stage | Plain text cutscene |

**To add a clip:**

1. Build your animation in any tool that can export a PNG sequence (CapCut, After Effects, piskel, ffmpeg, even a script). Keep it **2–5 seconds**.
2. Export as numbered frames into `assets/animations/<key>/` — e.g. `assets/animations/beast/0001.png`, `0002.png`, ... Any numeric filename works (`1.png`, `01.png`, `0001.png`); the game sorts them **numerically** and ignores non-images.
3. Make frames **1024x768** for pixel-perfect full-screen scenes. Different sizes are auto-stretched to fill the screen.
4. The game plays **one frame per tick at 30 FPS**, so export at **30 fps** for 1:1 timing (a 3-second clip = 90 frames).
5. **Audio is optional and per-beat.** Intro-beat reels (fall, chamber, ending) keep whatever music is already playing underneath. Pre-battle reels (zombie, corpse, ..., boss) stop the room music when the cutscene starts and play a **one-shot voice** from the matching music slot — it starts in sync with the reel, runs once on its own channel (nothing else playing), and stops at battle start. Match the clip length to the animation for a perfect landing (e.g. 240 frames ÷ 30 = 8.0 s).
6. Launch once and check **`ASSET_MANIFEST.md`**: the **Animations** table lists every key with its live frame count and `READY (N frames)` vs `NO FRAMES` status.

Frames load once into memory (no runtime video decoding, no new dependencies). Missing folders simply fall back to the cutscene shown in the table above — the same fallback rule as portraits and music.

### HD Images

Drop PNG/JPG files into `assets/images/`. These display as full-screen HD overlays at key story moments. The game looks for image keys matching interaction triggers.

## RPG Systems

- **Interaction range** — no need to face objects. Press SPACE/ENTER within a 5-tile radius and the nearest interactable (item, NPC, enemy, or door) is auto-selected. Priority: items > NPCs > enemies > doors.
- **Levels & XP** — every battle win drops XP. Leveling up increases Max HP, ATK, and DEF and fully heals you. Your level also gates the band's battle skills: the Frontman gains **SCREAM** at level 2 and **BLITZ** at level 4.
- **Band skills** — battle abilities are cast from the battle panel (no number keys): SCREAM is a landing-zone blast (5 AP), BLITZ a double shred at range (5 AP). Skill tomes found in the world add named abilities to your character sheet (see Inventory).
- **GRIT** — the shared currency. You start each battle with more of it if you've saved up, and earn +25 per victory. In battle it buys towers and groupies; in the world it fuels your Scream heal and the vendor's permanent upgrades.
- **Vendor upgrades** — the Sketchy Vendor spends GRIT on permanent stat boosts: **Max HP +10 (25 GRIT)**, **Attack +3 (30 GRIT)**, or **Defense +1 (20 GRIT)**. GRIT carries over between visits.
- **Passive regen** — when out of combat, you slowly recover +1 HP every few seconds.
- **Sanity** — drops from Screaming, certain items, and some abilities. Low sanity causes screen glitching.
- **Locked doors** — some require a key item (look for the crypt key on the Stage).
- **Gated doors** — a boss-gate in the Mosh Pit only opens after the Pit Lord's Enforcer is defeated.
- **Items** — one-time use pickups that restore HP/ATK or add to inventory.

## Combat Flavor

- **Pre-battle cutscene** — each fight opens with a two-line exchange between Azrael and Marduk (with per-speaker portraits), then a fullscreen animation reel with a synced one-shot voice clip, then the battle.
- **Victory one-liners** — every win earns an action-hero style quip, shown on the victory screen.
- **Boss fights** — the Pit Lord's Enforcer (Mosh Pit) and the Pit Lord himself (Chamber) are **single-enemy battles** in the same stage-defense engine, scaled to a one-versus-you duel with their own name, banter, and victory lines. Beat the Beast and the ending cutscene plays.

## Rooms (7 total)

1. **The Stage of Sin** — Starting area. Find the Roadie, grab gear, fight the zombie fan. The Roadie gives cryptic hints about the path deeper.
2. **Backstage Gore** — Corridors of blood. A rusted door leads to the secret Green Room of Vile if you have the crypt key.
3. **The Merch Table of Madness** — The Sketchy Vendor sells cursed items and buys your GRIT for upgrades. A demon guards the goods. The path forward goes east to the Mosh Pit.
4. **The Mosh Pit of Souls** — Boss arena. The Pit Lord's Enforcer blocks the way. Kill it to open the great gate to the final chamber. A north door leads to the Sound Booth.
5. **The Green Room of Vile** — (locked, requires crypt key) A VIP side-room. The Last Roadie gives lore and a heal. Loot and get out.
6. **The Sound Booth of Despair** — (side room off the Mosh Pit) The reanimated Sound Engineer mans the master console. Loot the **Double Down** tome and the Master Fader weapon. A west door loops back toward Backstage.
7. **The Pit Lord's Chamber** — Final boss. The Pit Lord himself. End the set and escape.

## Story

The band was mid-set when the floor gave out. Now the singer is in hell, surrounded by demons that look suspiciously like venue staff. The Roadie has intel, the Vendor has gear, the Green Room has secrets, and the Pit Lord has your exit ticket. The only way out is through him. The only way forward is violence and bad decisions.

The story is told to you by **AZRAEL D DESTROYER** — the band's cat-god, the narrator who introduces himself and his abyss in the opening cutscene, the spirit who hints at you when you're stuck, and the blazing ranged weapon that streaks in at range 3 during battles.

## Stage Fright Tactics (Demo / Battle mode)

```
python rts_demo.py
```

A turn-based stage-defense battler, inspired by Blood Bowl action points + C&C/Advance Wars base building. This **is** the RPG's battle mode (wired in via `BattleBridge`), and it's also playable standalone as a repeatable sandbox.

- **AP per unit** — move = 1 AP/tile, melee = 3 AP, ranged = 4 AP. Spend each unit, then END TURN; the horde follows the same rules.
- **Hold the Stage** — the Core must survive 4 fixed waves. Lose the Core, lose the battle. You deploy with one **ready Watchtower** and the Support Van.
- **GRIT economy (exact numbers)** — start with **60**. Earn **+8 per kill** and a wave-clear bonus of **40 + 20 × wave number** (waves 1–4). Spend it:
  - **Watchtower = 45 GRIT** — takes ~2 turns to build, then **auto-fires at every enemy in its range-4 once per round** (5–8 damage).
  - **Groupie = 20 GRIT** — hired from the Support Van (max **6** fielded at once, one meets you from the Van's queue each turn).
- **Shared band XP** — every hit, kill, and kill from *any* band member feeds one level pool. Needs **30 + (level−1)×26** per level; every level-up heals and toughens the whole team.
- **Melee vs ranged** — clicks auto-resolve: adjacent targets take the melee attack (3 AP); targets beyond that (up to each unit's reach) get the ranged attack where a unit has one (4 AP). Units specialize — Groupies are melee bruisers, while the Frontman hits hard up close and, at range, summons **Azrael D Destroyer** streaking in at range 3. Every band level-up is another way Azrael attacks: **SCREAM** (landing-zone blast, 5 AP) at band level 2, **BLITZ** (double shred at range, 5 AP) at level 4.
- **Undo** — one-step undo on moves/attacks, plus confirm styling on the action panel.
- **Music** — scans `assets/music/` for `combat1.mp3`, `combat2.mp3`, ... and `boss1.mp3`, ... and rotates through them so every battle sounds different. Missing files fall back to a built-in procedural riff (battles) or a low room drone (exploration) — never silence.
- **Retry** — R restarts the battle on a freshly randomized board (different obstacles each run).
- **Retreat** — Q abandons the battle and puts you back in the room (side-effects like core loss or rewards are skipped).

This is the hybrid now: roam the RPG, trigger a battle, fight it here — the same battle engine powers both.

## Help Guide

Press **H** during gameplay for a full in-game cheat sheet: every control (world + battle) and the exact battle/RPG mechanics (AP costs, GRIT economy, band XP, skills, vendor prices, sanity). Close it with H, I, or ESC.

## Tutorial System

The game teaches itself as you play. Watch for:
- **Objectives** — shown at top center, per-room guidance with a portrait reveal when you enter a room for the first time
- **Help banners** — one-time tips appear at the bottom when you perform actions for the first time
- **Contextual prompts** — bottom HUD shows what SPACE will do when you're near something interactable
- **Combat tutorial** — first fight shows controls; each new system teaches itself when it matters, and **H** opens the full help guide anytime
- **GRIT/Scream prompt** — appears when GRIT is full and you can heal
- **Sanity warning** — warns when sanity drops low

Progress and tutorial flags are saved with your game.