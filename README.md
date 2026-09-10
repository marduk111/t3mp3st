# T3MP3ST - Belligerent Dickhead vs The Beast

A horror RPG where the singer of Belligerent Dickhead falls through the floor during a gig and must fight through hell to finish the set.

## Try the Beta (Testers)

Clone it, install one package, run:

```
git clone https://github.com/marduk111/t3mp3st.git
cd t3mp3st
python -m pip install -r requirements.txt
python main.py
```

**Windows, no terminal needed:** double-click **`run.bat`** (full game) or **`run_demo.bat`** (repeatable battle-sandbox). It creates a private environment and installs pygame-ce for you on first launch.

Everything is procedurally generated — there are **no asset downloads**; a fresh clone boots straight to the menu.

- Requires **Python 3.11** and **pygame-ce** (`pip install -r requirements.txt`).
- Verified working combo on Windows: `python 3.11` + `pygame-ce 2.5.8`.
- macOS/Linux: use `python3 main.py` / `python3 rts_demo.py`.
- The game saves to `save.json` in the same folder (freely deletable for a clean start).
- Fullscreen toggle: **F11** (works anywhere, even mid-battle).

Found a bug? Record how you got there (keys pressed, what you saw) — the developer would love a minimal repro.

## Stage Fright Tactics (Demo)

A turn-based stage-defense battler, inspired by Blood Bowl action points + C&C/Advance Wars base building. This **is** the RPG's battle mode (wired in via `BattleBridge`), and it's also playable standalone as a repeatable sandbox.

```
python rts_demo.py
```

It's a turn-based stage-defense battler, inspired by Blood Bowl action points + C&C/Advance Wars base building:

