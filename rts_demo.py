import os
import random
import re
import sys
import pygame

SCREEN_W, SCREEN_H = 1024, 768
FPS = 30
TILE = 32
BOARD_W, BOARD_H = 24, 20
BOARD_X, BOARD_Y = 8, 76
BOARD_PX_W = BOARD_W * TILE
BOARD_PX_H = BOARD_H * TILE
HUD_X = BOARD_X + BOARD_PX_W + 14
HUD_W = SCREEN_W - HUD_X - 10
LOG_Y = BOARD_Y + BOARD_PX_H + 8
LOG_H = SCREEN_H - LOG_Y - 10

TILES_WALK = {"floor", "stage", "gate", "spawn", "cable"}

COL = {
    "bg": (9, 7, 12),
    "panel": (18, 14, 24),
    "panel2": (26, 20, 34),
    "text": (220, 214, 226),
    "dim": (138, 130, 150),
    "gold": (255, 205, 90),
    "green": (120, 230, 140),
    "red": (235, 90, 80),
    "blue": (110, 170, 255),
    "purple": (195, 130, 255),
    "floor": (44, 38, 54),
    "floor2": (48, 41, 58),
    "wall": (70, 62, 86),
    "hudbg": (13, 10, 18),
    "btn": (36, 30, 48),
    "btn_hot": (58, 48, 78),
    "btn_off": (26, 22, 34),
}

STATE_TITLE = 0
STATE_PLAY = 1
STATE_WON = 2
STATE_LOST = 3
STATE_DONE = 4


ACTED_OVERLAY = None


def _acted_overlay():
    global ACTED_OVERLAY
    if ACTED_OVERLAY is None:
        ACTED_OVERLAY = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        ACTED_OVERLAY.fill((0, 0, 0, 150))
    return ACTED_OVERLAY


def make_sprite(rows, palette):
    h = len(rows)
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in palette:
                surf.set_at((x, y), palette[ch])
    return pygame.transform.scale(surf, (w * 2, h * 2))


def _p(palette, **extra):
    base = {
        "k": (0, 0, 0, 0),
        "o": (70, 55, 40),
        "Y": (255, 205, 90),
        "W": (235, 235, 240),
        "R": (190, 70, 60),
        "B": (80, 130, 220),
        "G": (110, 200, 120),
        "P": (170, 95, 210),
        "D": (40, 34, 52),
        "g": (160, 160, 168),
        "s": (120, 190, 210),
        "d": (60, 50, 70),
    }
    base.update(extra)
    return base


FRONTMAN_ROWS = [
    "...kkkk...",
    "..kkkkkk..",
    "..kssssk..",
    "..kssssk..",
    "...kssk...",
    "..kRRRRk..",
    ".kRRRRRRk.",
    ".kRRRRRRk.",
    "...kDDk...",
    "...kDDk...",
    "...kDDk...",
    "...kDDk...",
]
FRONTMAN_PAL = _p({}, s=(235, 190, 150), R=(200, 55, 55), D=(35, 30, 50))

GROUPIE_ROWS = [
    "...kkkk...",
    "..kkkkkk..",
    "..kGGGGk..",
    "..kGGGGk..",
    "..kssssk..",
    "..kGGGGk..",
    ".kGGGGGGk.",
    ".kGkkkkGk.",
    "..kDDk....",
    "..kDDk....",
]
GROUPIE_PAL = _p({}, s=(230, 180, 140), G=(90, 190, 130), D=(30, 28, 40))

BASS_ROWS = [
    "...kkkk...",
    "..kkkkkk..",
    "..kPPPPk..",
    "..kPPPPk..",
    "..kPPPkk..",
    ".kPPWPk...",
    ".kWWPPPk..",
    ".kPPkPPk..",
    "..kDDk....",
    "..kDDk....",
]
BASS_PAL = _p({}, s=(235, 190, 150), P=(150, 80, 200), W=(220, 220, 235), D=(30, 28, 40))

FAN_ROWS = [
    "...kkkk...",
    "..kBBBBk..",
    "..kBssBk..",
    "..kBssBk..",
    "..kBBBBk..",
    "..kkkkk...",
    ".kWWkWWk..",
    ".kW.kWk...",
    "..kDkDk...",
    "..kDDk....",
]
FAN_PAL = _p({}, s=(200, 170, 130), B=(70, 120, 210), W=(150, 190, 230), D=(40, 34, 52))

NINJA_ROWS = [
    "...kkkk...",
    "..kddddk..",
    "..kddddk..",
    "..kddddk..",
    "..kWWWWk..",
    "..kddddk..",
    ".kddkddk..",
    ".kdWkWdk..",
    "..kDkDk...",
    "..kkkkk...",
]
NINJA_PAL = _p({}, d=(52, 46, 72), W=(200, 205, 220), D=(30, 26, 44))

BOSS_ROWS = [
    "...kkkkk...",
    "..kkkkkkk..",
    ".kgkssskg..",
    ".kgkssskg..",
    "..kkBBGkk..",
    ".kkBBBBGkk.",
    "kkBBBBBBGGk",
    "kkBBkBBkGGk",
    "kWWkWWkWWk.",
    ".kk.kk.kk..",
]
BOSS_PAL = _p({}, s=(200, 160, 120), B=(95, 120, 160), G=(140, 160, 190), W=(190, 200, 215))

TOSSER_ROWS = [
    "...kkkkk...",
    "..kkWWWkk..",
    "..kWWWWWk..",
    "..kkssskk..",
    "...kssk....",
    "..kYYYYk...",
    ".kYYYYYYk..",
    ".kYBkBYk...",
    "..kDkDk....",
]
TOSSER_PAL = _p({}, s=(200, 150, 110), Y=(235, 150, 60), W=(230, 190, 120), B=(90, 80, 70), D=(50, 40, 40))

CAT_ROWS = [
    ".kkkkkkkk.",
    "kWWkkkkWWk",
    "kkkkkkkkkk",
    "kYkkkkkkYk",
    "kkkkkkkkkk",
    "kkkkkkkkkk",
    ".kkkkkkkk.",
    ".kkkkkkkk.",
    "..kkkkkk..",
    "..kkkkkk..",
    "...kkkk...",
]
CAT_PAL = _p({}, W=(55, 55, 70), Y=(235, 205, 90))

