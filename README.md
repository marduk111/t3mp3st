# T3MP3ST - Belligerent Dickhead vs The Beast

A horror RPG where the singer of Belligerent Dickhead falls through the floor during a gig and must fight through hell to finish the set.

## Run It

```
python main.py
```

No external assets required. All audio is procedurally generated.

### For Your Tester

- Requires **Python 3.11** and the **pygame-ce** package (`pip install pygame-ce`).
- Verified working combo on Windows: `python 3.11` + `pygame-ce 2.5.8`.
- On other Python versions, `python3` (or `python3.11`) usually works the same.
- The game saves to `save.json` in the same folder (freely deletable for a clean start).
- Fullscreen toggle: F11.

Found a bug? Record how you got there (keys pressed, what you saw) — the developer would love a minimal repro.

## Stage Fright Tactics (Demo)

A separate, self-contained battle-system feel-test in `rts_demo.py` — the future combat mode for the main game, built as its own file so it never touches the working RPG.

```
python rts_demo.py
```

It's a turn-based stage-defense battler, inspired by Blood Bowl action points + C&C/Advance Wars base building:

- **AP per unit** — move = 1 AP/tile, melee = 3 AP, ranged = 4 AP. Spend each unit, then END TURN; the horde follows the same rules.
- **Hold the Stage** — the Core must survive 4 waves. Lose the Core, lose the battle. You deploy with one **ready Watchtower** and the Support Van.
- **GRIT economy** — trickle per kill + a wave-clear bonus. Spend it on Watchtowers (45, ~2 turns to build; each **auto-fires at every enemy in its range-4 once per round**) or Groupies from the Support Van (20, hire with a Van queue).
- **Shared band XP** — every hit, kill, and ability from *any* band member feeds one level pool (unlike WC3, grunts count too). Levels raise the whole team.
- **Melee vs ranged** — clicks auto-resolve: adjacent targets take the melee attack (3 AP); targets beyond that (up to each unit's reach) get the ranged attack where a unit has one (4 AP). Units specialize — Groupies and the Bass Player are melee bruisers, and the Frontman's ranged hit is Azrael D Destroyer streaking in at range 3. Every skill-up is another way Azrael attacks: **SCREAM** (landing-zone blast) at band level 2, **BLITZ** (double shred at range) at level 4.
- **Undo** — one-step undo on moves/attacks, plus confirm styling on the action panel.
- **Music** — scans `assets/music/` for `combat1.mp3`, `combat2.mp3`, ... and `boss1.mp3`, ... and rotates through them so every battle sounds different (falls back to silence gracefully).
- **Retry** — R restarts the battle on a freshly randomized board (different obstacles each run).

This is a placeholder for the future hybrid: roam the RPG, trigger a battle, and fight it here.

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move |
| SPACE / ENTER | Interact / Talk / Advance dialogue |
| I | Inventory |
| F | Scream (heal when GRIT is full) |
| M | Mute audio |
| F11 | Toggle fullscreen |
| F5 | Save game |
| ESC | Menu / Back |

Combat:
| Key | Action |
|-----|--------|
| 1 | Attack |
| 2 | First unlocked ability (or Taunt) |
| 3..9 | More abilities as they unlock, then Taunt/Flee |

Abilities are cast with their number key. Their order changes as you unlock more — read the on-screen list during battle.

## Tutorial System

The game teaches itself as you play. Watch for:
- **Objectives** — shown at top center, per-room guidance with a portrait reveal when you enter a room for the first time
- **Help banners** — one-time tips appear at the bottom when you perform actions for the first time
- **Contextual prompts** — bottom HUD shows what SPACE will do when you're near something interactable
- **Combat tutorial** — first fight shows controls; each new system teaches itself when it matters
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
- **Levels & XP** — every enemy drops XP. Leveling up increases Max HP, ATK, and DEF and fully heals you. Level 2 unlocks your first skill automatically.
- **Abilities** — as you level up and find skill tomes in the world, you unlock special combat moves cast with their number key. Abilities cost **GRIT** or **SANITY**:
  - **Power Chord** (1.6x, 30 GRIT) — auto-unlocked at level 2
  - **Double Down** (2.0x, 12 SANITY) — hidden tome in the Sound Booth
  - **Feedback Howl** (2.5x, 55 GRIT) — an effects pedal hidden in the Mosh Pit
- **GRIT meter** — fills when you land or take hits in combat. Acts as both your Scream fuel and a **currency**.
- **Vendor upgrades** — the Sketchy Vendor returns to it repeatedly to spend GRIT on permanent stat boosts (Max HP +10, Attack +3, or Defense +1). GRIT carries over between visits.
- **Passive regen** — when out of combat, you slowly recover +1 HP every few seconds.
- **Sanity** — drops from Screaming, certain items, and some abilities. Low sanity causes screen glitching.
- **Locked doors** — some doors require a key item (look for the crypt key on the Stage).
- **Gated doors** — a boss-gate in the Mosh Pit only opens after the Pit Lord's Enforcer is defeated.
- **Items** — one-time use pickups that restore HP/ATK or add to inventory.

## Combat Flavor

- **Pre-battle banter** — each fight opens with a trash-talking exchange between the enemy and Belligerent Dickhead. Lines are per enemy type.
- **Victory one-liners** — every win earns an action-hero style quip, shown on the victory screen.
- **Boss fights** — the Pit Lord's Enforcer (Mosh Pit) and the Pit Lord himself (Chamber) are multi-phase encounters with unique banter.

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

**Combat playlists** (used by the Stage Fright demo, and coming to the RPG's fights): drop several tracks as `combat1.mp3`, `combat2.mp3`, ... and the battle music rotates between them so no fight sounds identical. Same for `boss1.mp3`, `boss2.mp3`, ... in boss fights.

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