- **AP per unit** — move = 1 AP/tile, melee = 3 AP, ranged = 4 AP. Spend each unit, then END TURN; the horde follows the same rules.
- **Hold the Stage** — the Core must survive 4 fixed waves. Lose the Core, lose the battle. You deploy with one **ready Watchtower** and the Support Van.
- **GRIT economy (exact numbers)** — start with **60**. Earn **+8 per kill** and a wave-clear bonus of **40 + 20 × wave number** (waves 1–4, i.e. 60/80/100/120). Spend it:
  - **Watchtower = 45 GRIT** — takes ~2 turns to build, then **auto-fires at every enemy in its range-4 once per round** (5–8 damage).
  - **Groupie = 20 GRIT** — hired from the Support Van (max **6** fielded at once, one meets you from the Van's queue each turn).
- **Shared band XP** — every hit, kill, and kill from *any* band member feeds one level pool (unlike WC3, grunts count too). Needs **30 + (level−1)×26** per level; every level-up heals and toughens the whole team.
- **Melee vs ranged** — clicks auto-resolve: adjacent targets take the melee attack (3 AP); targets beyond that (up to each unit's reach) get the ranged attack where a unit has one (4 AP). Units specialize — Groupies are melee bruisers, while the Frontman hits hard up close and, at range, summons **Azrael D Destroyer** streaking in at range 3. Every band level-up is another way Azrael attacks: **SCREAM** (landing-zone blast, 5 AP) at band level 2, **BLITZ** (double shred at range, 5 AP) at level 4.
- **Undo** — one-step undo on moves/attacks, plus confirm styling on the action panel.
- **Music** — scans `assets/music/` for `combat1.mp3`, `combat2.mp3`, ... and `boss1.mp3`, ... and rotates through them so every battle sounds different (falls back to silence gracefully).
- **Retry** — R restarts the battle on a freshly randomized board (different obstacles each run).
- **Retreat** — Q abandons the battle and puts you back in the room (side-effects like core loss or rewards are skipped).

This is the hybrid now: roam the RPG, trigger a battle, fight it here — the same battle engine powers both.

## Help Guide

Press **H** during gameplay for a full in-game cheat sheet: every control (world + battle) and the exact battle/RPG mechanics (AP costs, GRIT economy, band XP, skills, vendor prices, sanity). Close it with H, I, or ESC. A tips-toast also reminds you the first time you open it.

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

## Tutorial System

The game teaches itself as you play. Watch for:
- **Objectives** — shown at top center, per-room guidance with a portrait reveal when you enter a room for the first time
- **Help banners** — one-time tips appear at the bottom when you perform actions for the first time
- **Contextual prompts** — bottom HUD shows what SPACE will do when you're near something interactable
- **Combat tutorial** — first fight shows controls; each new system teaches itself when it matters, and **H** opens the full help guide anytime
- **GRIT/Scream prompt** — appears when GRIT is full and you can heal
- **Sanity warning** — warns when sanity drops low

Progress and tutorial flags are saved with your game.

## Portraits (Placeholder Art)

Every character, enemy, and item has a portrait that appears beside dialogue, in battle, and on objective reveals. They're currently **generated placeholder art** — pixel mugshots so the game looks complete with zero external files.

To drop in your real artwork later, save a PNG named after the entity into `assets/portraits/`:

- `player.png` — Belligerent Dickhead (shows on intro cutscene, dialogue, combat)
- `zombie.png`, `corpse.png`, `shadow.png`, `demon.png`, `engineer.png`, `beast.png` — enemies
- `roadie.png`, `last_roadie.png`, `sketchy_vendor.png` — NPCs
- `beer.png`, `mic.png`, `crypt_key.png`, `broken_bottle.png`, `guitaraxe.png`, `tome_double_down.png`, etc. — items (full list in **ASSET_MANIFEST.md**)

Any PNG in `assets/portraits/` matching a portrait key **replaces** the placeholder automatically. Recommended size: 160x160.

Portrait keys are lowercased with spaces replaced by underscores (e.g. an NPC named "Last Roadie" → `last_roadie.png`).

## Asset Manifest

**`ASSET_MANIFEST.md`** (created at the project root on launch) is your one-stop reference for every replaceable placeholder. It lists:

- **Every portrait key** the game actually uses (characters, enemies, items, player) with its status (`PLACEHOLDER` → still auto-generated, `CUSTOM` → your PNG is live) and where it appears.
- **Every music slot** with its file name and the game moment it scores, plus live `missing`/`found` status.

When you add or remove rooms, NPCs, enemies, or items, the manifest updates automatically on the next launch. **You never edit it by hand** — it's a checklist your artwork and music fill in.

## RPG Systems

- **Interaction range** — no need to face objects. Press SPACE/ENTER within a 5-tile radius and the nearest interactable (item, NPC, enemy, or door) is auto-selected. Priority: items > NPCs > enemies > doors.
- **Levels & XP** — every battle win drops XP. Leveling up increases Max HP, ATK, and DEF and fully heals you. Your level also gates the band's battle skills: the Frontman gains **SCREAM** at level 2 and **BLITZ** at level 4.
- **Band skills** — battle abilities are cast from the battle panel (no number keys): SCREAM is a landing-zone blast (5 AP), BLITZ a double shred at range (5 AP). Skill tomes found in the world add named abilities to your character sheet (see Inventory).
- **GRIT** — the shared currency. You start each battle with more of it if you've saved up, and earn +25 per victory. In battle it buys towers and groupies; in the world it fuels your Scream heal and the vendor's permanent upgrades.
- **Vendor upgrades** — the Sketchy Vendor spends GRIT on permanent stat boosts: **Max HP +10 (25 GRIT)**, **Attack +3 (30 GRIT)**, or **Defense +1 (20 GRIT)**. GRIT carries over between visits.
- **Passive regen** — when out of combat, you slowly recover +1 HP every few seconds.
- **Sanity** — drops from Screaming, certain items, and some abilities. Low sanity causes screen glitching.
- **Locked doors** — some doors require a key item (look for the crypt key on the Stage).
- **Gated doors** — a boss-gate in the Mosh Pit only opens after the Pit Lord's Enforcer is defeated.
- **Items** — one-time use pickups that restore HP/ATK or add to inventory.

## Combat Flavor

- **Pre-battle banter** — each fight opens with a trash-talking exchange between the enemy and Belligerent Dickhead. Lines are per enemy type.
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

## Adding Your Music

There's a **live asset manifest** that tells you exactly what to drop where. Launch the game once and check **`ASSET_MANIFEST.md`** in the project folder — it is regenerated on every start/load and lists every portrait and music slot with live status (`missing` / `found`).

Music is **moment-based**: each game event looks for a file named after that event's slot in `assets/music/`. Drop `<slot>.mp3` (or `.ogg` / `.wav`) and it plays at that exact moment. Numbered names also work: `01-stage.mp3` = `stage.mp3`.

**Combat playlists** (used by every battle — the RPG's fights included): drop several tracks as `combat1.mp3`, `combat2.mp3`, ... and the battle music rotates between them so no fight sounds identical. Same for `boss1.mp3`, `boss2.mp3`, ... in boss fights.

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
| combat | `combat.mp3` | Any normal fight |
| boss | `boss.mp3` | Boss fights (Enforcer / Pit Lord) |
| levelup | `levelup.mp3` | LEVEL UP banner (one-shot sting) |
| discovery | `discovery.mp3` | Unlocking a new ability tome (one-shot sting) |
| victory | `victory.mp3` | Beast defeated (one-shot sting) |
| ending | `ending.mp3` | Ending cutscene |
| credits | `credits.mp3` | Credits roll |

Missing files fall back to the built-in procedural audio (menu drone / combat riff) or silence — the game never crashes on a missing track. A "Now Playing" readout shows the current file at the top of the screen when a track changes.

## Adding HD Images

Drop PNG/JPG files into `assets/images/`. These display as full-screen HD overlays at key story moments. The game looks for image keys matching interaction triggers.

## Adding Portrait Art

See the **Portraits** section above — `assets/portraits/` holds per-character mugshots that replace placeholders. The **Asset Manifest** lists every key currently in use.

## Adding Content

To add new rooms, enemies, items, or NPCs, edit the `setup_rooms()` method in `main.py`. Each room is a 20x15 tile grid with:
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

## Save System

Press F5 to save. Progress is written to `save.json` inside the project folder. Load from the main menu. Tutorial flags and story flags persist across saves, along with your **level, XP, unlocked abilities, upgraded stats, and inventory**.