TOWER_ROWS = [
    "....gg....",
    ".g..gg..g.",
    ".ggggggg..",
    ".gWWWWGg..",
    ".gWWWWGg..",
    ".ggggggg..",
    ".ggggggg..",
    ".gWgggGg..",
    ".gWgggGg..",
    ".ggggggg..",
    "..kkkkkk..",
    ".kkkkkkkk.",
]
TOWER_PAL = _p({}, g=(110, 108, 120), W=(160, 168, 180), G=(230, 220, 110))

VAN_ROWS = [
    "....kkkkkkk....",
    "...kggggggok...",
    ".kggggggggggok.",
    "kggggggggggggok",
    "kYYYYYYYYYYYYYk",
    "kYYkYYYkYYYYYYk",
    "kkkkkkkkkkkkkkk",
    "..kDDDDDDDDDk..",
]
VAN_PAL = _p({}, g=(120, 150, 165), o=(90, 80, 70), Y=(205, 160, 70), D=(40, 40, 48))

CORE_ROWS = [
    "..gggggggggg..",
    ".gWWWWWWWWWWg.",
    ".gWWgWWgWWgWg.",
    ".gWWgWWgWWgWg.",
    ".gWWgWWgWWgWg.",
    ".gWWgWWgWWgWg.",
    ".gggggggggggg.",
    "..YYYYYYYYYY..",
    "..gggggggggg..",
]
CORE_PAL = _p({}, g=(70, 66, 80), W=(120, 118, 130), Y=(225, 190, 80))

SPEAKER_ROWS = [
    ".kkkkkkkkk.",
    "kkWWWWWWWWk",
    "kWWWWWWWWWk",
    "kWWkkkkWWWk",
    "kWWkWWkWWWk",
    "kWWkWWkWWWk",
    "kkkkkkkkkkk",
    ".ddddddddd.",
]
SPEAKER_PAL = _p({}, W=(90, 86, 100), d=(50, 44, 58))

SPRITES = {}


def get_sprite(kind, variant=0):
    key = (kind, variant)
    if key in SPRITES:
        return SPRITES[key]
    surf = None
    if kind == "frontman":
        surf = make_sprite(FRONTMAN_ROWS, FRONTMAN_PAL)
    elif kind == "groupie":
        surf = make_sprite(GROUPIE_ROWS, GROUPIE_PAL)
    elif kind == "bass":
        surf = make_sprite(BASS_ROWS, BASS_PAL)
    elif kind == "fan":
        surf = make_sprite(FAN_ROWS, FAN_PAL)
    elif kind == "ninja":
        surf = make_sprite(NINJA_ROWS, NINJA_PAL)
    elif kind == "tosser":
        surf = make_sprite(TOSSER_ROWS, TOSSER_PAL)
    elif kind == "cat":
        surf = make_sprite(CAT_ROWS, CAT_PAL)
    elif kind == "enforcer":
        surf = make_sprite(BOSS_ROWS, BOSS_PAL)
    elif kind == "tower":
        surf = make_sprite(TOWER_ROWS, TOWER_PAL)
    elif kind == "van":
        surf = make_sprite(VAN_ROWS, VAN_PAL)
    elif kind == "core":
        surf = make_sprite(CORE_ROWS, CORE_PAL)
    elif kind == "speaker":
        surf = make_sprite(SPEAKER_ROWS, SPEAKER_PAL)
    SPRITES[key] = surf
    return surf


KINDS = {
    "frontman": {"name": "Belligerent Dickhead", "hp": 100, "atk": 11, "rng_atk": 11, "ap": 6, "range": 3, "team": 0},
    "groupie": {"name": "Groupie", "hp": 42, "atk": 5, "rng_atk": 0, "ap": 5, "range": 0, "team": 0},
    "bass": {"name": "Bass Player", "hp": 92, "atk": 10, "rng_atk": 0, "ap": 5, "range": 0, "team": 0},
    "fan": {"name": "Zombie Fan", "hp": 46, "atk": 6, "rng_atk": 0, "ap": 5, "range": 0, "team": 1},
    "ninja": {"name": "Stage Ninja", "hp": 32, "atk": 5, "rng_atk": 0, "ap": 7, "range": 0, "team": 1},
    "tosser": {"name": "Bottle Tosser", "hp": 34, "atk": 2, "rng_atk": 5, "ap": 4, "range": 3, "team": 1},
    "enforcer": {"name": "Enforcer", "hp": 150, "atk": 13, "rng_atk": 0, "ap": 4, "range": 0, "team": 1},
}

BUILD_KINDS = {
    "core": {"name": "The Stage", "hp": 220},
    "van": {"name": "Support Van", "hp": 90},
    "tower": {"name": "Watchtower", "hp": 85},
}

WAVES = [
    ["fan", "fan", "fan"],
    ["fan", "fan", "ninja", "fan"],
    ["ninja", "fan", "fan", "tosser", "ninja"],
    ["fan", "ninja", "tosser", "fan", "ninja", "enforcer"],
]

MAX_GROUPIES = 6
GROUPIE_COST = 20
TOWER_COST = 45
KILL_GRIT = 8
WAVE_GRIT = 40
START_GRIT = 60
START_XP = 0

TITLE_LINES = [
    "T3MP3ST // STAGE FRIGHT",
    "",
    "a turn-based stage-defense tactics demo",
    "",
    "Hold the Stage through 4 waves of the horde.",
    "Every unit spends ACTION POINTS each turn:",
    "  move = 1 AP per tile",
    "  attack = 3 AP (melee) or 4 AP (ranged)",
    "",
    "End the band's turn, then the horde moves.",
    "GRIT is earned per kill and per wave - build",
    "Watchtowers (45) or hire Groupies from the Van (20).",
    "Watchtowers auto-fire at every enemy in range (4)",
    "once per round - they're your stage's backline.",
    "",
    "The whole band shares XP: every hit, kill and",
    "ability feeds the level-up.",
    "",
    "Targets adjacent to the Frontman take melee; anything",
    "farther out gets AZRAEL D DESTROYER streaking over to",
    "shred it (range 3). Different units favor one or the",
    "other. Every skill-up is another way Azrael attacks -",
    "SCREAM at level 2, BLITZ at level 4.",
    "",
    "ENTER - start battle     ESC - pause/quit",
]


class MusicCue:
    def __init__(self):
        self.music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "music")
        self.available = pygame.mixer.get_init() is not None

    def scan_combat(self):
        if not self.available or not os.path.isdir(self.music_dir):
            return []
        names = sorted(os.listdir(self.music_dir))
        got = []
        for n in names:
            if re.match(r"^combat(\d*)\.(mp3|ogg|wav)$", n, re.I):
                got.append(os.path.join(self.music_dir, n))
        return got

    def scan_boss(self):
        if not self.available or not os.path.isdir(self.music_dir):
            return []
        names = sorted(os.listdir(self.music_dir))
        got = []
        for n in names:
            if re.match(r"^boss(\d*)\.(mp3|ogg|wav)$", n, re.I):
                got.append(os.path.join(self.music_dir, n))
        return got

    def play(self, path):
        if not self.available or not path or not os.path.isfile(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def menu_loop(self):
        if not self.available:
            return
        dirn = self.music_dir
        for cand in ("menu.mp3", "menu.ogg", "menu.wav", "demo.mp3", "demo.ogg", "demo.wav"):
            p = os.path.join(dirn, cand)
            if os.path.isfile(p):
                self.play(p)
                return

    def combat_loop(self, wave, boss=False):
        if not self.available:
            return
        if boss:
            got = self.scan_boss()
            pool = got or self.scan_combat()
            if pool:
                self.play(random.choice(pool))
                return
        got = self.scan_combat()
        if got:
            self.play(got[(wave - 1) % len(got)])


class Demo:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = self._font(18)
        self.font_sm = self._font(15)
        self.font_lg = self._font(40)
        self.music = MusicCue()
        self.reset()
        self.music.menu_loop()

    def _font(self, size):
        try:
            return pygame.font.SysFont("consolas", size)
        except Exception:
            return pygame.font.Font(None, size)

    def reset(self, retry_keep_music=False):
        self.state = STATE_TITLE
        self.grid = None
        self.units = []
        self.buildings = []
        self.grit = START_GRIT
        self.turn = 1
        self.wave = 1
        self.team_xp = START_XP
        self.level = 1
        self.max_groupies = MAX_GROUPIES
        self.messages = []
        self.selected = None
        self.place_mode = None
        self.phase = "player"
        self.action_log = []
        self.overlay = None
        self.banner = None
        self.banner_t = 0
        self.accent = 0
        self.cat_flash = None
        self.new_game()

    def log(self, text):
        self.messages.append(text)
        if len(self.messages) > 6:
            self.messages.pop(0)

    def new_game(self):
        self.grid = [["floor"] * BOARD_W for _ in range(BOARD_H)]
        self._wall_border()
        self._scatter_obstacles()
        self._deploy_zone()
        self._spawn_ports()
        self.units = []
        self.buildings = []
        mid = BOARD_H // 2
        self._add_building("core", 1, mid)
        self._add_building("van", 2, mid + 2)
        self._add_building("tower", 4, mid - 2, ready=True)
        self._add_unit("frontman", 2, mid - 1)
        self._add_unit("groupie", 3, mid)
        self._add_unit("groupie", 3, mid + 1)
        self.wave = 1
        self.turn = 1
        self.selected = None
        self.place_mode = None
        self.phase = "player"
        self.action_log = []
        self.overlay = None
        self.log("THE HORDE DESCENDS ON THE STAGE")
        self.log("Hold the core ('The Stage') until all 4 waves fall")
        self._spawn_wave()

    def _wall_border(self):
        for x in range(BOARD_W):
            self.grid[0][x] = "wall"
            self.grid[BOARD_H - 1][x] = "wall"
        for y in range(BOARD_H):
            self.grid[y][0] = "wall"
            self.grid[y][BOARD_W - 1] = "wall"

    def _scatter_obstacles(self):
        n = random.randint(10, 14)
        mid_x = range(8, BOARD_W - 6)
        mid_y = range(3, BOARD_H - 3)
        cells = [(x, y) for x in mid_x for y in mid_y]
        random.shuffle(cells)
        placed = 0
        for x, y in cells:
            if placed >= n:
                break
            if self.grid[y][x] != "floor":
                continue
            blockers = [(x, y), (x, y + 1)]
            if any(not (0 < bx < BOARD_W - 1 and 0 < by < BOARD_H - 1) for bx, by in blockers):
                continue
            if any(self.grid[by][bx] != "floor" for bx, by in blockers):
                continue
            self.grid[y][x] = "speaker"
            self.grid[y][x + 1] = "speaker"
            placed += 1

    def _deploy_zone(self):
        mid = BOARD_H // 2
        for y in range(mid - 2, mid + 3):
            for x in range(0, 7):
                self.grid[y][x] = "stage"

    def _spawn_ports(self):
        self.ports = []
        for y in range(3, BOARD_H - 3, 2):
            self.grid[y][BOARD_W - 2] = "gate"
            self.ports.append((BOARD_W - 2, y))
        extra = [(BOARD_W - 2, BOARD_H - 4), (BOARD_W - 2, 4)]
        for e in extra:
            self.grid[e[1]][e[0]] = "gate"
            self.ports.append(e)

    def _add_unit(self, kind, x, y):
        k = KINDS[kind]
        self.units.append({
            "id": len(self.units),
            "kind": kind,
            "team": k["team"],
            "x": x, "y": y,
            "hp": k["hp"], "max_hp": k["hp"],
            "atk": k["atk"],
            "rng_atk": k.get("rng_atk", 0),
            "ap": k["ap"], "max_ap": k["ap"],
            "range": k["range"],
            "buff": 0,
        })

    def _add_building(self, kind, x, y, ready=False):
        b = BUILD_KINDS[kind]
        self.buildings.append({
            "id": len(self.buildings),
            "kind": kind,
            "x": x, "y": y,
            "hp": b["hp"], "max_hp": b["hp"],
            "constructing": 0 if ready else (2 if kind == "tower" else 0),
        })

    def unit_at(self, x, y):
        for u in self.units:
            if u["x"] == x and u["y"] == y:
                return u
        return None

    def building_at(self, x, y):
        for b in self.buildings:
            if b["x"] == x and b["y"] == y:
                return b
        return None

    def enemy_units(self):
        return [u for u in self.units if u["team"] == 1]

    def player_units(self):
        return [u for u in self.units if u["team"] == 0]

    def attack_info(self, unit, target):
        d = abs(unit["x"] - target["x"]) + abs(unit["y"] - target["y"])
        if d <= 1 and unit.get("atk", 0) > 0:
            return "melee", 3, unit["atk"]
        if 1 < d <= unit.get("range", 0) and unit.get("rng_atk", 0) > 0:
            return "ranged", 4, unit["rng_atk"]
        return None

    def walkable(self, x, y, ignore=None):
        if not (0 <= x < BOARD_W and 0 <= y < BOARD_H):
            return False
        if self.grid[y][x] not in TILES_WALK:
            return False
        if self.building_at(x, y):
            return False
        u = self.unit_at(x, y)
        if u and u is not ignore:
            return False
        return True

    def paths(self, sx, sy):
        from collections import deque
        dist = {(sx, sy): 0}
        prev = {}
        q = deque([(sx, sy)])
        while q:
            cx, cy = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in dist:
                    continue
                if not self.walkable(nx, ny):
                    continue
                dist[(nx, ny)] = dist[(cx, cy)] + 1
                prev[(nx, ny)] = (cx, cy)
                q.append((nx, ny))
        return dist, prev

    def reachable(self, unit):
        dist, _ = self.paths(unit["x"], unit["y"])
        return {k for k, v in dist.items() if 0 < v <= unit["ap"]}

    def _path_to(self, unit, tx, ty, ignore=None):
        sx, sy = unit["x"], unit["y"]
        dist, prev = self.paths(sx, sy)
        if (tx, ty) not in prev:
            return None
        path = []
        cur = (tx, ty)
        while cur != (sx, sy):
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def _reconstruct(self, prev, unit, gx, gy):
        if (gx, gy) not in prev:
            return None
        path = []
        cur = (gx, gy)
        sx, sy = unit["x"], unit["y"]
        while cur != (sx, sy):
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def path_toward(self, unit, tx, ty):
        dist, prev = self.paths(unit["x"], unit["y"])
        coords = [(tx + dx, ty + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        coords = [c for c in coords if c in dist]
        if not coords:
            return None
        coords.sort(key=lambda c: dist[c])
        return self._reconstruct(prev, unit, coords[0][0], coords[0][1])

    def _announce_wave(self, wave):
        if wave == 4:
            self.log("WAVE 4 - the Enforcer arrives. THE FINAL STAND.")
            self.banner = "FINAL WAVE - THE ENFORCER"
        else:
            self.log("WAVE %d of 4" % wave)
            self.banner = "WAVE %d OF 4" % wave
        self.banner_t = 2.0
        self.music.combat_loop(wave, boss=(wave == 4))

    def _spawn_wave(self):
        comp = WAVES[self.wave - 1]
        random.shuffle(self.ports)
        for i, kind in enumerate(comp):
            px, py = self.ports[i % len(self.ports)]
            if self.unit_at(px, py):
                continue
            self._add_unit(kind, px, py)
        self._announce_wave(self.wave)

    def _wave_clear(self):
        return not self.enemy_units()

    def _add_xp(self, amount, source=None):
        self.team_xp += amount
        need = 30 + (self.level - 1) * 26
        while self.team_xp >= need:
            self.team_xp -= need
            self.level += 1
            need = 30 + (self.level - 1) * 26
            for u in self.player_units():
                u["max_hp"] += 12
                u["hp"] = u["max_hp"]
                u["atk"] += 2
            names = {u["kind"]: u for u in self.player_units()}
            if "frontman" in names and self.level == 2:
                self.log("BAND LEVEL 2 - Azrael learns SCREAM (5 AP: landing-zone blast)")
            elif "frontman" in names and self.level == 4:
                self.log("BAND LEVEL 4 - Azrael learns BLITZ (5 AP: double shred at range)")
            else:
                self.log("BAND LEVEL %d - the whole team gets tougher" % self.level)
            self.banner = "BAND LEVEL %d!" % self.level
            self.banner_t = 1.6

    def _damage(self, target, amount):
        target["hp"] -= amount
        return target["hp"] <= 0

    def _kill(self, target):
        if target.get("kind") == "core":
            self.log("THE STAGE FALLS TO THE HORDE")
            self.state = STATE_LOST
            return
        if target["team"] == 1:
            self.grit += KILL_GRIT
        if "unit" in target or "hp" in target and target.get("team") == 1:
            if target in self.units:
                self.units.remove(target)
                self.log("%s destroyed - +%d GRIT" % (KINDS[target["kind"]]["name"], KILL_GRIT))
                self._add_xp(6)
                if target["kind"] == "enforcer":
                    self.log("THE ENFORCER IS DOWN")
        else:
            if target in self.buildings:
                self.buildings.remove(target)
                self.log("%s destroyed" % BUILD_KINDS[target["kind"]]["name"])

    def try_move(self, unit, tx, ty):
        path = self._path_to(unit, tx, ty)
        if not path:
            return False
        cost = len(path)
        if cost > unit["ap"]:
            return False
        self._store_action({"type": "move", "unit": unit, "sx": unit["x"], "sy": unit["y"], "tx": tx, "ty": ty, "cost": cost})
        unit["x"], unit["y"] = tx, ty
        unit["ap"] -= cost
        return True

    def try_attack(self, unit, target):
        info = self.attack_info(unit, target)
        if not info:
            return False
        mode, cost, base = info
        if unit["ap"] < cost:
            return False
        unit["ap"] -= cost
        dmg = base
        if unit["buff"]:
            dmg = int(dmg * 1.6)
            unit["buff"] = 0
        dmg += random.randint(-1, 1)
        dmg = max(1, dmg)
        self._store_action({
            "type": "attack", "unit": unit, "target": target,
            "sx": unit["x"], "sy": unit["y"],
            "hp": target["hp"], "cost": cost, "xp": 2,
        })
        target["hp"] -= dmg
        self._add_xp(2)
        name = KINDS[unit["kind"]]["name"]
        if unit["kind"] == "frontman" and mode == "ranged":
            name = "AZRAEL D DESTROYER"
            self.cat_flash = [target["x"], target["y"], 0.35]
        tname = (KINDS.get(target["kind"]) or BUILD_KINDS.get(target["kind"]) or {"name": target["kind"]})["name"]
        if target["hp"] <= 0:
            self.log("%s obliterates %s" % (name, tname))
            self._kill(target)
        else:
            self.log("%s hits %s for %d" % (name, tname, dmg))
        return True

    def _store_action(self, action):
        self.action_log.append(action)
        if len(self.action_log) > 1:
            self.action_log.pop(0)

    def undo(self):
        if not self.action_log:
            return
        a = self.action_log.pop()
        if a["type"] == "move":
            u = a["unit"]
            if u in self.units:
                u["x"], u["y"] = a["sx"], a["sy"]
                u["ap"] += a["cost"]
            self._undone_move_reachable = (a["tx"], a["ty"])
        elif a["type"] == "attack":
            u = a["unit"]
            t = a["target"]
            if u in self.units:
                u["ap"] += a["cost"]
            if t is not None and t in self.units or (t is not None and t in self.buildings):
                t["hp"] = a["hp"]
            self.team_xp = max(0, self.team_xp - a["xp"])

    def end_player_turn(self):
        self.phase = "horde"
        self.selected = None
        self.place_mode = None
        self.action_log = []
        self._tower_fire()
        self._horde_act()

    def _tower_fire(self):
        for b in self.buildings:
            if b["kind"] != "tower" or b["constructing"] > 0:
                continue
            foes = [u for u in self.enemy_units()
                    if abs(b["x"] - u["x"]) + abs(b["y"] - u["y"]) <= 4]
            for t in foes:
                dmg = random.randint(5, 8)
                t["hp"] -= dmg
                if t["hp"] <= 0:
                    self.log("Watchtower LIGHTS UP %s" % KINDS[t["kind"]]["name"])
                    self._kill(t)
                else:
                    self.log("Watchtower snipes %s for %d" % (KINDS[t["kind"]]["name"], dmg))

    def _horde_act(self):
        foes = self.enemy_units()
        if not foes:
            self._finish_horde()
            return
        for e in foes:
            if e not in self.units:
                continue
            target = self._horde_target(e)
            if target is None:
                continue
            info = self.attack_info(e, target)
            if info and e["ap"] >= info[1]:
                mode, cost, base = info
                e["ap"] -= cost
                dmg = base + random.randint(0, 1)
                target["hp"] -= dmg
                tname = (KINDS.get(target["kind"]) or BUILD_KINDS.get(target["kind"]) or {"name": target["kind"]})["name"]
                self.log("%s tears into %s for %d" % (KINDS[e["kind"]]["name"], tname, dmg))
                if target["hp"] <= 0:
                    self._kill(target)
            else:
                path = self.path_toward(e, target["x"], target["y"])
                if path:
                    steps = min(e["ap"], len(path))
                    for i in range(steps):
                        nx, ny = path[i]
                        if not self.walkable(nx, ny):
                            break
                        e["x"], e["y"] = nx, ny
                        e["ap"] -= 1
        self._finish_horde()

    def _horde_target(self, e):
        units = self.player_units()
        if units:
            units.sort(key=lambda u: (abs(e["x"] - u["x"]) + abs(e["y"] - u["y"]), u["hp"]))
            return units[0]
        core = next((b for b in self.buildings if b["kind"] == "core"), None)
        return core

    def _finish_horde(self):
        for u in self.enemy_units():
            u["ap"] = u["max_ap"]
        for u in self.player_units():
            u["ap"] = u["max_ap"]
        self.turn += 1
        self._start_player_turn()

    def _start_player_turn(self):
        self._tick_production()
        for b in self.buildings:
            if b["kind"] == "tower" and b["constructing"] > 0:
                b["constructing"] -= 1
        if self._wave_clear():
            self._wave_complete()
            return
        self.phase = "player"
        self.banner = None

    def _tick_production(self):
        for b in self.buildings:
            if b["kind"] == "van" and b.get("queue") and b["queue"] > 0:
                b["queue"] -= 1
                self._spawn_groupie(b)

    def _spawn_groupie(self, van):
        candidates = []
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1)):
            nx, ny = van["x"] + dx, van["y"] + dy
            if self.walkable(nx, ny):
                candidates.append((nx, ny))
        if not candidates:
            return
        nx, ny = random.choice(candidates)
        self._add_unit("groupie", nx, ny)
        self.log("Fresh groupie joins the stage side")

    def _wave_complete(self):
        bonus = WAVE_GRIT + self.wave * 20
        self.grit += bonus
        self.log("WAVE %d of 4 CLEARED - +%d GRIT" % (self.wave, bonus))
        if self.wave >= 4:
            self.state = STATE_WON
            self.banner = "THE STAGE HOLDS"
            return
        self.wave += 1
        self._spawn_wave()

    def _groupie_count(self):
        return sum(1 for u in self.player_units() if u["kind"] == "groupie")

    def _van(self):
        return next((b for b in self.buildings if b["kind"] == "van"), None)

    def _hire_groupie(self):
        van = self._van()
        if not van or van["hp"] <= 0:
            self.log("No functional Support Van")
            return
        if self.grit < GROUPIE_COST:
            self.log("Not enough GRIT for a groupie")
            return
        if van.get("queue"):
            self.log("Van is already producing")
            return
        if self._groupie_count() >= MAX_GROUPIES:
            self.log("Too many groupies on the floor")
            return
        self.grit -= GROUPIE_COST
        van["queue"] = 1

    def _place_tower_at(self, x, y):
        if self.grit < TOWER_COST:
            self.log("Not enough GRIT for a watchtower")
            self.place_mode = None
            return
        if not (0 <= x < BOARD_W and 0 <= y < BOARD_H):
            return
        if self.grid[y][x] not in TILES_WALK:
            self.log("Can't build there")
            self.place_mode = None
            return
        if self.unit_at(x, y) or self.building_at(x, y):
            self.log("Space is occupied")
            self.place_mode = None
            return
        self.grit -= TOWER_COST
        self._add_building("tower", x, y)
        self.log("Watchtower under construction (2 turns)")
        self.place_mode = None

    def _azrael_scream(self, unit, tx, ty):
        if unit["ap"] < 5:
            self.log("Not enough AP")
            self.place_mode = None
            return
        if abs(unit["x"] - tx) + abs(unit["y"] - ty) > 3:
            self.log("AZRAEL can't reach there")
            return
        unit["ap"] -= 5
        dmg = 8 + self.level * 2
        hit = []
        for e in list(self.enemy_units()):
            if abs(e["x"] - tx) <= 1 and abs(e["y"] - ty) <= 1:
                e["hp"] -= dmg
                hit.append(e)
        self.cat_flash = [tx, ty, 0.4]
        self._add_xp(len(hit) + 2)
        for e in hit:
            if e["hp"] <= 0:
                self._kill(e)
        self.place_mode = None
        self.log("AZRAEL SCREAM - %d enemies torn apart for %d" % (len(hit), dmg))

    def _azrael_blitz(self, unit, tx, ty):
        if unit["ap"] < 5:
            self.log("Not enough AP")
            self.place_mode = None
            return
        if abs(unit["x"] - tx) + abs(unit["y"] - ty) > 3:
            self.log("AZRAEL can't reach there")
            return
        tgt = self.unit_at(tx, ty)
        if not tgt or tgt["team"] != 1:
            self.log("No enemy there for the cat")
            self.place_mode = None
            return
        unit["ap"] -= 5
        dmg = unit["atk"] * 2 + random.randint(-1, 2)
        self.cat_flash = [tx, ty, 0.5]
        self._add_xp(4)
        tgt["hp"] -= dmg
        tname = (KINDS.get(tgt["kind"]) or {"name": tgt["kind"]})["name"]
        if tgt["hp"] <= 0:
            self.log("AZRAEL BLITZ obliterates %s" % tname)
            self._kill(tgt)
        else:
            self.log("AZRAEL BLITZ tears into %s for %d" % (tname, dmg))
        self.place_mode = None

    def handle_event(self, e):
        if self.state == STATE_TITLE:
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.state = STATE_PLAY
                self.new_game()
            return
        if self.state in (STATE_WON, STATE_LOST):
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                self.reset()
            return
        if self.overlay == "pause":
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.overlay = None
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                self.reset()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self._panel_click(e.pos)
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.overlay = "pause"
            elif e.key == pygame.K_r and self.state == STATE_PLAY:
                self.reset()
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._click(e.pos)

    def _click(self, pos):
        mx, my = pos
        brush = getattr(self, "_undone_move_reachable", None)
        if brush:
            self._undone_move_reachable = None
        if mx >= HUD_X:
            self._panel_click(pos)
            return
        tx = (mx - BOARD_X) // TILE
        ty = (my - BOARD_Y) // TILE
        if not (0 <= tx < BOARD_W and 0 <= ty < BOARD_H):
            self.selected = None
            self.place_mode = None
            return
        if self.place_mode:
            if self.place_mode == "tower":
                self._place_tower_at(tx, ty)
            else:
                pkind, punit = self.place_mode
                if pkind == "scream":
                    self._azrael_scream(punit, tx, ty)
                elif pkind == "blitz":
                    self._azrael_blitz(punit, tx, ty)
            return
        if self.phase != "player":
            return
        unit = self.unit_at(tx, ty)
        if unit and unit["team"] == 0:
            self.selected = unit
            return
        if self.selected:
            sel = self.selected
            if sel.get("ap", 0) is None:
                self.selected = None
                return
            if sel["ap"] > 0:
                if self.try_move(sel, tx, ty):
                    return
                tgt = self.unit_at(tx, ty)
                if tgt and tgt["team"] == 1:
                    if self.try_attack(sel, tgt):
                        return
            self.selected = None
            return
        self.selected = None

    def _panel_click(self, pos):
        bx = HUD_X + 8
        y = self._buttons_y(self.selected)
        for label, key in self._buttons():
            rect = self._btn_rect(bx, y)
            if rect.collidepoint(pos):
                self._do_button(key)
                return
            y += 40
        if self.overlay == "pause":
            if self._btn_rect(bx, 330).collidepoint(pos):
                self.reset()
            if self._btn_rect(bx, 375).collidepoint(pos):
                self.state = STATE_DONE

    def _do_button(self, key):
        if key == "end":
            if self.phase == "player":
                self.end_player_turn()
            return
        if key == "undo":
            if self.phase == "player":
                self.undo()
            return
        if self.phase != "player":
            return
        if key == "tower":
            self.place_mode = "tower" if self.grit >= TOWER_COST else None
            if not self.place_mode:
                self.log("Not enough GRIT for a watchtower")
        elif key == "groupie":
            self._hire_groupie()
        elif key == "scream":
            if self.selected and self.selected["kind"] == "frontman" and self.level >= 2:
                self.place_mode = ("scream", self.selected)
        elif key == "blitz":
            if self.selected and self.selected["kind"] == "frontman" and self.level >= 4:
                self.place_mode = ("blitz", self.selected)

    def _buttons(self):
        btns = [("END TURN", "end"), ("UNDO LAST", "undo")]
        if self.state == STATE_PLAY:
            tower_off = self.selected is None or self.place_mode
            btns.append(("BUILD WATCHTOWER (%dG)" % TOWER_COST, "tower"))
            van = self._van()
            queue_txt = " (BUSY)" if van and van.get("queue") else ""
            btns.append(("HIRE GROUPIE (%dG)%s" % (GROUPIE_COST, queue_txt), "groupie"))
        if self.selected and self.selected["kind"] == "frontman":
            btns.append(("AZRAEL SCREAM (5 AP)%s" % ("" if self.level >= 2 else " - L2"), "scream"))
            btns.append(("AZRAEL BLITZ (5 AP)%s" % ("" if self.level >= 4 else " - L4"), "blitz"))
        return btns

    def _btn_rect(self, x, y):
        return pygame.Rect(x, y, HUD_W - 16, 32)

    def update(self, dt):
        self.accent += dt
        if self.banner_t > 0:
            self.banner_t -= dt
        if self.cat_flash:
            self.cat_flash[2] -= dt
            if self.cat_flash[2] <= 0:
                self.cat_flash = None

    def _click_cell(self, pos):
        pass

    def render(self):
        self.screen.fill(COL["hudbg"])
        if self.state == STATE_TITLE:
            self._render_title()
            return
        if self.state == STATE_DONE:
            self.screen.fill(COL["bg"])
            return
        self._render_board()
        self._render_units()
        self._render_buildings()
        self._render_topbar()
        self._render_panel()
        self._render_log()
        if self.banner and self.banner_t > 0:
            self._render_banner()
        if self.overlay == "pause":
            self._render_pause()
        if self.state == STATE_WON:
            self._render_win()
        if self.state == STATE_LOST:
            self._render_lose()

    def _render_title(self):
        y = 120
        for line in TITLE_LINES:
            col = COL["gold"] if y == 120 else COL["text"]
            surf = self.font.render(line, True, col)
            self.screen.blit(surf, (80, y))
            y += 26

    def _render_board(self):
        for ty in range(BOARD_H):
            for tx in range(BOARD_W):
                px, py = tx * TILE + BOARD_X, ty * TILE + BOARD_Y
                tile = self.grid[ty][tx]
                if tile == "floor":
                    c = COL["floor"] if (tx + ty) % 2 == 0 else COL["floor2"]
                elif tile == "stage":
                    c = (52, 42, 66) if (tx + ty) % 2 == 0 else (55, 45, 70)
                elif tile == "gate":
                    c = (40, 30, 50)
                elif tile == "cable":
                    c = (38, 44, 62)
                else:
                    c = COL["wall"]
                pygame.draw.rect(self.screen, c, (px, py, TILE, TILE))
                if tile == "speaker":
                    self.screen.blit(get_sprite("speaker"), (px + 2, py + 2))
                if tile == "gate":
                    pygame.draw.rect(self.screen, (90, 40, 60), (px + 10, py + 10, 12, 12))
        sel_reach = None
        sel_dist = None
        if self.selected and self.phase == "player" and self.selected.get("ap", 0) and "kind" in self.selected:
            sel_dist, _ = self.paths(self.selected["x"], self.selected["y"])
            sel_reach = {k for k, v in sel_dist.items() if 0 < v <= self.selected["ap"]}
        if sel_reach:
            for (rx, ry) in sel_reach:
                px, py = rx * TILE + BOARD_X, ry * TILE + BOARD_Y
                pygame.draw.rect(self.screen, (90, 200, 110), (px + 2, py + 2, TILE - 4, TILE - 4), 1)
                pygame.draw.rect(self.screen, (60, 120, 75), (px + 4, py + 4, TILE - 8, TILE - 8))
                cost_txt = self.font_sm.render(str(sel_dist[(rx, ry)]), True, (215, 235, 195))
                self.screen.blit(cost_txt, (px + 4, py + 3))
        if self.place_mode:
            for ty in range(BOARD_H):
                for tx in range(BOARD_W):
                    if self.grid[ty][tx] in TILES_WALK and not self.building_at(tx, ty) and not self.unit_at(tx, ty):
                        px, py = tx * TILE + BOARD_X, ty * TILE + BOARD_Y
                        pygame.draw.rect(self.screen, (130, 110, 60), (px + 2, py + 2, TILE - 4, TILE - 4), 1)
        pygame.draw.rect(self.screen, COL["panel"], (BOARD_X - 4, BOARD_Y - 4, BOARD_PX_W + 8, BOARD_PX_H + 8), 2)

    def _sprite_kind(self, unit):
        return unit["kind"]

    def _render_units(self):
        sel = self.selected
        for u in self.units:
            px, py = u["x"] * TILE + BOARD_X, u["y"] * TILE + BOARD_Y
            spr = get_sprite(self._sprite_kind(u))
            self.screen.blit(spr, (px + 2, py + 2))
            if self.phase == "player" and u["team"] == 0 and u["ap"] <= 0:
                self.screen.blit(_acted_overlay(), (px, py))
            if u is sel:
                pygame.draw.rect(self.screen, COL["gold"], (px + 1, py + 1, TILE - 2, TILE - 2), 2)
            bar_w = TILE - 6
            frac = max(0, u["hp"] / u["max_hp"])
            pygame.draw.rect(self.screen, (60, 40, 44), (px + 3, py + 26, bar_w, 3))
            pygame.draw.rect(self.screen, (200, 70, 60) if frac < 0.35 else (140, 210, 100), (px + 3, py + 26, int(bar_w * frac), 3))
            badge = pygame.Rect(px, py - 17, TILE, 15)
            pygame.draw.rect(self.screen, (14, 12, 20), badge)
            pygame.draw.rect(self.screen, COL["gold"] if u["ap"] > 0 else (70, 66, 82), badge, 1)
            ap_txt = self.font_sm.render("AP %d" % max(0, u["ap"]), True, COL["gold"] if u["ap"] > 0 else COL["dim"])
            self.screen.blit(ap_txt, (px + 3, py - 16))
        if sel and sel["team"] == 0 and sel.get("ap", 0) > 0:
            for e in self.enemy_units():
                d = abs(sel["x"] - e["x"]) + abs(sel["y"] - e["y"])
                if d <= 1 and sel.get("atk", 0) > 0:
                    cost_txt = self.font_sm.render("3", True, COL["gold"])
                elif 1 < d <= sel.get("range", 0) and sel.get("rng_atk", 0) > 0:
                    cost_txt = self.font_sm.render("4", True, COL["gold"])
                else:
                    continue
                epx, epy = e["x"] * TILE + BOARD_X, e["y"] * TILE + BOARD_Y
                color = COL["red"] if d <= 1 else (255, 150, 60)
                pygame.draw.circle(self.screen, color, (epx + 16, epy + 16), 18, 2)
                self.screen.blit(cost_txt, (epx + TILE - 18, epy))
        if self.cat_flash:
            fx, fy, ft = self.cat_flash
            px, py = fx * TILE + BOARD_X, fy * TILE + BOARD_Y
            spr = get_sprite("cat").copy()
            spr.set_alpha(255 if int(ft * 20) % 2 == 0 else 130)
            self.screen.blit(spr, (px + 6, py + 16))

    def _render_buildings(self):
        for b in self.buildings:
            px, py = b["x"] * TILE + BOARD_X, b["y"] * TILE + BOARD_Y
            spr = get_sprite(b["kind"])
            if b["kind"] == "van":
                self.screen.blit(spr, (px - 8, py - 2))
            else:
                self.screen.blit(spr, (px, py))
            if b["kind"] in ("core", "van", "tower"):
                bar_w = TILE - 6
                frac = max(0, b["hp"] / b["max_hp"])
                pygame.draw.rect(self.screen, (70, 60, 66), (px + 3, py + 28, bar_w, 3))
                pygame.draw.rect(self.screen, (160, 150, 110), (px + 3, py + 28, int(bar_w * frac), 3))
            if b["constructing"]:
                txt = self.font_sm.render("x%d" % b["constructing"], True, COL["gold"])
                self.screen.blit(txt, (px + 2, py + 2))

    def _render_topbar(self):
        y = 10
        ap_left = sum(u["ap"] for u in self.player_units())
        ap_ready = sum(1 for u in self.player_units() if u["ap"] > 0)
        ap_total = len(self.player_units())
        lines = [
            ("WAVE %d/4" % self.wave, COL["gold"]),
            ("TURN %d" % self.turn, COL["text"]),
            ("GRIT: %d" % self.grit, COL["green"]),
            ("BAND Lv.%d  XP:%d/%d" % (self.level, self.team_xp, 30 + (self.level - 1) * 26), COL["purple"]),
            ("AP LEFT %d | READY %d/%d" % (ap_left, ap_ready, ap_total), COL["green"] if ap_ready else COL["dim"]),
        ]
        x = 20
        for txt, col in lines:
            surf = self.font.render(txt, True, col)
            self.screen.blit(surf, (x, y))
            x += surf.get_width() + 26
        if self.phase == "horde":
            ph = self.font.render("HORDE TURN - FIGHT BACK NEXT ROUND", True, COL["red"])
            self.screen.blit(ph, (SCREEN_W - ph.get_width() - 16, y))
        else:
            ph = self.font.render("YOUR TURN - spend AP, then END TURN", True, COL["green"])
            self.screen.blit(ph, (SCREEN_W - ph.get_width() - 16, y))
        pygame.draw.line(self.screen, COL["panel"], (0, 62), (SCREEN_W, 62), 2)

    def _panel_info_lines(self, sel):
        lines = []
        if not sel:
            lines.append(("No selection", COL["dim"]))
            return lines
        name = "UNIT"
        if "hp" in sel and "team" in sel:
            name = KINDS.get(sel["kind"], {"name": sel["kind"]})["name"]
        else:
            name = BUILD_KINDS.get(sel["kind"], sel["kind"])["name"]
        lines.append((name, COL["gold"]))
        lines.append(("HP %d/%d" % (sel["hp"], sel["max_hp"]), COL["text"]))
        if sel.get("kind") == "tower":
            if sel.get("constructing", 0) > 0:
                lines.append(("UNDER CONSTRUCTION (%d turns)" % sel["constructing"], COL["gold"]))
            else:
                lines.append(("AUTO-FIRE: every foe in RNG 4", COL["red"]))
        if "ap" in sel:
            lines.append(("AP %d/%d" % (sel["ap"], sel["max_ap"]), COL["gold"]))
        if "atk" in sel:
            if sel.get("rng_atk", 0) > 0:
                lines.append(("MEL ATK %d | RG ATK %d (RNG %d)" % (sel["atk"], sel["rng_atk"], sel["range"]), COL["text"]))
            else:
                lines.append(("ATK %d (melee only)" % sel["atk"], COL["text"]))
        if sel.get("kind") == "frontman":
            lines.append(("CLICK FOE: melee / AZRAEL at range", COL["gold"]))
        if sel.get("team") == 0:
            if sel.get("atk", 0) > 0:
                lines.append(("MELEE = 3 AP", COL["green"]))
            if sel.get("rng_atk", 0) > 0:
                lines.append(("RANGED = 4 AP (reach %d)" % sel["range"], COL["green"]))
            lines.append(("MOVE = 1 AP per tile", COL["green"]))
            if sel.get("kind") == "frontman":
                if self.level >= 2:
                    lines.append(("SCREAM = 5 AP", COL["green"]))
                if self.level >= 4:
                    lines.append(("BLITZ = 5 AP", COL["green"]))
        return lines

    def _buttons_y(self, sel):
        return 20 + len(self._panel_info_lines(sel)) * 22 + 8

    def _render_panel(self):
        pygame.draw.rect(self.screen, COL["panel"], (HUD_X - 4, 8, HUD_W + 8, LOG_Y - 16))
        sel = self.selected
        x = HUD_X + 8
        y = 20
        for txt, col in self._panel_info_lines(sel):
            st = self.font_sm.render(txt, True, col)
            self.screen.blit(st, (x, y))
            y += 22
        y = self._buttons_y(sel)
        for label, key in self._buttons():
            rect = self._btn_rect(x, y)
            self._render_button(rect, label)
            y += 40

    def _render_button(self, rect, label):
        pygame.draw.rect(self.screen, COL["btn"], rect)
        pygame.draw.rect(self.screen, COL["panel2"], rect, 2)
        surf = self.font_sm.render(label, True, COL["text"])
        self.screen.blit(surf, (rect.x + 6, rect.y + 8))

    def _render_log(self):
        y = LOG_Y + 6
        for line in self.messages:
            surf = self.font_sm.render(line, True, COL["dim"])
            self.screen.blit(surf, (BOARD_X + 4, y))
            y += 20

    def _render_banner(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((30, 20, 40, 120))
        if self.banner_t > 1.0:
            self.screen.blit(overlay, (0, 0))
        txt = self.font_lg.render(self.banner, True, COL["gold"])
        self.screen.blit(txt, ((SCREEN_W - txt.get_width()) // 2, 280))

    def _render_pause(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((10, 8, 14, 190))
        self.screen.blit(overlay, (0, 0))
        txt = self.font_lg.render("PAUSED", True, COL["gold"])
        self.screen.blit(txt, ((SCREEN_W - txt.get_width()) // 2, 220))
        self._render_button(self._btn_rect(HUD_X + 40, 360), "RETRY (R)")
        self._render_button(self._btn_rect(HUD_X + 40, 420), "QUIT (ESC)")
        hint = self.font_sm.render("ESC resumes", True, COL["dim"])
        self.screen.blit(hint, ((SCREEN_W - hint.get_width()) // 2, 500))

    def _render_win(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((15, 30, 18, 200))
        self.screen.blit(overlay, (0, 0))
        txt = self.font_lg.render("THE STAGE HOLDS", True, COL["green"])
        self.screen.blit(txt, ((SCREEN_W - txt.get_width()) // 2, 240))
        for i, line in enumerate(["All 4 waves crushed. The crowd wants more.", "", "R - play again    ESC - quit"]):
            st = self.font.render(line, True, COL["text"])
            self.screen.blit(st, ((SCREEN_W - st.get_width()) // 2, 340 + i * 30))

    def _render_lose(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((40, 12, 12, 200))
        self.screen.blit(overlay, (0, 0))
        txt = self.font_lg.render("THE STAGE FALLS", True, COL["red"])
        self.screen.blit(txt, ((SCREEN_W - txt.get_width()) // 2, 240))
        for i, line in enumerate(["The horde owns the venue. Your returrrrn is written in their lyrics.", "", "R - try again    ESC - quit"]):
            st = self.font.render(line, True, COL["text"])
            self.screen.blit(st, ((SCREEN_W - st.get_width()) // 2, 340 + i * 30))


def main():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    pygame.init()
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
    except Exception:
        pass
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("T3MP3ST // STAGE FRIGHT")
    demo = Demo(screen)
    fullscreen = False
    fullscreen_surf = None
    running = True
    while running:
        dt = demo.clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    info = pygame.display.Info()
                    fullscreen_surf = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
                    demo.screen = fullscreen_surf
                else:
                    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
                    demo.screen = screen
            demo.handle_event(e)
        demo.update(dt)
        target = demo.screen
        target.fill(COL["hudbg"])
        surf_buf = None
        if demo.screen is not screen and fullscreen:
            surf_buf = pygame.Surface((SCREEN_W, SCREEN_H))
            previous = demo.screen
            demo.screen = surf_buf
            demo.render()
            demo.screen = previous
            scaled = pygame.transform.scale(surf_buf, previous.get_size())
            previous.blit(scaled, (0, 0))
        else:
            demo.render()
        pygame.display.flip()
        if demo.state == STATE_DONE:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()