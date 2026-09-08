import pygame
import sys
import os
import math
import random
import json
import struct
import array
from enum import Enum, auto

import battle_bridge
import fxkit

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

pygame.init()

SCREEN_W, SCREEN_H = 1024, 768
FPS = 30
TILE = 32

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("T3MP3ST - Belligerent Dickhead vs The Beast")
clock = pygame.time.Clock()

fullscreen = False


def toggle_fullscreen():
    global screen, fullscreen
    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

ASSETS = os.path.dirname(__file__)
MUSIC_DIR = os.path.join(ASSETS, "assets", "music")
IMAGES_DIR = os.path.join(ASSETS, "assets", "images")
PORTRAITS_DIR = os.path.join(ASSETS, "assets", "portraits")


def load_hd_images():
    imgs = {}
    if os.path.isdir(IMAGES_DIR):
        for f in os.listdir(IMAGES_DIR):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                key = os.path.splitext(f)[0]
                try:
                    img = pygame.image.load(os.path.join(IMAGES_DIR, f)).convert()
                    img = pygame.transform.smoothscale(img, (SCREEN_W, SCREEN_H))
                    imgs[key] = img
                except Exception:
                    pass
    return imgs


def load_music_files():
    tracks = []
    if os.path.isdir(MUSIC_DIR):
        for f in sorted(os.listdir(MUSIC_DIR)):
            if f.lower().endswith((".mp3", ".ogg", ".wav")):
                tracks.append({"path": os.path.join(MUSIC_DIR, f), "name": f})
    return tracks


# Human-readable labels for item interact keys (shared by the on-screen
# interaction prompt and the generated ASSET_MANIFEST.md reference).
ITEM_LABELS = {
    "beer": "a warm beer",
    "microphone": "a stage mic",
    "key": "the rusted key",
    "crypt_key": "the DO NOT USE key",
    "weapon": "a shattered bottle",
    "health": "a bloodied rag",
    "blood": "a pool of blood",
    "blood_puddle": "a pool of blood",
    "mysterious_lager": "a laced lager",
    "merch_bloody_rag": "a bloody rag",
    "guitaraxe": "the Guitar-Axe",
    "mixer_fader": "the Master Fader",
    "broken_bottle": "the Broken Bottle",
    "pit_mystery_vial": "a glowing vial",
    "vip_broken_lamp": "a cracked stage lamp",
    "vip_energy_drink": "a sketchy drink",
    "vip_blood": "a slick of blood",
    "chamber_vial": "a vial of Pit Lord blood",
    "tome_power_chord": "an ancient setlist",
    "tome_double_down": "a cursed vinyl",
    "tome_feedback_howl": "a rusted effects pedal",
    "booth_earplugs": "sound-dampening earplugs",
}

TYPE_LABELS = {
    "beer": "a beer",
    "microphone": "a stage mic",
    "key": "a key",
    "weapon": "a weapon",
    "health": "a healing item",
    "blood": "blood",
    "tome": "a tome of power",
}


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    DIALOGUE = auto()
    HD_REVEAL = auto()
    GAME_OVER = auto()
    INVENTORY = auto()
    CUTSCENE = auto()
    CREDITS = auto()


class Fonts:
    def __init__(self):
        self.body = pygame.font.SysFont("consolas", 18)
        self.body_big = pygame.font.SysFont("consolas", 28)
        self.title = pygame.font.SysFont("impact", 64)
        self.small = pygame.font.SysFont("consolas", 14)
        self.band = pygame.font.SysFont("impact", 36)

    def render(self, text, color=(200, 200, 200), big=False):
        f = self.body_big if big else self.body
        return f.render(text, True, color)

    def render_small(self, text, color=(150, 150, 150)):
        return self.small.render(text, True, color)

    def render_title(self, text, color=(180, 0, 0)):
        return self.title.render(text, True, color)

    def render_band(self, text, color=(200, 50, 50)):
        return self.band.render(text, True, color)


fonts = Fonts()


class ProceduralAudio:
    RATE = 22050

    @staticmethod
    def _make_sound(samples):
        if HAS_NUMPY:
            mono = np.array(samples, dtype=np.float32)
            mono = np.clip(mono, -1.0, 1.0)
            stereo = np.column_stack([mono, mono])
            arr = (stereo * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(arr)
        else:
            ints = [max(-32768, min(32767, int(s * 32767))) for s in samples]
            stereo = array.array('h')
            for v in ints:
                stereo.append(v)
                stereo.append(v)
            sound = pygame.sndarray.make_sound(stereo)
        return sound

    @staticmethod
    def generate_hit():
        samples = []
        for i in range(800):
            t = i / ProceduralAudio.RATE
            env = max(0, 1 - t * 15)
            noise = random.uniform(-1, 1) * 0.3
            freq = 200 * (1 - t * 5)
            tone = math.sin(2 * math.pi * freq * t) * 0.7
            samples.append((tone + noise) * env)
        return ProceduralAudio._make_sound(samples)

    @staticmethod
    def generate_hurt():
        samples = []
        for i in range(1200):
            t = i / ProceduralAudio.RATE
            env = max(0, 1 - t * 8)
            freq = 150 + math.sin(t * 40) * 100
            tone = math.sin(2 * math.pi * freq * t) * 0.5
            noise = random.uniform(-1, 1) * 0.2 * env
            samples.append((tone + noise) * env)
        return ProceduralAudio._make_sound(samples)

    @staticmethod
    def generate_pickup():
        samples = []
        for i in range(600):
            t = i / ProceduralAudio.RATE
            env = max(0, 1 - t * 10)
            freq = 400 + t * 2000
            tone = math.sin(2 * math.pi * freq * t) * 0.6
            samples.append(tone * env)
        return ProceduralAudio._make_sound(samples)

    @staticmethod
    def generate_heal():
        samples = []
        for i in range(800):
            t = i / ProceduralAudio.RATE
            env = max(0, 1 - t * 8)
            freq = 500 + math.sin(t * 10) * 200
            tone = math.sin(2 * math.pi * freq * t) * 0.4
            tone2 = math.sin(2 * math.pi * freq * 1.5 * t) * 0.2
            samples.append((tone + tone2) * env)
        return ProceduralAudio._make_sound(samples)

    @staticmethod
    def generate_door():
        samples = []
        for i in range(1500):
            t = i / ProceduralAudio.RATE
            env = max(0, 1 - t * 5)
            freq = 80 + math.sin(t * 3) * 30
            tone = math.sin(2 * math.pi * freq * t) * 0.5
            creak = math.sin(2 * math.pi * 120 * t) * math.sin(2 * math.pi * 3 * t) * 0.3
            samples.append((tone + creak) * env)
        return ProceduralAudio._make_sound(samples)

    @staticmethod
    def generate_menu_drone():
        samples = []
        duration = 4.0
        n = int(ProceduralAudio.RATE * duration)
        for i in range(n):
            t = i / ProceduralAudio.RATE
            env = min(1, t * 2) * min(1, (duration - t) * 2)
            base = math.sin(2 * math.pi * 55 * t) * 0.3
            sub = math.sin(2 * math.pi * 27.5 * t) * 0.2
            dist = math.tanh(base * 3) * 0.4
            rumble = math.sin(2 * math.pi * 40 * t + math.sin(t * 2) * 3) * 0.15
            samples.append((dist + sub + rumble) * env)
        return ProceduralAudio._make_sound(samples)

    @staticmethod
    def generate_combat_riff():
        samples = []
        duration = 3.0
        n = int(ProceduralAudio.RATE * duration)
        notes = [110, 110, 130.81, 110, 146.83, 130.81, 110, 98]
        note_len = n // len(notes)
        for idx, freq in enumerate(notes):
            for i in range(note_len):
                t = i / ProceduralAudio.RATE
                progress = i / note_len
                env = max(0, 1 - progress * 1.5) * min(1, progress * 20)
                saw = 0
                for h in range(1, 6):
                    saw += math.sin(2 * math.pi * freq * h * t) / h
                saw *= 0.3
                palm = math.sin(2 * math.pi * freq * 2 * t) * 0.15 * env
                samples.append((saw + palm) * env * 0.6)
        return ProceduralAudio._make_sound(samples)


class SoundManager:
    # Narrative music slots. Players can drop files matching these names
    # (or numbered variants like 01-stage.mp3) into assets/music/ and they
    # play at the matching moment in-game.
    MUSIC_SLOTS = [
        "menu", "intro", "stage", "backstage", "merch", "pit", "greenroom",
        "booth", "chamber", "combat", "boss", "levelup", "discovery",
        "victory", "ending", "credits",
    ]

    # Room name -> music slot played while exploring that room.
    ROOM_SLOT = {
        "The Stage of Sin": "stage",
        "Backstage Gore": "backstage",
        "The Merch Table of Madness": "merch",
        "The Mosh Pit of Souls": "pit",
        "The Green Room of Vile": "greenroom",
        "The Sound Booth of Despair": "booth",
        "The Pit Lord's Chamber": "chamber",
    }

    def __init__(self):
        self.external_tracks = load_music_files()
        self.current_track = -1
        self.music_volume = 0.4
        self.sfx_volume = 0.7
        self.muted = False
        self.sfx_cache = {}
        self.music_channel = None
        self.jingle_channel = None
        self.using_external = False

        try:
            pygame.mixer.set_num_channels(8)
            self.music_channel = pygame.mixer.Channel(0)
            self.jingle_channel = pygame.mixer.Channel(1)
        except Exception:
            self.jingle_channel = None

        self._generate_sfx()
        self._generate_music_loops()
        self.slots = self._scan_music_slots()
        self.ambient_slot = None
        self.jingle_cache = {}
        self._pending_announce = False

    def _generate_sfx(self):
        self.sfx_cache["hit"] = ProceduralAudio.generate_hit()
        self.sfx_cache["hurt"] = ProceduralAudio.generate_hurt()
        self.sfx_cache["pickup"] = ProceduralAudio.generate_pickup()
        self.sfx_cache["heal"] = ProceduralAudio.generate_heal()
        self.sfx_cache["door"] = ProceduralAudio.generate_door()

    def _generate_music_loops(self):
        self.menu_drone = ProceduralAudio.generate_menu_drone()
        self.combat_riff = ProceduralAudio.generate_combat_riff()

    @staticmethod
    def _strip_numeric_prefix(name):
        i = 0
        while i < len(name) and name[i].isdigit():
            i += 1
        if i and i < len(name) and name[i] in ("-", "_", " "):
            i += 1
        return name[i:]

    def _scan_music_slots(self):
        slots = {}
        if os.path.isdir(MUSIC_DIR):
            for f in sorted(os.listdir(MUSIC_DIR)):
                if not f.lower().endswith((".mp3", ".ogg", ".wav")):
                    continue
                base = os.path.splitext(f)[0].lower()
                stripped = self._strip_numeric_prefix(base).lower()
                for slot in self.MUSIC_SLOTS:
                    if slot in (base, stripped):
                        slots.setdefault(slot, os.path.join(MUSIC_DIR, f))
        return slots

    def play_ambient(self, slot, force=True):
        if self.muted:
            return
        path = self.slots.get(slot)
        if not path:
            if slot in ("menu", "intro", "ending", "credits"):
                self._play_procedural("menu")
            elif slot in ("combat", "boss"):
                self._play_procedural("combat")
            else:
                self._stop_procedural()
                self.stop_file()
                self.ambient_slot = None
            return
        self._stop_procedural()
        if force or self.ambient_slot != slot or not self._file_playing():
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(0 if self.muted else self.music_volume)
                pygame.mixer.music.play(-1)
                self.using_external = True
                self.ambient_slot = slot
                self._pending_announce = True
            except Exception:
                pass

    def _play_procedural(self, kind):
        self.stop_file()
        snd = self.menu_drone if kind == "menu" else self.combat_riff
        if not snd:
            return
        try:
            snd.play(-1)
        except Exception:
            pass
        self.ambient_slot = kind
        self._pending_announce = True

    def _stop_procedural(self):
        try:
            self.menu_drone.stop()
            self.combat_riff.stop()
        except Exception:
            pass

    def stop_file(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def _file_playing(self):
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False

    def play_menu_music(self):
        self.play_ambient("menu", force=True)

    def stop_menu_music(self):
        self.stop_music()

    def play_combat_music(self):
        self.play_ambient("combat", force=True)

    def stop_combat_music(self):
        if self.ambient_slot in ("combat", "boss"):
            self._stop_procedural()
            self.stop_file()
            self.ambient_slot = None
        else:
            self._stop_procedural()

    def jingle(self, slot):
        path = self.slots.get(slot)
        if not path or self.muted or not self.jingle_channel:
            return
        snd = self.jingle_cache.get(slot)
        if snd is None:
            try:
                snd = pygame.mixer.Sound(path)
            except Exception:
                return
            self.jingle_cache[slot] = snd
        try:
            self.jingle_channel.play(snd)
        except Exception:
            pass

    def current_track_name(self):
        if self.ambient_slot:
            path = self.slots.get(self.ambient_slot)
            if path:
                return os.path.basename(path)
            if self.ambient_slot == "menu":
                return "Procedural Hellnoise (menu drone)"
            if self.ambient_slot in ("combat", "boss"):
                return "Procedural Combat Riff"
        return "silence"

    def take_announce(self):
        if not self._pending_announce:
            return None
        self._pending_announce = False
        return self.current_track_name()

    def stop_music(self):
        pygame.mixer.music.stop()
        self._stop_procedural()
        self.ambient_slot = None

    def play_sfx(self, name):
        snd = self.sfx_cache.get(name)
        if snd and not self.muted:
            try:
                snd.play()
            except Exception:
                pass

    def toggle_mute(self):
        self.muted = not self.muted
        v = 0 if self.muted else self.music_volume
        try:
            pygame.mixer.music.set_volume(v)
        except Exception:
            pass
        try:
            if self.music_channel:
                self.music_channel.set_volume(v)
        except Exception:
            pass

    def get_track_name(self):
        return self.current_track_name()


sound = SoundManager()
hd_images = load_hd_images()


class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.shake = 0

    def update(self):
        if self.shake > 0.5:
            self.x = random.randint(-int(self.shake), int(self.shake))
            self.y = random.randint(-int(self.shake), int(self.shake))
            self.shake *= 0.9
        else:
            self.x = 0
            self.y = 0
            self.shake = 0

    def add_shake(self, amount):
        self.shake = min(self.shake + amount, 25)


camera = Camera()


class PixelArt:
    @staticmethod
    def draw_character(surface, x, y, facing="down", frame=0, color=(240, 130, 90), scale=2):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        c = color
        dark = tuple(max(0, v - 60) for v in c)
        light = tuple(min(255, v + 60) for v in c)

        s.set_at((7, 2), c)
        s.set_at((8, 2), c)
        s.set_at((6, 3), c)
        s.set_at((7, 3), light)
        s.set_at((8, 3), light)
        s.set_at((9, 3), c)

        if facing == "down":
            s.set_at((6, 4), (255, 255, 255))
            s.set_at((9, 4), (255, 255, 255))
            s.set_at((7, 5), (200, 0, 0))
            s.set_at((8, 5), (200, 0, 0))
        elif facing == "up":
            s.set_at((7, 3), dark)
            s.set_at((8, 3), dark)
        elif facing == "left":
            s.set_at((6, 4), (255, 255, 255))
            s.set_at((7, 5), (200, 0, 0))
        elif facing == "right":
            s.set_at((9, 4), (255, 255, 255))
            s.set_at((8, 5), (200, 0, 0))

        for dy in range(6, 10):
            s.set_at((6, dy), c)
            s.set_at((7, dy), c)
            s.set_at((8, dy), c)
            s.set_at((9, dy), c)

        s.set_at((5, 7), c)
        s.set_at((10, 7), c)
        s.set_at((7, 10), dark)
        s.set_at((8, 10), dark)

        if frame % 2 == 0:
            s.set_at((6, 11), dark)
            s.set_at((9, 11), dark)
        else:
            s.set_at((5, 11), dark)
            s.set_at((10, 11), dark)

        scaled = pygame.transform.scale(s, (16 * scale, 16 * scale))
        surface.blit(scaled, (x - 16, y - 24))

    @staticmethod
    def draw_enemy(surface, x, y, etype="demon", frame=0, scale=2):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)

        if etype == "demon":
            c = (120, 0, 0)
            dark = (60, 0, 0)
            s.set_at((6, 1), (200, 0, 0))
            s.set_at((9, 1), (200, 0, 0))
            for dx in range(5, 11):
                s.set_at((dx, 2), c)
                s.set_at((dx, 3), c)
            s.set_at((6, 3), (255, 255, 0))
            s.set_at((9, 3), (255, 255, 0))
            for dy in range(4, 10):
                for dx in range(5, 11):
                    s.set_at((dx, dy), c)
            s.set_at((4, 5), dark)
            s.set_at((11, 5), dark)
            s.set_at((3, 6), dark)
            s.set_at((12, 6), dark)
            s.set_at((7, 10), dark)
            s.set_at((8, 10), dark)

        elif etype == "corpse":
            c = (80, 60, 60)
            for dx in range(3, 13):
                s.set_at((dx, 8), c)
            s.set_at((3, 7), c)
            s.set_at((12, 7), c)
            s.set_at((4, 6), c)
            s.set_at((11, 6), c)
            if frame % 2 == 0:
                s.set_at((5, 5), (150, 0, 0))
                s.set_at((6, 6), (150, 0, 0))

        elif etype == "shadow":
            c = (30, 0, 40)
            for dx in range(4, 12):
                for dy in range(2, 12):
                    if random.random() > 0.3:
                        s.set_at((dx, dy), c)
            s.set_at((6, 4), (200, 0, 200))
            s.set_at((9, 4), (200, 0, 200))

        elif etype == "zombie":
            c = (60, 80, 50)
            dark = (30, 50, 25)
            for dx in range(5, 11):
                for dy in range(2, 10):
                    s.set_at((dx, dy), c)
            s.set_at((6, 3), (200, 200, 0))
            s.set_at((9, 3), (200, 200, 0))
            s.set_at((4, 6), dark)
            s.set_at((11, 7), dark)
            s.set_at((7, 10), dark)
            s.set_at((8, 10), dark)

        elif etype == "engineer":
            c = (50, 60, 140)
            dark = (30, 40, 90)
            for dx in range(5, 11):
                for dy in range(3, 11):
                    s.set_at((dx, dy), c)
            s.set_at((4, 5), dark)
            s.set_at((11, 5), dark)
            s.set_at((3, 7), dark)
            s.set_at((12, 7), dark)
            s.set_at((7, 4), (255, 220, 50))
            s.set_at((8, 4), (255, 220, 50))
            s.set_at((7, 2), (220, 220, 230))
            s.set_at((8, 2), (220, 220, 230))
            if frame % 3 == 0:
                s.set_at((6, 7), (255, 80, 0))
                s.set_at((9, 7), (0, 200, 255))

        elif etype == "beast":
            c = (160, 20, 10)
            dark = (80, 0, 0)
            horn = (220, 220, 230)
            for dx in range(4, 12):
                for dy in range(2, 12):
                    s.set_at((dx, dy), c)
            s.set_at((5, 1), horn)
            s.set_at((6, 1), horn)
            s.set_at((10, 1), horn)
            s.set_at((9, 1), horn)
            s.set_at((7, 1), (50, 0, 0))
            s.set_at((8, 1), (50, 0, 0))
            s.set_at((6, 3), (255, 80, 0))
            s.set_at((9, 3), (255, 80, 0))
            s.set_at((4, 5), dark)
            s.set_at((11, 5), dark)
            s.set_at((3, 7), dark)
            s.set_at((12, 7), dark)
            for dy in range(10, 12):
                for dx in range(5, 11):
                    s.set_at((dx, dy), dark)
            if frame % 2 == 0:
                s.set_at((5, 8), (255, 255, 0))
                s.set_at((10, 8), (255, 255, 0))

        scaled = pygame.transform.scale(s, (16 * scale, 16 * scale))
        surface.blit(scaled, (x - 16, y - 24))

    @staticmethod
    def draw_item(surface, x, y, item_type="blood", scale=2):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)

        if item_type == "blood":
            c = (150, 0, 0)
            for dx in range(4, 12):
                for dy in range(5, 11):
                    if random.random() > 0.2:
                        s.set_at((dx, dy), c)
        elif item_type == "key":
            c = (200, 180, 50)
            for pos in [(7,3),(8,3),(7,4),(8,4)]:
                s.set_at(pos, c)
            for dy in range(5, 11):
                s.set_at((7, dy), c)
                s.set_at((8, dy), c)
            s.set_at((9, 9), c)
            s.set_at((10, 9), c)
        elif item_type == "weapon":
            c = (180, 180, 180)
            for dx in range(7, 14):
                s.set_at((dx, 5), c)
            s.set_at((6, 6), c)
            s.set_at((7, 7), (100, 70, 40))
            s.set_at((8, 8), (100, 70, 40))
        elif item_type == "health":
            c = (0, 180, 0)
            for dx in range(5, 11):
                s.set_at((dx, 7), c)
            for dy in range(4, 11):
                s.set_at((7, dy), c)
        elif item_type == "beer":
            c = (200, 180, 50)
            for dy in range(3, 11):
                for dx in range(6, 10):
                    s.set_at((dx, dy), c)
            for pos in [(6,2),(9,2),(7,1),(8,1)]:
                s.set_at(pos, (180, 180, 180))
        elif item_type == "tome":
            c = (200, 180, 120)
            dark = (120, 100, 60)
            for dx in range(5, 12):
                for dy in range(3, 13):
                    s.set_at((dx, dy), c)
            for dy in range(3, 14):
                s.set_at((5, dy), dark)
            for row in (5, 8, 11):
                for dx in range(7, 12):
                    s.set_at((dx, row), dark)

        elif item_type == "microphone":
            c = (100, 100, 100)
            for dy in range(1, 7):
                s.set_at((7, dy), c)
                s.set_at((8, dy), c)
            for pos in [(6,1),(7,0),(8,0),(9,1)]:
                s.set_at(pos, (150, 150, 150))
            for dy in range(7, 10):
                s.set_at((7, dy), (60, 40, 20))
                s.set_at((8, dy), (60, 40, 20))

        scaled = pygame.transform.scale(s, (16 * scale, 16 * scale))
        surface.blit(scaled, (x - 16, y - 16))

    @staticmethod
    def draw_tile(surface, x, y, tile_type="floor"):
        if tile_type == "floor":
            surface.fill((40, 35, 30), (x, y, TILE, TILE))
            for _ in range(3):
                sx = x + random.randint(0, TILE - 2)
                sy = y + random.randint(0, TILE - 2)
                surface.set_at((sx, sy), (50, 45, 40))
        elif tile_type == "wall":
            surface.fill((60, 50, 45), (x, y, TILE, TILE))
            pygame.draw.rect(surface, (45, 38, 33), (x, y, TILE, TILE), 1)
        elif tile_type == "door":
            surface.fill((80, 50, 20), (x, y, TILE, TILE))
            pygame.draw.rect(surface, (100, 70, 30), (x + 4, y + 2, TILE - 8, TILE - 4))
            pygame.draw.circle(surface, (180, 160, 50), (x + TILE - 8, y + TILE // 2), 3)
        elif tile_type == "locked_door":
            surface.fill((80, 50, 20), (x, y, TILE, TILE))
            pygame.draw.rect(surface, (100, 70, 30), (x + 4, y + 2, TILE - 8, TILE - 4))
            pygame.draw.circle(surface, (180, 160, 50), (x + TILE - 8, y + TILE // 2), 3)
            pygame.draw.line(surface, (150, 150, 150), (x + 6, y + 10), (x + TILE - 6, y + 2), 2)
            pygame.draw.line(surface, (200, 200, 60), (x + 4, y + TILE - 6), (x + TILE - 4, y + 6), 2)
        elif tile_type == "blood_floor":
            surface.fill((40, 35, 30), (x, y, TILE, TILE))
            for _ in range(8):
                bx = x + random.randint(2, TILE - 3)
                by = y + random.randint(2, TILE - 3)
                surface.set_at((bx, by), (100, 10, 10))
        elif tile_type == "wall_blood":
            surface.fill((60, 50, 45), (x, y, TILE, TILE))
            pygame.draw.rect(surface, (45, 38, 33), (x, y, TILE, TILE), 1)
            for _ in range(12):
                bx = x + random.randint(1, TILE - 2)
                by = y + random.randint(1, TILE - 2)
                surface.set_at((bx, by), (120, 10, 10))
        elif tile_type == "stage":
            surface.fill((50, 30, 30), (x, y, TILE, TILE))
            pygame.draw.rect(surface, (70, 40, 40), (x + 2, y + 2, TILE - 4, TILE - 4))
        elif tile_type == "speaker":
            surface.fill((30, 30, 35), (x, y, TILE, TILE))
            pygame.draw.rect(surface, (50, 50, 55), (x + 4, y + 4, TILE - 8, TILE - 8))
            pygame.draw.circle(surface, (20, 20, 25), (x + TILE // 2, y + TILE // 2), 8)
            pygame.draw.circle(surface, (40, 40, 45), (x + TILE // 2, y + TILE // 2), 4)


class PortraitSystem:
    """Placeholder portrait art generator + loader.

    Draws a hero/enemy/item mugshot procedurally so the game looks complete
    with no external files. To use your own art later, drop a PNG named
    <key>.png into assets/portraits/ and it replaces the generated placeholder
    automatically (e.g. player.png, beast.png, crypt_key.png).
    """
    SIZE = (160, 160)

    def __init__(self):
        self.cache = {}
        os.makedirs(PORTRAITS_DIR, exist_ok=True)

    def _load_file(self, key):
        path = os.path.join(PORTRAITS_DIR, key + ".png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.smoothscale(img, self.SIZE)
            except Exception:
                return None
        return None

    def get(self, key):
        key = str(key).lower().replace(" ", "_")
        if key in self.cache:
            return self.cache[key]
        img = self._load_file(key)
        if img is None:
            img = self._generate(key)
        self.cache[key] = img
        return img

    def _surface(self, face_color, features=None):
        s = pygame.Surface(self.SIZE, pygame.SRCALPHA)
        random.seed(hash(face_color) & 0xFFFF)
        dark = tuple(max(0, v - 50) for v in face_color)
        light = tuple(min(255, v + 50) for v in face_color)
        # scale factor to draw 32x32 art then scale up
        art = pygame.Surface((32, 32), pygame.SRCALPHA)
        for dx in range(6, 26):
            for dy in range(4, 28):
                if 7 <= dx <= 24 and 6 <= dy <= 26:
                    art.set_at((dx, dy), face_color)
        # eyes
        art.set_at((11, 12), (255, 255, 255))
        art.set_at((20, 12), (255, 255, 255))
        art.set_at((12, 13), (0, 0, 0))
        art.set_at((21, 13), (0, 0, 0))
        if features:
            for spec in features:
                kind = spec[0]
                if kind == "mouth":
                    for dx in range(spec[1], spec[2]):
                        art.set_at((dx, spec[3]), (0, 0, 0))
                elif kind == "scar":
                    for dx in range(8, 24):
                        art.set_at((dx, 18), (150, 0, 0))
                elif kind == "horns":
                    hc = spec[4] if len(spec) > 4 else (220, 220, 230)
                    art.set_at((9, 3), hc)
                    art.set_at((22, 3), hc)
                elif kind == "glow":
                    art.set_at((10, 11), (255, 255, 0))
                    art.set_at((19, 11), (255, 255, 0))
                elif kind == "teeth":
                    for dx in range(spec[1], spec[2]):
                        art.set_at((dx, 20), (230, 230, 230))
        scaled = pygame.transform.scale(art, self.SIZE)
        s.blit(scaled, (0, 0))
        # border
        pygame.draw.rect(s, (180, 40, 40), s.get_rect(), 6)
        pygame.draw.rect(s, dark, s.get_rect(), 1)
        random.seed()
        return s

    def _generate(self, key):
        if key == "player" or key == "belligerent_dickhead":
            return self._surface((180, 60, 60), [("mouth", 12, 19, 22), ("scar",)])
        if key in ("zombie",):
            return self._surface((90, 110, 60), [("mouth", 12, 19, 22), ("glow",), ("teeth", 10, 21)])
        if key in ("corpse",):
            return self._surface((100, 70, 70), [("mouth", 13, 18, 22)])
        if key in ("shadow",):
            return self._surface((40, 0, 60), [("glow",), ("mouth", 12, 19, 22)])
        if key in ("demon",):
            return self._surface((150, 30, 30), [("horns",), ("glow",), ("teeth", 9, 22), ("mouth", 11, 20, 18)])
        if key in ("beast",):
            return self._surface((200, 30, 10), [("horns",), ("glow",), ("teeth", 8, 23), ("scar",), ("mouth", 10, 21, 18)])
        if key in ("engineer",):
            return self._surface((60, 70, 160), [("glow",), ("mouth", 12, 19, 22)])
        if key in ("tome_power_chord", "tome_double_down", "tome_feedback_howl"):
            return self._item_surface((200, 180, 120), "tome")
        if key == "booth_earplugs":
            return self._item_surface((80, 190, 200), "health")
        if key in ("roadie", "last_roadie"):
            return self._surface((120, 40, 40), [("mouth", 13, 18, 22)])
        if key in ("sketchy_vendor",):
            return self._surface((90, 40, 120), [("mouth", 12, 19, 22)])
        # items
        if key in ("beer", "mysterious_lager"):
            return self._item_surface((200, 180, 50), "beer")
        if key in ("microphone", "mic"):
            return self._item_surface((120, 120, 130), "mic")
        if key in ("key", "crypt_key"):
            return self._item_surface((200, 180, 50), "key")
        if key in ("weapon", "broken_bottle", "vip_broken_lamp", "guitaraxe"):
            return self._item_surface((180, 180, 180), "weapon")
        if key in ("health", "energy_drink", "vip_energy_drink", "merch_bloody_rag",
                   "pit_mystery_vial", "chamber_vial"):
            return self._item_surface((0, 190, 0), "health")
        if key in ("blood", "blood_puddle", "vip_blood"):
            return self._item_surface((150, 0, 0), "blood")
        # generic / npc fallback
        return self._surface((100, 100, 100), [("mouth", 13, 18, 22)])

    def _item_surface(self, color, kind):
        s = pygame.Surface(self.SIZE, pygame.SRCALPHA)
        art = pygame.Surface((32, 32), pygame.SRCALPHA)
        dark = tuple(max(0, v - 60) for v in color)
        if kind == "beer":
            for dx in range(12, 20):
                for dy in range(6, 24):
                    art.set_at((dx, dy), color)
            for dx in range(11, 21):
                art.set_at((dx, 5), (180, 180, 180))
        elif kind == "mic":
            for dx in range(14, 18):
                for dy in range(4, 12):
                    art.set_at((dx, dy), (160, 160, 170))
            for dx in range(11, 21):
                for dy in range(12, 16):
                    art.set_at((dx, dy), (150, 150, 160))
        elif kind == "key":
            for dx in range(14, 21):
                for dy in range(8, 16):
                    art.set_at((dx, dy), color)
            for dy in range(16, 24):
                art.set_at((16, dy), color)
                art.set_at((17, dy), color)
            art.set_at((19, 22), color)
            art.set_at((20, 22), color)
        elif kind == "weapon":
            for dx in range(12, 24):
                art.set_at((dx, 16), (180, 180, 180))
            for dy in range(16, 24):
                art.set_at((12, dy), (120, 80, 40))
        elif kind == "health":
            for dx in range(11, 21):
                for dy in range(14, 20):
                    art.set_at((dx, dy), (0, 190, 0))
            for dy in range(6, 14):
                art.set_at((14, dy), (0, 190, 0))
        elif kind == "blood":
            for dx in range(8, 24):
                for dy in range(10, 24):
                    if random.random() > 0.2:
                        art.set_at((dx, dy), (150, 0, 0))
        scaled = pygame.transform.scale(art, self.SIZE)
        s.blit(scaled, (0, 0))
        pygame.draw.rect(s, (180, 40, 40), s.get_rect(), 6)
        return s


portraits = PortraitSystem()


class Room:
    def __init__(self, name, width, height, tiles, enemies=None, items=None,
                 npcs=None, doors=None, ambient_color=(20, 15, 15), objective="",
                 objective_portrait=""):
        self.name = name
        self.width = width
        self.height = height
        self.ambient_color = ambient_color
        self.tiles = tiles
        self.enemies = enemies or []
        self.items = items or []
        self.npcs = npcs or []
        self.doors = doors or []
        self.objective = objective
        self.objective_portrait = objective_portrait
        self.discovered = False
        self.tile_surface = None
        self._build_background()

    def _build_background(self):
        self.tile_surface = pygame.Surface((self.width * TILE, self.height * TILE))
        random.seed(hash(self.name))
        for y in range(self.height):
            for x in range(self.width):
                PixelArt.draw_tile(self.tile_surface, x * TILE, y * TILE, self.tiles[y][x])
        random.seed()

    def render(self, surface, cam_x=0, cam_y=0, locked_door_keys=None):
        locked_door_keys = locked_door_keys or set()
        surface.blit(self.tile_surface, (-cam_x, -cam_y))
        for item in self.items:
            if item.get("active", True):
                ix = item["x"] * TILE + TILE // 2 - cam_x
                iy = item["y"] * TILE + TILE // 2 - cam_y
                PixelArt.draw_item(surface, ix, iy, item["type"])
        for npc in self.npcs:
            if npc.get("active", True):
                nx = npc["x"] * TILE + TILE // 2 - cam_x
                ny = npc["y"] * TILE + TILE // 2 - cam_y
                PixelArt.draw_character(surface, nx, ny, color=npc.get("color", (100, 100, 200)))
        for enemy in self.enemies:
            if enemy.get("active", True):
                ex = enemy["x"] * TILE + TILE // 2 - cam_x
                ey = enemy["y"] * TILE + TILE // 2 - cam_y
                PixelArt.draw_enemy(surface, ex, ey, enemy["type"],
                                    frame=pygame.time.get_ticks() // 200)
        for door in self.doors:
            dx = door["x"] * TILE - cam_x
            dy = door["y"] * TILE - cam_y
            if id(door) in locked_door_keys:
                PixelArt.draw_tile(surface, dx, dy, "locked_door")
            else:
                PixelArt.draw_tile(surface, dx, dy, "door")

    def get_tile(self, tx, ty):
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.tiles[ty][tx]
        return "wall"

    def is_walkable(self, tx, ty):
        return self.get_tile(tx, ty) not in ("wall", "wall_blood", "speaker")


class DialogueBox:
    def __init__(self):
        self.active = False
        self.texts = []
        self.current = 0
        self.char_index = 0
        self.timer = 0
        self.speaker = ""
        self.speaker_color = (200, 200, 200)
        self.callback = None
        self.rect = pygame.Rect(50, SCREEN_H - 214, SCREEN_W - 100, 196)
        self.choices = None
        self.selected_choice = 0
        self.portrait_key = ""
        self.portrait_img = None
        self.default_portrait = None

    def _set_portrait(self, key):
        self.portrait_key = key or ""
        self.portrait_img = portraits.get(key) if key else None

    def set_default_portrait(self, key):
        self.default_portrait = key

    def _wrap_text(self, text, width, max_lines=None):
        lines = []
        for paragraph in text.split("\n"):
            words = paragraph.split(" ")
            cur = ""
            for word in words:
                test = cur + " " + word if cur else word
                if fonts.render_small(test).get_width() > width:
                    lines.append(cur)
                    cur = word
                else:
                    cur = test
            lines.append(cur)
        if max_lines is not None:
            lines = lines[:max_lines]
        return lines

    def start(self, texts, speaker="", color=(200, 200, 200), callback=None, portrait=None):
        self.texts = texts
        self.current = 0
        self.char_index = 0
        self.timer = 0
        self.active = True
        self.speaker = speaker
        self.speaker_color = color
        self.callback = callback
        self.choices = None
        self._set_portrait(portrait or self.default_portrait or speaker)

    def start_choice(self, speaker, question, options, callback, color=(200, 200, 200),
                     portrait=None):
        self.active = True
        self.speaker = speaker
        self.speaker_color = color
        self.texts = [question]
        self.current = 0
        self.char_index = len(question)
        self.choices = options
        self.selected_choice = 0
        self.callback = callback
        self._set_portrait(portrait or self.default_portrait or speaker)

    def update(self):
        if not self.active:
            return
        self.timer += 1
        if self.timer % 2 == 0 and self.choices is None:
            if self.char_index < len(self.texts[self.current]):
                self.char_index += 1

    def handle_input(self, event):
        if not self.active:
            return
        if self.choices:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_choice = max(0, self.selected_choice - 1)
                elif event.key == pygame.K_DOWN:
                    self.selected_choice = min(len(self.choices) - 1, self.selected_choice + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    cb = self.callback
                    sel = self.selected_choice
                    self.active = False
                    self.choices = None
                    if cb:
                        cb(sel)
        else:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.char_index < len(self.texts[self.current]):
                        self.char_index = len(self.texts[self.current])
                    else:
                        self.current += 1
                        self.char_index = 0
                        if self.current >= len(self.texts):
                            self.active = False
                            if self.callback:
                                self.callback(-1)

    def render(self, surface):
        if not self.active:
            return
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        # Portrait (if any) sits above the dialogue box on the left.
        if self.portrait_img:
            px = 60
            py = self.rect.y - self.portrait_img.get_height() - 10
            surface.blit(self.portrait_img, (px, py))
            name = fonts.render_small(self.portrait_key.replace("_", " ").title(), (255, 200, 80))
            surface.blit(name, (px + 8, py + self.portrait_img.get_height() + 2))

        # Box — dark, opaque, warm border for readability.
        box = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        box.fill((10, 6, 8, 245))
        pygame.draw.rect(box, (200, 100, 30), box.get_rect(), 3)
        pygame.draw.rect(box, (255, 190, 90), box.get_rect(), 1)
        surface.blit(box, self.rect.topleft)

        text_x = self.rect.x + 16
        text_width = self.rect.width - 32
        line_h = 18
        body_color = (245, 245, 245)
        accent = (255, 210, 60)

        name_y = self.rect.y + 12
        text_top = name_y + 28 if self.speaker else name_y + 2

        display_text = self.texts[self.current][:self.char_index]
        full_displayed = self.char_index >= len(self.texts[self.current])

        if self.speaker:
            ns = fonts.render(self.speaker, self.speaker_color, big=True)
            surface.blit(ns, (text_x, name_y))

        if self.choices:
            # Reserved choices zone at the bottom; divider above it.
            choice_h = len(self.choices) * 27 + 12
            choices_top = self.rect.bottom - choice_h - 6
            pygame.draw.line(surface, (120, 60, 25), (text_x, choices_top - 5),
                             (self.rect.right - 16, choices_top - 5), 2)

            max_text_bottom = choices_top - 8
            y = text_top
            for line in self._wrap_text(display_text, text_width):
                if y + line_h > max_text_bottom:
                    break
                ts = fonts.render_small(line, body_color)
                surface.blit(ts, (text_x, y))
                y += line_h

            for i, choice in enumerate(self.choices):
                cy = choices_top + 9 + i * 27
                selected = i == self.selected_choice
                label = ("> " if selected else "  ") + choice
                c = accent if selected else (215, 205, 185)
                if selected:
                    cs = fonts.render_small(label, c)
                    pill = pygame.Surface((cs.get_width() + 16, 20), pygame.SRCALPHA)
                    pill.fill((90, 40, 10, 190))
                    pygame.draw.rect(pill, (250, 160, 50), pill.get_rect(), 1)
                    surface.blit(pill, (text_x - 5, cy - 2))
                cs = fonts.render_small(label, c)
                surface.blit(cs, (text_x, cy))
        else:
            y = text_top
            for line in self._wrap_text(display_text, text_width):
                if y + line_h > self.rect.bottom - 12:
                    break
                ts = fonts.render_small(line, body_color)
                surface.blit(ts, (text_x, y))
                y += line_h

            if full_displayed:
                hint = fonts.render_small("[ENTER]...", (200, 160, 80))
                surface.blit(hint, (self.rect.right - hint.get_width() - 16, self.rect.bottom - 26))


class Player:
    def __init__(self):
        self.x = 3 * TILE + TILE // 2
        self.y = 3 * TILE + TILE // 2
        self.speed = 3
        self.hp = 100
        self.max_hp = 100
        self.attack = 15
        self.defense = 5
        self.inventory = []
        self.sanity = 100
        self.facing = "down"
        self.anim_frame = 0
        self.anim_timer = 0
        self.kills = 0
        self.name = "Belligerent Dickhead"

        # Healing mechanics: "Grit" meter + passive regen
        self.grit = 0
        self.grit_max = 100
        self.regen_timer = 0
        self.regen_delay = 120

        # Progression: XP, levels, abilities
        self.level = 1
        self.xp = 0
        self.xp_to_next = 30
        self.skills = []

    def add_xp(self, amount):
        """Gain XP and apply level-ups. Returns (leveled, new_skill_ids)."""
        self.xp += amount
        leveled = False
        new_skills = []
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.max_hp += 8
            self.hp = self.max_hp
            self.attack += 2
            self.defense += 1
            self.sanity = min(100, self.sanity + 10)
            self.xp_to_next = 30 + (self.level - 1) * 20
            for sid, sk in SKILLS.items():
                if sk.get("unlock_level") == self.level and self.unlock_skill(sid):
                    new_skills.append(sid)
            leveled = True
        return leveled, new_skills

    def unlock_skill(self, skill_id):
        if skill_id not in self.skills:
            self.skills.append(skill_id)
            return True
        return False

    def has_skill(self, skill_id):
        return skill_id in self.skills

    def update(self, keys, room):
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -self.speed
            self.facing = "up"
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = self.speed
            self.facing = "down"
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -self.speed
            self.facing = "left"
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = self.speed
            self.facing = "right"

        new_x = self.x + dx
        new_y = self.y + dy
        tx = int(new_x // TILE)
        ty = int(new_y // TILE)

        if room.is_walkable(tx, int(self.y // TILE)):
            self.x = new_x
        if room.is_walkable(int(self.x // TILE), ty):
            self.y = new_y

        self.x = max(TILE + 8, min(self.x, room.width * TILE - TILE - 8))
        self.y = max(TILE + 8, min(self.y, room.height * TILE - TILE - 8))

        if dx != 0 or dy != 0:
            self.anim_timer += 1
            if self.anim_timer > 8:
                self.anim_timer = 0
                self.anim_frame += 1

    def render(self, surface, cam_x=0, cam_y=0):
        sx = self.x - cam_x
        sy = self.y - cam_y
        bob = int(math.sin(pygame.time.get_ticks() * 0.006 + self.anim_frame * 0.8) * 2)
        pygame.draw.ellipse(surface, (12, 8, 8), (sx - 9, sy + 5, 18, 6))
        PixelArt.draw_character(surface, sx, sy + bob, self.facing, self.anim_frame)

    def tile_pos(self):
        return int(self.x // TILE), int(self.y // TILE)

    def add_grit(self, amount):
        self.grit = min(self.grit_max, self.grit + amount)

    def spend_grit(self):
        self.grit = max(0, self.grit - self.grit_max)

    def can_scream(self):
        return self.grit >= self.grit_max

    def scream_heal(self, amount):
        restored = 0
        if self.hp < self.max_hp:
            before = self.hp
            self.hp = min(self.max_hp, self.hp + amount)
            restored = self.hp - before
        return restored

    def passive_regen(self, amount_per_tick):
        if self.hp < self.max_hp:
            self.regen_timer += 1
            if self.regen_timer >= self.regen_delay:
                self.regen_timer = 0
                self.hp = min(self.max_hp, self.hp + amount_per_tick)
        else:
            self.regen_timer = 0
SKILLS = {
    "power_chord": {
        "name": "Power Chord",
        "desc": "A heavy opening riff. 1.6x damage.",
        "cost": 30,
        "cost_type": "grit",
        "mult": 1.6,
        "unlock_level": 2,
        "lines": [
            "You strike a POWER CHORD. The floor cracks.",
            "POWER CHORD! The monitors rattle in their cages.",
            "You rip a POWER CHORD. It vibrates in their bones.",
        ],
    },
    "double_down": {
        "name": "Double Down",
        "desc": "Reroute your sanity into damage. 2.0x damage.",
        "cost": 12,
        "cost_type": "sanity",
        "mult": 2.0,
        "unlock_level": None,
        "lines": [
            "You DOUBLE DOWN. Every doubt becomes a downbeat.",
            "DOUBLE DOWN! You swing twice in the space of one breath.",
            "DOUBLE DOWN! Your grip tightens, your mind spins, the hit lands.",
        ],
    },
    "feedback_howl": {
        "name": "Feedback Howl",
        "desc": "Turn all your rage into one massive note. 2.5x damage.",
        "cost": 55,
        "cost_type": "grit",
        "mult": 2.5,
        "unlock_level": None,
        "lines": [
            "The FEEDBACK HOWL shreds the air itself!",
            "FEEDBACK HOWL! Even the walls start bleeding noise.",
            "FEEDBACK HOWL! It keeps going after the swing ends.",
        ],
    },
}


class CombatSystem:
    ENEMY_NAMES = {
        "zombie": "the Zombie Fan",
        "corpse": "the Reanimated Roadie",
        "shadow": "the Stage Ninja",
        "demon": "the Pit Lord's Enforcer",
        "engineer": "the Sound Engineer",
        "beast": "the Pit Lord himself",
    }

    ENEMY_XP = {
        "zombie": 18,
        "corpse": 14,
        "shadow": 22,
        "demon": 45,
        "engineer": 30,
        "beast": 150,
    }

    ENEMY_BANTER = {
        "zombie": [
            "Zombie Fan: 'I still have your setlist, dude... it's... the only thing... I ever loved...'",
            "Zombie Fan: 'The mosh pit... never ends... down here...'",
            "Zombie Fan: 'I moshed so hard... my soul fell out...'",
        ],
        "corpse": [
            "Reanimated Roadie: 'This gig has gone on... way too long... someone... book another...'",
            "Reanimated Roadie: 'Even roadies die... but the tour... continues...'",
            "Reanimated Roadie: 'I just wanted... to fix the monitors... why... why...'",
        ],
        "shadow": [
            "Stage Ninja: 'Your stage presence... is misplaced. It belongs to me now.'",
            "Stage Ninja: 'In the dark of the wings, I am the only real performer.'",
            "Stage Ninja: 'I'll open for your funeral, Dickhead.'",
        ],
        "demon": [
            "Pit Lord's Enforcer: 'The Beast has evolved the setlist. You're opening for oblivion.'",
            "Pit Lord's Enforcer: 'Your screams will be the encore. On loop. Forever.'",
            "Pit Lord's Enforcer: 'You call that heavy? I'll show you a breakdown.'",
        ],
        "engineer": [
            "Sound Engineer: 'THE MIX IS WRONG. YOUR FACE IS WRONG. EVERYTHING IS WRONG.'",
            "Sound Engineer: 'You hear that feedback? That's my soul. Still ringing.'",
            "Sound Engineer: 'I mixed this room. The acoustics are my religion. Die quietly.'",
        ],
        "beast": [
            "PIT LORD: 'Little singer. You think your noise scares me?'",
            "PIT LORD: 'I have devoured ten thousand openers. You will be the loudest snack yet.'",
            "PIT LORD: 'Your band. Your crowd. Your soul. All booked. All mine.'",
        ],
    }

    PLAYER_RETORTS = [
        "Belligerent Dickhead: 'You should've stayed a one-hit wonder.'",
        "Belligerent Dickhead: 'My dog plays better than you, and he's a corpse too.'",
        "Belligerent Dickhead: 'I've headlined worse crowds than hell.'",
        "Belligerent Dickhead: 'Let me autograph your face. Real close. With my boot.'",
        "Belligerent Dickhead: 'You're all gimmick, no substance. Extra disembowelment for that.'",
        "Belligerent Dickhead: 'This is the shortest opening set you've ever done.'",
    ]

    VICTORY_LINES = {
        "zombie": [
            "That's a review you won't recover from.",
            "Final encore: you. In pieces.",
            "Rest in pieces, groupie.",
            "I just made your last show a total wipeout.",
            "Moshed your soul into the merch table.",
        ],
        "corpse": [
            "Next time, keep the monitors level with the living.",
            "That one's for every roadie who carried my gear.",
            "You done kicked your last kick drum.",
            "Load-out's over, buddy.",
        ],
        "shadow": [
            "Looks like the lights found you after all.",
            "You're the one who's off-stage now. Permanently.",
            "Nope, still the loudest thing here.",
            "I'll mail your cape back. Maybe.",
        ],
        "demon": [
            "Your breakdown was mid. Mine's a knockout.",
            "The Beast should've booked a better opener.",
            "That's how you close a set.",
            "Tell the Beast I want my own merch table.",
        ],
        "engineer": [
            "Check the meters now. Flatlining.",
            "That's one engineer who'll never touch a fader again.",
            "Sound check: complete. No reverb. No exit.",
            "Rest of the board and board of rest.",
        ],
        "beast": [
            "That's the whole gig, Pit Lord. Headlining. Forever.",
            "You booked the wrong band to open.",
            "The noise won. Souls stay. Set's over.",
            "I'll handle the encore. You handle the pit.",
        ],
    }

    GENERIC_VICTORY = [
        "And that's the encore.",
        "Another one for the merch pile.",
        "Sang 'em to death. Literally.",
        "Still sharper than half the bands I've shared a stage with.",
        "I'd say rest easy, but you're basically confetti now.",
    ]

    def __init__(self):
        self.active = False
        self.enemy = None
        self.enemy_hp = 0
        self.enemy_max_hp = 0
        self.player_turn = True
        self.log = []
        self.turn_timer = 0
        self.resolved = False
        self.result = None
        self.options = ["Attack", "Taunt", "Flee"]
        self.taunt_bonus = 0
        self.banter = []
        self.one_liner = ""
        self.banter_done = False
        self.banter_timer = 0
        self.xp_gained = 0
        self.leveled_up = False
        self.skills_gained = []

    def start(self, enemy, player_ref=None):
        self.active = True
        self.enemy = enemy
        self.enemy_hp = enemy.get("hp", 50)
        self.enemy_max_hp = self.enemy_hp
        self.player_turn = True
        self.taunt_bonus = 0
        self.resolved = False
        self.result = None
        self.one_liner = ""
        self.banter_done = False
        self.banter_timer = 0
        self.xp_gained = 0
        self.leveled_up = False
        self.skills_gained = []

        enemy_type = enemy["type"]
        enemy_list = self.ENEMY_BANTER.get(enemy_type, self.ENEMY_BANTER["zombie"])
        enemy_line = random.choice(enemy_list)
        retort = random.choice(self.PLAYER_RETORTS)
        self.log = [enemy_line, retort]

        # Build options from the protagonist's unlocked abilities.
        self.options = ["Attack"]
        if player_ref:
            for sid in player_ref.skills:
                self.options.append(sid)
        self.options += ["Taunt", "Flee"]

        is_boss = bool(enemy.get("boss")) or enemy["type"] == "beast"
        sound.play_ambient("boss" if is_boss else "combat", force=True)

    def _skill_affordable(self, skill_id, player_ref):
        sk = SKILLS.get(skill_id)
        if not sk:
            return True
        if sk["cost_type"] == "grit":
            return player_ref.grit >= sk["cost"]
        return player_ref.sanity >= sk["cost"]

    def player_action(self, action, player_ref):
        if not self.player_turn or self.resolved:
            return

        if action == "Attack":
            dmg = max(1, player_ref.attack + self.taunt_bonus + random.randint(-5, 5))
            self.enemy_hp -= dmg
            player_ref.add_grit(18)
            self.log.append(f"You smash it for {dmg}!")
            sound.play_sfx("hit")
            camera.add_shake(5)
            self.taunt_bonus = 0
            if self.enemy_hp <= 0:
                self._resolve_win(player_ref)
                return
        elif action in SKILLS:
            sk = SKILLS[action]
            if not self._skill_affordable(action, player_ref):
                need = f"{sk['cost']} {sk['cost_type'].upper()}"
                self.log.append(f"Not enough {sk['cost_type'].upper()} ({sk['name']} needs {need}).")
                return
            if sk["cost_type"] == "grit":
                player_ref.grit -= sk["cost"]
            else:
                player_ref.sanity -= sk["cost"]
            dmg = max(1, int((player_ref.attack + self.taunt_bonus + random.randint(-5, 5)) * sk["mult"]))
            self.enemy_hp -= dmg
            player_ref.add_grit(25)
            self.log.append(random.choice(sk["lines"]))
            self.log.append(f"{sk['name']}: {dmg} damage!")
            sound.play_sfx("hit")
            camera.add_shake(8)
            self.taunt_bonus = 0
            if self.enemy_hp <= 0:
                self._resolve_win(player_ref)
                return
        elif action == "Taunt":
            self.taunt_bonus = random.randint(8, 20)
            taunts = [
                "You scream insults about their mother!",
                "You tell them their riff is derivative!",
                "You say their leather pants are fake!",
                "You call them a poser!",
            ]
            self.log.append(random.choice(taunts))
            self.log.append(f"+{self.taunt_bonus} damage next hit!")
        elif action == "Flee":
            if random.random() > 0.4:
                self.log.append("You run away!")
                self.resolved = True
                self.result = "flee"
                sound.stop_combat_music()
                return
            else:
                self.log.append("No escape!")

        self.player_turn = False
        self.turn_timer = 0

    def _resolve_win(self, player_ref):
        player_ref.add_grit(25)
        player_ref.kills += 1
        self.log.append(f"The {self.enemy['type']} goes down!")
        self.xp_gained = self.ENEMY_XP.get(self.enemy["type"], 15)
        self.log.append(f"GAINED {self.xp_gained} XP.")
        self.leveled_up, self.skills_gained = player_ref.add_xp(self.xp_gained)
        self.one_liner = self._pick_win_line(self.enemy["type"])
        self.log.append(self.one_liner)
        self.resolved = True
        self.result = "win"
        sound.stop_combat_music()

    def update(self, player_ref):
        if not self.active or self.resolved:
            return
        if not self.player_turn:
            self.turn_timer += 1
            if self.turn_timer > 30:
                edmg = max(1, random.randint(8, 18))
                player_ref.hp -= edmg
                player_ref.add_grit(12)
                self.log.append(f"The {self.enemy['type']} hits for {edmg}!")
                sound.play_sfx("hurt")
                camera.add_shake(8)
                self.player_turn = True
                if player_ref.hp <= 0:
                    self.resolved = True
                    self.result = "lose"
                    sound.stop_combat_music()

    def _pick_win_line(self, enemy_type):
        pool = self.VICTORY_LINES.get(enemy_type)
        if pool:
            return '"' + random.choice(pool) + '"'
        return '"' + random.choice(self.GENERIC_VICTORY) + '"'

    def render(self, surface, player_ref):
        if not self.active:
            return

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        cx, cy = SCREEN_W // 2, SCREEN_H // 2

        # Enemy portrait (still image substitute) - top right
        ep = portraits.get(self.enemy["type"])
        if ep:
            surface.blit(ep, (SCREEN_W - ep.get_width() - 20, 20))
            ename = fonts.render(f"{self.ENEMY_NAMES.get(self.enemy['type'], 'Enemy')}",
                                 (200, 80, 80), big=True)
            surface.blit(ename, (SCREEN_W - ep.get_width() - 20, 20 + ep.get_height() + 4))

        # Protagonist portrait - top left
        pp = portraits.get("player")
        if pp:
            surface.blit(pp, (20, 20))
            pname = fonts.render(f"{player_ref.name}", (200, 200, 200), big=True)
            surface.blit(pname, (20, 20 + pp.get_height() + 4))

        PixelArt.draw_enemy(surface, cx + 100, cy - 50, self.enemy["type"],
                            frame=pygame.time.get_ticks() // 200, scale=4)

        hp_pct = self.enemy_hp / self.enemy_max_hp
        pygame.draw.rect(surface, (40, 0, 0), (cx + 40, cy + 50, 200, 16))
        pygame.draw.rect(surface, (200, 0, 0), (cx + 40, cy + 50, int(200 * hp_pct), 16))
        ehp = fonts.render_small(f"{self.enemy_hp}/{self.enemy_max_hp}", (255, 255, 255))
        surface.blit(ehp, (cx + 120, cy + 50))

        php_pct = player_ref.hp / player_ref.max_hp
        pygame.draw.rect(surface, (0, 40, 0), (50, SCREEN_H - 100, 200, 16))
        pygame.draw.rect(surface, (0, 200, 0), (50, SCREEN_H - 100, int(200 * php_pct), 16))
        php = fonts.render_small(f"HP: {player_ref.hp}/{player_ref.max_hp}", (255, 255, 255))
        surface.blit(php, (50, SCREEN_H - 120))

        log_y = cy - 80
        for i, msg in enumerate(self.log[-5:]):
            lt = fonts.render_small(msg, (180, 180, 180))
            surface.blit(lt, (50, log_y + i * 18))

        if self.player_turn and not self.resolved:
            n = len(self.options)
            top = SCREEN_H - 24 - n * 22
            res = fonts.render_small(f"GRIT {int(player_ref.grit)}/100   SANITY {player_ref.sanity}",
                                     (210, 205, 190))
            surface.blit(res, (SCREEN_W - 220, top - 20))
            for i, opt in enumerate(self.options):
                if opt == "Attack":
                    c = (255, 200, 50)
                    label = "Attack"
                elif opt in SKILLS:
                    sk = SKILLS[opt]
                    unit = "GRIT" if sk["cost_type"] == "grit" else "SAN"
                    affordable = self._skill_affordable(opt, player_ref)
                    label = f"{sk['name']} [{sk['cost']} {unit}]"
                    if not affordable:
                        label = f"{sk['name']} [x{sk['cost']} {unit}]"
                        c = (130, 120, 110)
                    else:
                        c = (170, 225, 255) if sk["cost_type"] == "sanity" else (255, 210, 100)
                elif opt == "Taunt":
                    c = (180, 180, 180)
                    label = "Taunt"
                else:
                    c = (180, 180, 180)
                    label = "Flee"
                ot = fonts.render(f"[{i + 1}] {label}", c)
                surface.blit(ot, (SCREEN_W - 220, top + i * 22))

        if self.resolved:
            text = "VICTORY!" if self.result == "win" else "ESCAPED!" if self.result == "flee" else "KNOCKED OUT..."
            c = (255, 50, 50) if self.result == "lose" else (200, 200, 50)
            rt = fonts.render(text, c, big=True)
            surface.blit(rt, (cx - rt.get_width() // 2, cy + 100))
            if self.result == "win" and self.one_liner:
                ol = fonts.render(self.one_liner, (255, 220, 120))
                surface.blit(ol, (cx - ol.get_width() // 2, cy + 135))
                hint = fonts.render_small("Press ENTER", (100, 100, 100))
                surface.blit(hint, (cx - hint.get_width() // 2, cy + 165))
            else:
                hint = fonts.render_small("Press ENTER", (100, 100, 100))
                surface.blit(hint, (cx - hint.get_width() // 2, cy + 140))


class CutsceneSystem:
    def __init__(self):
        self.active = False
        self.lines = []
        self.current = 0
        self.char_index = 0
        self.timer = 0
        self.bg_color = (5, 0, 0)
        self.callback = None
        self.portrait_img = None
        self.portrait_label = ""

    def start(self, lines, bg_color=(5, 0, 0), callback=None, portrait=None, label=""):
        self.active = True
        self.lines = lines
        self.current = 0
        self.char_index = 0
        self.timer = 0
        self.bg_color = bg_color
        self.callback = callback
        self.portrait_img = portraits.get(portrait) if portrait else None
        self.portrait_label = label

    def update(self):
        if not self.active:
            return
        self.timer += 1
        if self.timer % 2 == 0:
            if self.char_index < len(self.lines[self.current]):
                self.char_index += 1

    def handle_input(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.char_index < len(self.lines[self.current]):
                    self.char_index = len(self.lines[self.current])
                else:
                    self.current += 1
                    self.char_index = 0
                    if self.current >= len(self.lines):
                        self.active = False
                        if self.callback:
                            self.callback()

    def render(self, surface):
        if not self.active:
            return
        surface.fill(self.bg_color)
        text_y = SCREEN_H // 2 - 20
        if self.portrait_img:
            px = SCREEN_W // 2 - self.portrait_img.get_width() // 2
            py = 40
            surface.blit(self.portrait_img, (px, py))
            if self.portrait_label:
                lb = fonts.render(self.portrait_label, (200, 120, 50), big=True)
                surface.blit(lb, (SCREEN_W // 2 - lb.get_width() // 2, py + self.portrait_img.get_height() + 4))
            text_y = py + self.portrait_img.get_height() + 60
        display = self.lines[self.current][:self.char_index]
        ts = fonts.render(display, (200, 200, 200), big=True)
        surface.blit(ts, (SCREEN_W // 2 - ts.get_width() // 2, text_y))
        if self.char_index >= len(self.lines[self.current]):
            hint = fonts.render_small("[ENTER]", (100, 100, 100))
            surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, text_y + 50))


class Game:
    def __init__(self):
        self.state = GameState.MENU
        self.current_room = None
        self.room_map = {}
        self.embers = None
        self.transition_alpha = 0
        self.transitioning = False
        self.transition_target = None
        self.transition_callback = None
        self.menu_select = 0
        self.vignette = self._make_vignette()
        self.story_flags = {}
        self.hd_overlay = None
        self.hd_timer = 0
        self.player = Player()
        self.dialogue = DialogueBox()
        self.combat = battle_bridge.BattleBridge(screen)
        self.cutscene = CutsceneSystem()
        self.track_announcement = ""
        self.track_announcement_timer = 0
        self.help_banner = ""
        self.help_banner_timer = 0
        self.objective_banner = ""
        self.objective_banner_timer = 0
        self.objective_banner_portrait = None

    def _make_vignette(self):
        vig = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(80):
            alpha = int(255 * (i / 80) ** 3)
            pygame.draw.rect(vig, (0, 0, 0, alpha),
                             (i, i, SCREEN_W - 2 * i, SCREEN_H - 2 * i), 1)
        return vig

    def _make_tiles(self, w, h, border="wall", fill="floor"):
        tiles = [[fill] * w for _ in range(h)]
        for x in range(w):
            tiles[0][x] = border
            tiles[h - 1][x] = border
        for y in range(h):
            tiles[y][0] = border
            tiles[y][w - 1] = border
        return tiles

    def setup_rooms(self):
        w, h = 20, 15

        # Room 1: The Stage
        stage = self._make_tiles(w, h)
        for x in range(6, 14):
            stage[3][x] = "stage"
        for x in range(5, 15):
            stage[4][x] = "stage"
        stage[3][4] = "speaker"
        stage[3][15] = "speaker"
        stage[8][10] = "door"
        for x in range(2, 5):
            for yy in range(7, 10):
                stage[yy][x] = "blood_floor"

        room_stage = Room("The Stage of Sin", w, h, stage,
                          ambient_color=(25, 10, 10),
                          objective="Get your bearings. Grab what's on the floor, talk to the Roadie, then find the exit door.",
                         objective_portrait="roadie")
        room_stage.items = [
            {"x": 2, "y": 8, "type": "beer", "active": True, "interact": "beer"},
            {"x": 17, "y": 12, "type": "microphone", "active": True, "interact": "mic"},
            {"x": 14, "y": 6, "type": "key", "active": True, "interact": "crypt_key"},
        ]
        room_stage.enemies = [
            {"x": 12, "y": 10, "type": "zombie", "active": True, "hp": 40,
             "defense": 3, "interact": "zombie_fan"},
        ]
        room_stage.npcs = [
            {"x": 8, "y": 5, "color": (240, 130, 90), "active": True,
             "name": "Roadie", "interact": "roadie"},
        ]
        room_stage.doors = [{"x": 10, "y": 8, "target": "Backstage Gore", "spawn_x": 2, "spawn_y": 7}]

        # Room 2: Backstage
        back = self._make_tiles(w, h, "wall_blood")
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                back[y][x] = "floor" if random.random() > 0.2 else "blood_floor"
        back[7][1] = "door"
        back[7][18] = "door"
        back[12][10] = "door"

        room_back = Room("Backstage Gore", w, h, back, ambient_color=(15, 8, 8),
                         objective="Search the Backstage. Grab the bottle and the drink. That rusted door to the south needs a key.",
                         objective_portrait="broken_bottle")
        room_back.enemies = [
            {"x": 10, "y": 5, "type": "corpse", "active": True, "hp": 35,
             "defense": 2, "interact": "corpse_reanimated"},
            {"x": 14, "y": 10, "type": "shadow", "active": True, "hp": 55,
             "defense": 6, "interact": "stage_ninja"},
        ]
        room_back.items = [
            {"x": 5, "y": 3, "type": "weapon", "active": True, "interact": "broken_bottle"},
            {"x": 16, "y": 12, "type": "health", "active": True, "interact": "energy_drink"},
            {"x": 8, "y": 8, "type": "blood", "active": True, "interact": "blood_puddle"},
        ]
        room_back.doors = [
            {"x": 1, "y": 7, "target": "The Stage of Sin", "spawn_x": 9, "spawn_y": 8},
            {"x": 18, "y": 7, "target": "The Merch Table of Madness", "spawn_x": 2, "spawn_y": 7},
            {"x": 10, "y": 12, "target": "The Green Room of Vile", "requires_item": "crypt_key",
             "spawn_x": 8, "spawn_y": 7,
             "locked_msg": "A heavy rusted door. It's engraved with a keyhole shaped like a certain DO-NOT-USE key..."},
        ]

        # Room 3: Merch Table
        merch = self._make_tiles(w, h)
        for x in range(5, 15):
            merch[4][x] = "speaker"
        for x in range(3, 17):
            merch[10][x] = "stage"
        merch[7][1] = "door"
        merch[7][18] = "door"

        room_merch = Room("The Merch Table of Madness", w, h, merch, ambient_color=(20, 15, 20),
                          objective="Talk to the vendor. Stock up. The Mosh Pit awaits beyond the east door.",
                         objective_portrait="sketchy_vendor")
        room_merch.enemies = [
            {"x": 10, "y": 7, "type": "demon", "active": True, "hp": 70,
             "defense": 8, "interact": "merch_demon"},
        ]
        room_merch.npcs = [
            {"x": 3, "y": 7, "color": (150, 50, 150), "active": True,
             "name": "Sketchy Vendor", "interact": "vendor"},
        ]
        room_merch.items = [
            {"x": 8, "y": 5, "type": "beer", "active": True, "interact": "mysterious_lager"},
            {"x": 15, "y": 12, "type": "health", "active": True, "interact": "merch_bloody_rag"},
        ]
        room_merch.doors = [
            {"x": 1, "y": 7, "target": "Backstage Gore", "spawn_x": 17, "spawn_y": 7},
            {"x": 18, "y": 7, "target": "The Mosh Pit of Souls", "spawn_x": 2, "spawn_y": 7},
        ]

        # Room 4: Mosh Pit (Boss)
        pit = self._make_tiles(w, h, "wall_blood")
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                pit[y][x] = "blood_floor" if random.random() > 0.15 else "floor"
        for x in range(8, 13):
            for yy in range(5, 10):
                pit[yy][x] = "blood_floor"
        pit[7][1] = "door"
        pit[7][12] = "door"
        pit[1][7] = "door"

        room_pit = Room("The Mosh Pit of Souls", w, h, pit, ambient_color=(30, 0, 0),
                        objective="Slay the Pit Lord's Enforcer to open the great gate to the east.",
                        objective_portrait="demon")
        room_pit.enemies = [
            {"x": 10, "y": 7, "type": "demon", "active": True, "hp": 120,
             "defense": 10, "interact": "pit_lord", "boss": True},
            {"x": 6, "y": 4, "type": "zombie", "active": True, "hp": 45,
             "defense": 3, "interact": "pit_zombie"},
            {"x": 14, "y": 10, "type": "zombie", "active": True, "hp": 45,
             "defense": 3, "interact": "pit_zombie2"},
        ]
        room_pit.items = [
            {"x": 12, "y": 3, "type": "weapon", "active": True, "interact": "guitaraxe"},
            {"x": 4, "y": 12, "type": "health", "active": True, "interact": "pit_mystery_vial"},
            {"x": 8, "y": 12, "type": "tome", "active": True, "interact": "tome_feedback_howl"},
        ]
        room_pit.doors = [
            {"x": 1, "y": 7, "target": "The Merch Table of Madness", "spawn_x": 17, "spawn_y": 7},
            {"x": 12, "y": 7, "target": "The Pit Lord's Chamber", "requires_flag": "pit_lord_defeated",
             "spawn_x": 8, "spawn_y": 7,
             "locked_msg": "A colossal iron gate. It's fused shut by demonic chains. Only the Enforcer's death will break them."},
            {"x": 7, "y": 1, "target": "The Sound Booth of Despair", "spawn_x": 7, "spawn_y": 12},
        ]

        # Room 5: The Green Room of Vile (secret/side room)
        green = self._make_tiles(w, h, "wall_blood")
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                green[y][x] = "floor" if random.random() > 0.4 else "blood_floor"
        green[7][1] = "door"
        green[7][18] = "door"

        room_green = Room("The Green Room of Vile", w, h, green, ambient_color=(10, 25, 10),
                          objective="Sneak the VIP lounge. Talk to the Last Roadie. Loot the green room.",
                          objective_portrait="last_roadie")
        room_green.enemies = [
            {"x": 10, "y": 8, "type": "shadow", "active": True, "hp": 60,
             "defense": 7, "interact": "vip_ninja"},
            {"x": 4, "y": 5, "type": "corpse", "active": True, "hp": 40,
             "defense": 3, "interact": "vip_corpse"},
        ]
        room_green.items = [
            {"x": 15, "y": 4, "type": "weapon", "active": True, "interact": "vip_broken_lamp"},
            {"x": 12, "y": 12, "type": "health", "active": True, "interact": "vip_energy_drink"},
            {"x": 5, "y": 12, "type": "blood", "active": True, "interact": "vip_blood"},
        ]
        room_green.npcs = [
            {"x": 8, "y": 7, "color": (50, 150, 50), "active": True,
             "name": "Last Roadie", "interact": "last_roadie"},
        ]
        room_green.doors = [
            {"x": 1, "y": 7, "target": "Backstage Gore", "spawn_x": 9, "spawn_y": 12},
            {"x": 18, "y": 7, "target": "The Stage of Sin", "spawn_x": 9, "spawn_y": 8},
        ]

        # Room 6: The Pit Lord's Chamber (final boss)
        chamber = self._make_tiles(w, h, "wall_blood")
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                chamber[y][x] = "floor" if random.random() > 0.3 else "blood_floor"
        for x in range(7, 13):
            for yy in range(4, 10):
                chamber[yy][x] = "blood_floor"
        chamber[7][1] = "door"
        chamber[7][12] = "door"

        room_chamber = Room("The Pit Lord's Chamber", w, h, chamber, ambient_color=(40, 0, 0),
                            objective="The Pit Lord. End the set and escape. He drops no mercy.",
                            objective_portrait="beast")
        room_chamber.enemies = [
            {"x": 10, "y": 7, "type": "beast", "active": True, "hp": 200,
             "defense": 14, "interact": "the_beast", "boss": True},
        ]
        room_chamber.items = [
            {"x": 3, "y": 12, "type": "health", "active": True, "interact": "chamber_vial"},
        ]
        room_chamber.doors = [
            {"x": 1, "y": 7, "target": "The Mosh Pit of Souls", "spawn_x": 15, "spawn_y": 7},
        ]

        # Room 7: The Sound Booth of Despair (side room off Mosh Pit)
        booth = self._make_tiles(w, h, "wall_blood")
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                booth[y][x] = "floor" if random.random() > 0.25 else "blood_floor"
        booth[13][7] = "door"
        booth[5][18] = "door"

        room_booth = Room("The Sound Booth of Despair", w, h, booth, ambient_color=(15, 15, 40),
                          objective="The sound booth. The engineer controls everything. Grab the fader. Grab the tomes. Break the mix.",
                          objective_portrait="engineer")
        room_booth.enemies = [
            {"x": 10, "y": 7, "type": "engineer", "active": True, "hp": 70,
             "defense": 7, "interact": "sound_engineer"},
        ]
        room_booth.items = [
            {"x": 8, "y": 3, "type": "tome", "active": True, "interact": "tome_double_down"},
            {"x": 14, "y": 8, "type": "key", "active": True, "interact": "booth_earplugs"},
            {"x": 4, "y": 11, "type": "weapon", "active": True, "interact": "mixer_fader"},
        ]
        room_booth.doors = [
            {"x": 7, "y": 13, "target": "The Mosh Pit of Souls", "spawn_x": 7, "spawn_y": 2},
            {"x": 18, "y": 5, "target": "Backstage Gore", "spawn_x": 17, "spawn_y": 7},
        ]

        self.room_map = {
            "The Stage of Sin": room_stage,
            "Backstage Gore": room_back,
            "The Merch Table of Madness": room_merch,
            "The Mosh Pit of Souls": room_pit,
            "The Green Room of Vile": room_green,
            "The Pit Lord's Chamber": room_chamber,
            "The Sound Booth of Despair": room_booth,
        }
        self.current_room = room_stage
        self.generate_asset_manifest()

    def transition_to(self, room_name, spawn_x, spawn_y, callback=None):
        self.transitioning = True
        self.transition_target = (room_name, spawn_x, spawn_y)
        self.transition_callback = callback

    def announce_track(self, name):
        self.track_announcement = f"Now Playing: {name}"
        self.track_announcement_timer = 120

    # --- Tutorial / onboarding helpers ---

    def show_help(self, text, frames=240):
        self.help_banner = text
        self.help_banner_timer = frames

    def show_level_up(self):
        sound.jingle("levelup")
        parts = [f"LEVEL UP! You are now Level {self.player.level}.",
                 "Max HP +8, ATK +2, DEF +1. Fully healed!"]
        if self.combat.skills_gained:
            names = ", ".join(SKILLS[s]["name"] for s in self.combat.skills_gained)
            parts.append(f"New ability: {names}!")
            self.tutorial_once("tut_skills",
                               "TIP: New abilities unlock as your band levels up in battle. Select a band member and use the panel buttons.",
                               frames=300)
        self.objective_banner = "  ".join(parts)
        self.objective_banner_timer = 420
        self.objective_banner_portrait = portraits.get("player")

    def tutorial_once(self, flag, text, frames=240):
        if not self.story_flags.get(flag, False):
            self.story_flags[flag] = True
            self.show_help(text, frames)

    def tutorial_objective(self):
        if self.current_room:
            return self.current_room.objective
        return ""

    def handle_tutorial_signals(self):
        p = self.player
        if not self.story_flags.get("tut_fullscreen", False):
            # already in game; teach F11 subtly once
            pass
        if p.can_scream() and not self.story_flags.get("tut_scream", False):
            self.tutorial_once("tut_scream",
                               "TIP: GRIT is FULL! Press F to SCREAM and heal 40 HP (costs 20 sanity).")
        if p.sanity < 30 and not self.story_flags.get("tut_sanity", False):
            self.tutorial_once("tut_sanity",
                               "TIP: Your sanity is dropping. Low sanity makes the world flicker. Screaming costs sanity.")
        if not self.story_flags.get("tut_mthud", False) and self.player.kills >= 1:
            self.tutorial_once("tut_mthud",
                               "TIP: Grunt. When you defeat enemies your GRIT fills faster. Save your Scream for when it matters.")

    def tutorial_combat_start(self):
        self.tutorial_once("tut_combat",
                           "FIGHT! 1=Attack 2=Taunt (+damage next hit) 3=Flee. Take the pit by storm.",
                           frames=360)

    def show_room_objective(self):
        room = self.current_room
        if not room:
            return
        if room.objective and not room.discovered:
            room.discovered = True
            self.objective_banner = room.objective
            self.objective_banner_timer = 300
            self.objective_banner_portrait = portraits.get(room.objective_portrait) if room.objective_portrait else None

    def start_game(self):
        self.player = Player()
        self.story_flags = {}
        self.setup_rooms()
        self.state = GameState.CUTSCENE
        sound.play_ambient("intro", force=True)
        self.cutscene.start([
            "The gig was going great.",
            "300 sweaty bodies screaming our name.",
            "Then the floor opened up.",
            "Now I'm here. Wherever here is.",
            "The crowd is still screaming.",
            "But they're not screaming our name anymore.",
            "They're screaming for help.",
            "Time to finish the set.",
        ], bg_color=(5, 0, 0), callback=self.after_intro,
            portrait="player", label="BELLIGrant DICKHEAD")

    def after_intro(self):
        self.state = GameState.PLAYING
        self._sync_room_music()
        self.show_room_objective()
        self.tutorial_once("tut_move",
                           "TO MOVE: WASD or arrow keys. Walk up to things and press SPACE/ENTER to interact.",
                           frames=360)

    def _sync_room_music(self):
        if self.current_room:
            slot = SoundManager.ROOM_SLOT.get(self.current_room.name)
            if slot:
                sound.play_ambient(slot, force=True)

    def generate_asset_manifest(self, path=None):
        path = path or os.path.join(ASSETS, "ASSET_MANIFEST.md")
        lines = [
            "# T3MP3ST - Asset Manifest",
            "",
            "Auto-generated by the game every time you start or load a game. You don't edit",
            "this file - drop your own art and music into the folders below using the exact",
            "names shown and they replace the procedurally generated placeholders automatically.",
            "",
            "Legend: PLACEHOLDER = generated pixel-art by the game | CUSTOM = your file was found",
            "",
        ]

        lines += ["## Portraits & Mugshots", "",
                  "Folder: `assets/portraits/`  -  File: `<key>.png` (recommended 160x160).",
                  "",
                  "| Key | Status | Used as |", "|---|---|---|"]
        rows = {}
        rows["player"] = ("The protagonist (Belligerent Dickhead)", "menu, cutscenes, HUD banners")
        for room in self.room_map.values():
            for npc in room.npcs:
                key = npc["name"].lower().replace(" ", "_")
                where = f"NPC '{npc['name']}' - {room.name}"
                rows.setdefault(key, (npc["name"], where))
            for e in room.enemies:
                key = e["type"].lower().replace(" ", "_")
                name = CombatSystem.ENEMY_NAMES.get(e["type"], e["type"].title())
                if e.get("boss"):
                    name += " (Boss)"
                where = f"Enemy {name} - {room.name}"
                rows.setdefault(key, (name, where))
            for it in room.items:
                ix = it.get("interact", "")
                key = str(ix).lower().replace(" ", "_")
                if not key:
                    continue
                label = ITEM_LABELS.get(ix, TYPE_LABELS.get(it.get("type"), ix.title()))
                where = f"Item {label} - {room.name}"
                rows.setdefault(key, (label, where))
        for key, (label, where) in sorted(rows.items()):
            status = "CUSTOM" if os.path.exists(os.path.join(PORTRAITS_DIR, key + ".png")) else "PLACEHOLDER"
            lines.append(f"| {key} | {status} | {where} |")

        lines += ["", "## Music - key moments", "",
                  "Folder: `assets/music/`.  File: `<slot>.mp3` (or `.ogg` / `.wav`).",
                  "Numbered variants work too: `01-stage.mp3` is the same slot as `stage.mp3`.",
                  "Slots with no file fall back to procedural audio (menu/combat) or silence.",
                  "",
                  "| Slot | File | Plays when | File status |", "|---|---|---|---|"]
        moment = {
            "menu": "Main menu",
            "intro": "Opening cutscene",
            "stage": "The Stage of Sin",
            "backstage": "Backstage Gore",
            "merch": "The Merch Table of Madness",
            "pit": "The Mosh Pit of Souls",
            "greenroom": "The Green Room of Vile",
            "booth": "The Sound Booth of Despair",
            "chamber": "The Pit Lord's Chamber",
            "combat": "Any normal fight",
            "boss": "Pit Lord's Enforcer or the Beast (boss fight)",
            "levelup": "LEVEL UP banner (one-shot sting)",
            "discovery": "Unlocking a new ability tome (one-shot sting)",
            "victory": "Beast defeated (one-shot sting)",
            "ending": "Ending cutscene",
            "credits": "Credits roll",
        }
        for slot in SoundManager.MUSIC_SLOTS:
            file_status = "found" if slot in sound.slots else "missing"
            lines.append(f"| {slot} | {slot}.mp3 | {moment.get(slot, slot)} | {file_status} |")

        lines += ["",
                  "_This file regenerates on every launch; your artwork and music files are never touched._",
                  ""]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass

    def start_ending(self):
        self.state = GameState.CUTSCENE
        sound.play_ambient("ending", force=True)
        self.cutscene.start([
            "The Pit Lord collapses into the pit he came from.",
            "The lights come up. The PA crackles to life.",
            "Somewhere above, the trapdoor grinds open.",
            "You climb back onto the stage... and it feels real again.",
            "The crowd is gone. The blood is gone.",
            "Your guitar is still in tune.",
            "You step up to the mic and scream the last verse of the set.",
            "Somewhere in the void below, a demon claps politely.",
            "THE END",
            "...FOR NOW",
        ], bg_color=(0, 5, 0), callback=self.after_ending)

    def after_ending(self):
        self.state = GameState.CREDITS
        sound.play_ambient("credits", force=True)

    def handle_menu_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.menu_select = (self.menu_select - 1) % 4
            elif event.key == pygame.K_DOWN:
                self.menu_select = (self.menu_select + 1) % 4
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.menu_select in (0, 1):
                    sound.stop_music()
                if self.menu_select == 0:
                    self.start_game()
                elif self.menu_select == 1:
                    self.load_game()
                    self._sync_room_music()
                elif self.menu_select == 2:
                    self.state = GameState.CREDITS
                    sound.play_ambient("credits", force=True)
                elif self.menu_select == 3:
                    pygame.quit()
                    sys.exit()

    def handle_playing_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                sound.toggle_mute()
            elif event.key == pygame.K_F11:
                toggle_fullscreen()
                self.tutorial_once("tut_fullscreen",
                                   "F11 toggles fullscreen. F11 again to go back to windowed.")
            elif event.key == pygame.K_i:
                self.tutorial_once("tut_inventory",
                                   "I opens your inventory. Press I or ESC to close it.")
                self.state = GameState.INVENTORY
            elif event.key == pygame.K_F5:
                self.save_game()
            elif event.key == pygame.K_f:
                self.use_scream()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.interact_forward()

    def use_scream(self):
        if not self.player.can_scream():
            self.dialogue.start(["Your throat isn't ready. Keep fighting to build GRIT.",
                                 "Scream fills when you land or take hits."],
                                "Belligerent Dickhead", (240, 130, 90))
            return
        self.player.spend_grit()
        restored = self.player.scream_heal(40)
        self.player.sanity = max(0, self.player.sanity - 20)
        if restored > 0:
            sound.play_sfx("heal")
            self.dialogue.start([f"You SCREAM the pain out of your body!",
                                 f"+{restored} HP. Your chords are wrecked... SANITY -20"],
                                "Belligerent Dickhead", (240, 130, 90))
        else:
            self.dialogue.start(["You SCREAM, but you're already unharmed.",
                                 "Waste of a good growl. SANITY -20"],
                                "Belligerent Dickhead", (240, 130, 90))

    def nearest_interactable(self):
        RANGE = 5
        tx, ty = self.player.tile_pos()
        candidates = []
        for item in self.current_room.items:
            if item.get("active"):
                d = abs(tx - item["x"]) + abs(ty - item["y"])
                if d <= RANGE:
                    candidates.append((d, item, "item"))
        for npc in self.current_room.npcs:
            if npc.get("active"):
                d = abs(tx - npc["x"]) + abs(ty - npc["y"])
                if d <= RANGE:
                    candidates.append((d, npc, "npc"))
        for enemy in self.current_room.enemies:
            if enemy.get("active"):
                d = abs(tx - enemy["x"]) + abs(ty - enemy["y"])
                if d <= RANGE:
                    candidates.append((d, enemy, "enemy"))
        for door in self.current_room.doors:
            d = abs(tx - door["x"]) + abs(ty - door["y"])
            if d <= RANGE:
                candidates.append((d, door, "door"))
        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        return candidates[0]

    def get_interact_prompt(self):
        found = self.nearest_interactable()
        if not found:
            return None
        d, target, kind = found
        if kind == "item":
            ix = target.get("interact", "")
            label = ITEM_LABELS.get(ix, TYPE_LABELS.get(target["type"], "an object"))
            return f"[SPACE] Take {label}"
        elif kind == "npc":
            return f"[SPACE] Talk to {target['name']}"
        elif kind == "enemy":
            return f"[SPACE] Fight the {target['type']}"
        elif kind == "door":
            if self.door_locked_reason(target):
                return f"[SPACE] Locked gate ({target['target']})"
            return f"[SPACE] Go through the door"
        return None

    def interact_forward(self):
        found = self.nearest_interactable()
        if not found:
            return
        _, target, kind = found

        if kind == "item":
            self.interact_item(target)
            self.tutorial_once("tut_interact",
                               "You grabbed it! Interact by pressing SPACE when a prompt shows at the bottom.",
                               frames=240)
        elif kind == "npc":
            self.interact_npc(target)
            self.tutorial_once("tut_npc",
                               "You talked. NPCs give lore, loot, or choices. Pick with UP/DOWN and SPACE.",
                               frames=240)
        elif kind == "enemy":
            self.tutorial_combat_start()
            self.combat.start(target, self.player)
        elif kind == "door":
            locked_reason = self.door_locked_reason(target)
            if locked_reason:
                self.dialogue.start([locked_reason], "Belligerent Dickhead", (240, 130, 90))
                return
            dest = target["target"]
            if dest in self.room_map:
                sound.play_sfx("door")
                self.transition_to(dest, target.get("spawn_x", 2), target.get("spawn_y", 2))

    def door_is_unlocked(self, door):
        if door.get("requires_flag") and not self.story_flags.get(door["requires_flag"]):
            return False
        if door.get("requires_item") and door["requires_item"] not in self.player.inventory:
            return False
        return True

    def door_locked_reason(self, door):
        if door.get("requires_flag") and not self.story_flags.get(door["requires_flag"]):
            if door.get("locked_msg"):
                return door["locked_msg"]
            return "A heavy gate. It will only open after the Pit Lord's Enforcer is defeated."
        if door.get("requires_item") and door["requires_item"] not in self.player.inventory:
            if door.get("locked_msg"):
                return door["locked_msg"]
            return "Locked. It needs a key. A specific, oddly-labeled key."
        return None

    def handle_combat_input(self, event):
        if event.type == pygame.KEYDOWN:
            if self.combat.resolved:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._finish_combat()
                return
            if getattr(self.combat, "is_bridge", False):
                return
            if self.combat.player_turn:
                keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                        pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]
                for i, key in enumerate(keys):
                    if event.key == key and i < len(self.combat.options):
                        self.combat.player_action(self.combat.options[i], self.player)
                        break
        elif getattr(self.combat, "is_bridge", False) and not self.combat.resolved:
            self.combat.handle_event(event)

    def _finish_combat(self):
        self.combat.active = False
        if self.combat.result == "lose":
            self.state = GameState.GAME_OVER
            return
        if self.combat.result != "win":
            self.state = GameState.PLAYING
            self._sync_room_music()
            return
        e = self.combat.enemy
        if e and e.get("interact") == "pit_lord":
            self.story_flags["pit_lord_defeated"] = True
            self.show_help("The Enforcer is down. The great gate to the Pit Lord's Chamber has opened!",
                           frames=300)
        if e and e.get("interact") == "the_beast":
            sound.jingle("victory")
            self.state = GameState.PLAYING
            self.start_ending()
            return
        if self.combat.leveled_up:
            self.show_level_up()
        self.state = GameState.PLAYING
        self._sync_room_music()

    def interact_item(self, item):
        ix = item.get("interact", "")
        self.dialogue.set_default_portrait(ix)

        if ix == "beer":
            self.player.hp = min(self.player.max_hp, self.player.hp + 15)
            self.player.sanity = max(0, self.player.sanity - 5)
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "You crack open a warm beer. Tastes like backstage.",
                "It doesn't heal your wounds. But it numbs everything else.",
                "HP +15, SANITY -5"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "mic":
            self.player.inventory.append("mic")
            self.player.attack += 3
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "You grab the mic. It's heavy. Real metal.",
                "The last singer's fingerprints are still on it.",
                "His fingerprints are also on the walls. Separately.",
                "ATTACK +3"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "crypt_key":
            self.player.inventory.append("crypt_key")
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "A key with a tag that says 'DO NOT USE'",
                "Naturally, you pocket it immediately.",
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "broken_bottle":
            self.player.inventory.append("broken_bottle")
            self.player.attack += 8
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "A broken bottle. The preferred weapon of every",
                "punk show you've ever played.",
                "ATTACK +8"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "energy_drink":
            self.player.hp = min(self.player.max_hp, self.player.hp + 25)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "Some kind of energy drink. The label just says 'PAIN'.",
                "You drink it anyway. It tastes like regret and taurine.",
                "HP +25"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "blood_puddle":
            self.dialogue.start([
                "A puddle of blood. You're not sure whose.",
                "At a metal show, it could be anyone's.",
                "You dip your fingers in it. Feels... warm.",
                "You write 'BD' on the wall. Branding."
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "mysterious_lager":
            self.player.hp = min(self.player.max_hp, self.player.hp + 10)
            self.player.attack += 5
            self.player.sanity -= 10
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "The label is in a language you don't recognize.",
                "It tastes like lightning and poor decisions.",
                "HP +10, ATTACK +5, SANITY -10"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "merch_bloody_rag":
            self.player.hp = min(self.player.max_hp, self.player.hp + 20)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "It's a rag. It's bloody. You use it as a bandage.",
                "Hygiene left the building several lifetimes ago.",
                "HP +20"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "guitaraxe":
            self.player.inventory.append("guitaraxe")
            self.player.attack += 15
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "A guitar shaped like an axe. Because of course it is.",
                "It's tuned to Drop Z. The strings hum with malice.",
                "This is the most metal thing you've ever held.",
                "ATTACK +15"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "mixer_fader":
            self.player.inventory.append("mixer_fader")
            self.player.attack += 12
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "The master fader from the sound board. It's been ripped clean off.",
                "Heavy steel, sharp edge, and a label that reads 'MASTER'.",
                "You swing it once. The room feedback peaks. Perfect.",
                "ATTACK +12"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "pit_mystery_vial":
            self.player.hp = self.player.max_hp
            self.player.sanity = max(0, self.player.sanity - 20)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "You don't know what this is. You drink it anyway.",
                "Your wounds close. Your vision goes red. Then purple.",
                "Everything tastes like copper. You feel... complete.",
                "FULL HP RESTORED, SANITY -20"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "vip_broken_lamp":
            self.player.inventory.append("vip_lamp")
            self.player.attack += 10
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "A stage lamp cracked off its rig.",
                "Glass, tungsten, and the souls of a thousand burned-out bulbs.",
                "You swing it once. The hum it makes sounds like feedback.",
                "ATTACK +10"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "vip_energy_drink":
            self.player.hp = min(self.player.max_hp, self.player.hp + 30)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "A green-room energy drink. It's unlabeled, duct-taped shut.",
                "The VIP rider is VOMIT, and somebody honored it literally.",
                "Whatever was left in the can tastes like the encore.",
                "HP +30"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "vip_blood":
            self.player.sanity = max(0, self.player.sanity - 8)
            self.dialogue.start([
                "A slick of blood on the green-room couch.",
                "Someone bled here. Someone famous, probably.",
                "You leave a handprint on the wall and keep going.",
                "SANITY -8"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "chamber_vial":
            self.player.hp = self.player.max_hp
            self.player.sanity = max(0, self.player.sanity + 15)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "A vial of Pit Lord blood. It glows faintly crimson.",
                "You down it. It tastes like a headline slot.",
                "Your mind clears. Your body screams 'MORE'.",
                "FULL HP RESTORED, SANITY +15"
            ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "tome_power_chord":
            item["active"] = False
            sound.play_sfx("pickup")
            if self.player.unlock_skill("power_chord"):
                sound.jingle("discovery")
                self.dialogue.start([
                    "A torn setlist scrawled in crayon. The riffs are written in blood.",
                    "You study it. The first note splits the air.",
                    "New ability unlocked: POWER CHORD (1.6x damage, costs 30 GRIT)"
                ], "Belligerent Dickhead", (240, 130, 90))
                self.tutorial_once("tut_skills",
                                   "TIP: New abilities unlock as your band levels up in battle. Select a band member and use the panel buttons.")
            else:
                self.dialogue.start([
                    "You already know this riff. The setlist crumbles."
                ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "tome_double_down":
            item["active"] = False
            sound.play_sfx("pickup")
            if self.player.unlock_skill("double_down"):
                sound.jingle("discovery")
                self.dialogue.start([
                    "A cursed vinyl etched with anger. Every groove is a scream.",
                    "You listen until the anger becomes yours.",
                    "New ability unlocked: DOUBLE DOWN (2.0x damage, costs 12 SANITY)"
                ], "Belligerent Dickhead", (240, 130, 90))
                self.tutorial_once("tut_skills",
                                   "TIP: New abilities unlock as your band levels up in battle. Select a band member and use the panel buttons.")
            else:
                self.dialogue.start([
                    "You've already internalized this one. The vinyl melts."
                ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "tome_feedback_howl":
            item["active"] = False
            sound.play_sfx("pickup")
            if self.player.unlock_skill("feedback_howl"):
                sound.jingle("discovery")
                self.dialogue.start([
                    "A rusted pedal marked 'DO NOT STEP'. You step on it.",
                    "The feedback howl lives inside the casing now. And inside you.",
                    "New ability unlocked: FEEDBACK HOWL (2.5x damage, costs 55 GRIT)"
                ], "Belligerent Dickhead", (240, 130, 90))
                self.tutorial_once("tut_skills",
                                   "TIP: New abilities unlock as your band levels up in battle. Select a band member and use the panel buttons.")
            else:
                self.dialogue.start([
                    "The pedal screams, but you've heard this song before."
                ], "Belligerent Dickhead", (240, 130, 90))

        elif ix == "booth_earplugs":
            self.player.sanity = min(100, self.player.sanity + 15)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "A pair of sound-dampening earplugs. Label reads 'FOR INTERNAL USE ONLY'.",
                "You pop them in. The screaming fades to a manageable roar.",
                "SANITY +15"
            ], "Belligerent Dickhead", (240, 130, 90))

        else:
            self.dialogue.start(["Nothing useful here."])
        self.dialogue.set_default_portrait(None)

    def interact_npc(self, npc):
        name = npc.get("name", "")
        if name == "Roadie":
            if not self.story_flags.get("roadie_talked"):
                self.story_flags["roadie_talked"] = True
                self.dialogue.start_choice(
                    "Roadie",
                    "'Bro. The acoustics down here are UNREAL. But also everything is trying to kill us. The vendor through backstage... he's got the good stuff. And the bad stuff. And the stuff that makes you see God.'",
                    ["'Where's the exit?'", "'What happened to the band?'", "'You got any gear?'"],
                    self._roadie_choice, (230, 90, 90))
            else:
                self.dialogue.start([
                    "'The stage is up north. Backstage leads deeper in.'",
                    "'Also, the drummer's holding it down backstage. Says he'll sit in once the set proves it.'"
], "Roadie", (230, 90, 90))
        elif name == "Sketchy Vendor":
            if not self.story_flags.get("vendor_talked"):
                self.story_flags["vendor_talked"] = True
                self.dialogue.start_choice(
                    "Sketchy Vendor",
                    "'Welcome to the merch table! We got shirts, patches, and things that were alive ten minutes ago! What can I do for ya?'",
                    ["'What are you selling?'", "'Are you human?'", "'Weirdest item.'"],
                    self._vendor_choice, (215, 95, 215))
            else:
                grit = int(self.player.grit)
                self.dialogue.start_choice(
                    "Sketchy Vendor",
                    f"'Back so soon? You have {grit} GRIT. That's currency down here. Spend it or keep screaming.' Pick an upgrade:",
                    ["Max HP +10 (25 GRIT)", "Attack +3 (30 GRIT)", "Defense +1 (20 GRIT)", "Not today. I'm saving it."],
                    self._vendor_upgrade_choice, (215, 95, 215))

        elif name == "Last Roadie":
            if not self.story_flags.get("last_roadie_talked"):
                self.story_flags["last_roadie_talked"] = True
                self.player.hp = min(self.player.max_hp, self.player.hp + 20)
                self.dialogue.start([
                    "'Hey. You made it to the VIP room. Real ones come here.'",
                    "'The Pit Lord's real name is Kevin. He's insecure about it.'",
                    "'Hit him in the ego. That's the only weak spot he's got.'",
                    "'Also I patched you up. You're welcome.'",
                    "HP +20 (bandage courtesy of the Last Roadie)"
                ], "Last Roadie", (110, 230, 110))
            else:
                self.dialogue.start([
                    "'Kevin's got horns, big teeth, and a terrible sense of humor.'",
                    "'Knock him into the pit. That's how you close a set.'"
                ], "Last Roadie", (110, 230, 110))

    def _vendor_upgrade_choice(self, choice):
        costs = [25, 30, 20]
        if choice == 3:
            self.dialogue.start([
                "'Smart. Hoard your grit. When the moment comes, spend it on something that hurts.'"
            ], "Sketchy Vendor", (215, 95, 215))
            return
        cost = costs[choice]
        if self.player.grit < cost:
            self.dialogue.start([
                f"'That's {cost} GRIT. You've got {int(self.player.grit)}. Go mosh, then come back.'"
            ], "Sketchy Vendor", (215, 95, 215))
            return
        self.player.grit -= cost
        if choice == 0:
            self.player.max_hp += 10
            self.player.hp = min(self.player.max_hp, self.player.hp + 10)
            stat = "Max HP +10"
        elif choice == 1:
            self.player.attack += 3
            stat = "Attack +3"
        else:
            self.player.defense += 1
            stat = "Defense +1"
        self.dialogue.start([
            f"'Deal.' He twists something under the table. You feel {stat}.",
            "Your bones rattle in a way that suggests improvement.",
            f"{stat}. Spend wisely, or scream harder."
        ], "Sketchy Vendor", (215, 95, 215))
        self.tutorial_once("tut_vendor_upgrade",
                           "TIP: The vendor upgrades your body for GRIT. GRIT fills as you fight. Keep some for the Scream.",
                           frames=300)

    def _roadie_choice(self, choice):
        if choice == 0:
            self.dialogue.start([
                "'Exit? EXIT? Brother, the only exit is through the Pit.'",
                "'The Pit Lord guards the way out. Big fella. Red. Likes to talk.'",
                "'Pro tip: don't let him talk. He's very persuasive.'"
            ], "Roadie", (230, 90, 90))
        elif choice == 1:
            self.dialogue.start([
                "'The band? Oh man... they're still playing.'",
                "'The guitarist is headlining the third circle now.'",
                "'Bass player went full method. Became the monster.'",
                "'Drummer's back there, keeping time to the void. He'll find us when it counts.'"
            ], "Roadie", (230, 90, 90))
        elif choice == 2:
            self.player.sanity -= 5
            self.dialogue.start([
                "'Take this.' He hands you a pair of earplugs.",
                "'Won't stop the demons. But it'll muffle their screaming.'",
                "SANITY -5"
            ], "Roadie", (230, 90, 90))

    def _vendor_choice(self, choice):
        if choice == 0:
            self.dialogue.start([
                "'We got the usual: suffering, existential dread, regret.'",
                "'Oh, and t-shirts. The shirts are made of... let's call it leather.'",
                "'Don't ask what kind of leather.'"
            ], "Sketchy Vendor", (215, 95, 215))
        elif choice == 1:
            self.dialogue.start([
                "'Human? Friend, nobody down here is human anymore.'",
                "'I used to sell bootleg CDs in a parking lot.'",
                "'Now I sell bootleg CDs in hell. Same job, different tax bracket.'"
            ], "Sketchy Vendor", (215, 95, 215))
        elif choice == 2:
            self.player.sanity -= 10
            self.player.attack += 5
            self.dialogue.start([
                "'Ah, a connoisseur!' He reaches under the table.",
                "'This baby is a cursed vinyl. Every scratch screams.'",
                "'You can use it as a weapon. The music never stops.'",
                "ATTACK +5, SANITY -10"
            ], "Sketchy Vendor", (215, 95, 215))

    def save_game(self):
        self.tutorial_once("tut_save", "F5 = Save. Your progress is saved to save.json automatically.")
        data = {
            "player": {
                "x": self.player.x, "y": self.player.y, "hp": self.player.hp,
                "max_hp": self.player.max_hp, "attack": self.player.attack,
                "defense": self.player.defense, "sanity": self.player.sanity,
                "kills": self.player.kills, "grit": self.player.grit,
                "level": self.player.level, "xp": self.player.xp,
                "xp_to_next": self.player.xp_to_next,
                "skills": self.player.skills,
                "inventory": self.player.inventory,
            },
            "room": self.current_room.name if self.current_room else "The Stage of Sin",
            "flags": self.story_flags,
            "enemies": {},
        }
        for name, room in self.room_map.items():
            data["enemies"][name] = [
                {"x": e["x"], "y": e["y"], "active": e.get("active", True)}
                for e in room.enemies
            ]
        with open(os.path.join(ASSETS, "save.json"), "w") as f:
            json.dump(data, f, indent=2)
        self.dialogue.start(["Game saved."])

    def load_game(self):
        path = os.path.join(ASSETS, "save.json")
        if not os.path.exists(path):
            self.dialogue.start(["No save found."])
            return
        with open(path) as f:
            data = json.load(f)
        self.player = Player()
        p = data["player"]
        self.player.x, self.player.y = p["x"], p["y"]
        self.player.hp = p["hp"]
        self.player.max_hp = p.get("max_hp", 100)
        self.player.attack = p["attack"]
        self.player.defense = p["defense"]
        self.player.sanity = p["sanity"]
        self.player.kills = p["kills"]
        self.player.grit = p.get("grit", 0)
        self.player.level = p.get("level", 1)
        self.player.xp = p.get("xp", 0)
        self.player.xp_to_next = p.get("xp_to_next", 30)
        self.player.skills = p.get("skills", [])
        self.player.inventory = p["inventory"]
        self.story_flags = data.get("flags", {})
        self.setup_rooms()
        room_name = data.get("room", "The Stage of Sin")
        if room_name in self.room_map:
            self.current_room = self.room_map[room_name]
        for name, enemies_data in data.get("enemies", {}).items():
            if name in self.room_map:
                for i, ed in enumerate(enemies_data):
                    if i < len(self.room_map[name].enemies):
                        self.room_map[name].enemies[i]["active"] = ed["active"]
        self.state = GameState.PLAYING

    def update(self):
        if self.current_room and (self.embers is None or getattr(self.embers, "room_name", None) != self.current_room.name):
            base = self.current_room.ambient_color
            acc = tuple(min(255, c + 45) for c in base)
            hot = (max(90, base[0] + 60), max(50, base[1] + 55), max(30, base[2] + 45))
            self.embers = fxkit.Drift(SCREEN_W, SCREEN_H, [base, acc, hot], 26)
            self.embers.room_name = self.current_room.name
        if self.embers and self.state == GameState.PLAYING and not self.combat.active:
            self.embers.update(1 / 30.0)
        ann = sound.take_announce()
        if ann:
            self.announce_track(ann)
        if self.transitioning:
            self.transition_alpha = min(255, self.transition_alpha + 15)
            if self.transition_alpha >= 255:
                room_name, sx, sy = self.transition_target
                if room_name in self.room_map:
                    self.current_room = self.room_map[room_name]
                self.player.x = sx * TILE + TILE // 2
                self.player.y = sy * TILE + TILE // 2
                self.transitioning = False
                self.show_room_objective()
                self._sync_room_music()
                if self.transition_callback:
                    cb = self.transition_callback
                    self.transition_callback = None
                    cb()
        else:
            if self.transition_alpha > 0:
                self.transition_alpha = max(0, self.transition_alpha - 15)

        if self.state == GameState.HD_REVEAL:
            self.hd_timer -= 1
            if self.hd_timer <= 0:
                self.hd_overlay = None
                self.state = GameState.PLAYING
                if self.transition_callback:
                    cb = self.transition_callback
                    self.transition_callback = None
                    cb()

        if self.track_announcement_timer > 0:
            self.track_announcement_timer -= 1

        if self.help_banner_timer > 0:
            self.help_banner_timer -= 1
            if self.help_banner_timer == 0:
                self.help_banner = ""

        if self.objective_banner_timer > 0:
            self.objective_banner_timer -= 1

        self.cutscene.update()
        self.dialogue.update()
        if self.combat.active:
            self.combat.update(self.player)
        else:
            # Passive regen while out of combat: +1 HP per few seconds
            self.player.passive_regen(1)
        if self.state == GameState.PLAYING and not self.dialogue.active and not self.combat.active:
            self.handle_tutorial_signals()
        camera.update()

    def render_menu(self):
        screen.fill((5, 0, 0))
        t = pygame.time.get_ticks() / 1000
        for i in range(40):
            sx = int(SCREEN_W // 2 + math.sin(t * 0.5 + i * 0.7) * 400)
            sy = int(SCREEN_H // 2 + math.cos(t * 0.3 + i * 0.4) * 300)
            sz = 1 + int(abs(math.sin(t + i)) * 2)
            pygame.draw.circle(screen, (150 + int(50 * math.sin(t + i)), 0, 0), (sx, sy), sz)

        title = fonts.render_title("T3MP3ST", (200, 0, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))
        band = fonts.render_band("BELLIGrant DICKHEAD", (200, 50, 50))
        screen.blit(band, (SCREEN_W // 2 - band.get_width() // 2, 160))
        sub = fonts.render_small("presents: A Descent Into Madness", (120, 40, 40))
        screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 210))

        options = ["New Game", "Load Game", "Credits", "Quit"]
        for i, opt in enumerate(options):
            c = (255, 50, 50) if i == self.menu_select else (120, 60, 60)
            prefix = "> " if i == self.menu_select else "  "
            ot = fonts.render(prefix + opt, c, big=True)
            screen.blit(ot, (SCREEN_W // 2 - ot.get_width() // 2, 300 + i * 50))

        hints = [
            "WASD: Move | SPACE/ENTER: Interact | I: Inventory | F: Scream (Heal when GRIT full) | F11: Fullscreen",
            "M: Mute | F5: Save | Drop music by slot name in assets/music/ - see ASSET_MANIFEST.md",
        ]
        for i, h in enumerate(hints):
            ht = fonts.render_small(h, (60, 30, 30))
            screen.blit(ht, (SCREEN_W // 2 - ht.get_width() // 2, SCREEN_H - 60 + i * 16))

    def render_playing(self):
        if not self.current_room:
            return
        cam_x = max(0, min(self.player.x - SCREEN_W // 2,
                           self.current_room.width * TILE - SCREEN_W))
        cam_y = max(0, min(self.player.y - SCREEN_H // 2,
                           self.current_room.height * TILE - SCREEN_H))
        screen.fill(self.current_room.ambient_color)
        locked_keys = set()
        if self.current_room:
            for d in self.current_room.doors:
                if not self.door_is_unlocked(d):
                    locked_keys.add(id(d))
        self.current_room.render(screen, cam_x + camera.x, cam_y + camera.y, locked_door_keys=locked_keys)
        self.player.render(screen, cam_x + camera.x, cam_y + camera.y)
        if self.embers:
            self.embers.render(screen)
        screen.blit(self.vignette, (0, 0))
        self._render_hud()

    def _render_hud(self):
        hp_pct = self.player.hp / self.player.max_hp
        pygame.draw.rect(screen, (40, 0, 0), (10, 10, 202, 22))
        pygame.draw.rect(screen, (180, 0, 0), (11, 11, int(200 * hp_pct), 20))
        screen.blit(fonts.render_small(f"HP: {self.player.hp}/{self.player.max_hp}", (255, 255, 255)), (15, 12))

        san_pct = self.player.sanity / 100
        sc = (0, 0, 200) if san_pct > 0.5 else (150, 0, 150) if san_pct > 0.25 else (200, 0, 0)
        pygame.draw.rect(screen, (0, 0, 40), (10, 36, 202, 16))
        pygame.draw.rect(screen, sc, (11, 37, int(200 * san_pct), 14))
        screen.blit(fonts.render_small(f"SAN: {self.player.sanity}", (200, 200, 200)), (15, 37))

        # GRIT meter (heals HP when full via F)
        grit_pct = self.player.grit / self.player.grit_max
        grit_flash = (pygame.time.get_ticks() // 250) % 2 if self.player.can_scream() else 0
        gum = "READY - PRESS F" if self.player.can_scream() else "BUILD IN COMBAT"
        gc = (220, 180, 50) if self.player.can_scream() else (130, 90, 30)
        pygame.draw.rect(screen, (40, 40, 15), (10, 58, 202, 16))
        pygame.draw.rect(screen, gc, (11, 59, int(200 * grit_pct), 14))
        screen.blit(fonts.render_small(f"GRIT: {int(self.player.grit)}/100  {gum}", (255, 220, 120)), (15, 59))

        screen.blit(fonts.render_small(self.current_room.name, (150, 100, 100)),
                     (SCREEN_W - fonts.render_small(self.current_room.name).get_width() - 10, 10))
        kt = f"Kills: {self.player.kills}"
        screen.blit(fonts.render_small(kt, (150, 50, 50)),
                     (SCREEN_W - fonts.render_small(kt).get_width() - 10, 28))
        screen.blit(fonts.render_small("BELLIGrant DICKHEAD", (80, 30, 30)),
                     (SCREEN_W - fonts.render_small("BELLIGrant DICKHEAD").get_width() - 10, 46))

        if self.track_announcement_timer > 0:
            at = fonts.render(self.track_announcement, (200, 200, 200))
            at.set_alpha(min(255, self.track_announcement_timer * 4))
            screen.blit(at, (SCREEN_W // 2 - at.get_width() // 2, 70))

        # Objective banner (tutorial line) - top center
        obj = self.tutorial_objective()
        if obj:
            obj_t = fonts.render_small(obj, (200, 180, 120))
            screen.blit(obj_t, (SCREEN_W // 2 - obj_t.get_width() // 2, 90))

        # Delayed objective reveal with portrait
        if self.objective_banner_timer > 0 and self.current_room:
            reveal = self.current_room.objective if not self.objective_banner else self.objective_banner
            r = pygame.Rect(SCREEN_W // 2 - 260, 150, 520, 42)
            panel = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            panel.fill((15, 10, 5, 235))
            pygame.draw.rect(panel, (200, 120, 40), panel.get_rect(), 2)
            rt = fonts.render_small(reveal, (255, 220, 150))
            panel.blit(rt, (10, 12))
            screen.blit(panel, r.topleft)
            if self.objective_banner_portrait:
                screen.blit(self.objective_banner_portrait, (r.x + r.width + 10, r.y + r.height - 160))
            if r.collidepoint(pygame.mouse.get_pos()):
                pass

        # Help banner (one-time tips)
        if self.help_banner and self.help_banner_timer > 0:
            hb = fonts.render(self.help_banner, (255, 220, 50))
            panel = pygame.Surface((hb.get_width() + 24, hb.get_height() + 12), pygame.SRCALPHA)
            panel.fill((10, 10, 5, 230))
            pygame.draw.rect(panel, (200, 160, 40), panel.get_rect(), 1)
            screen.blit(panel, (SCREEN_W // 2 - hb.get_width() // 2 - 12, 118))
            screen.blit(hb, (SCREEN_W // 2 - hb.get_width() // 2, 124))

        # Interaction prompt: show what SPACE will target
        prompt = self.get_interact_prompt()
        if prompt and not self.combat.active and not self.dialogue.active:
            found = self.nearest_interactable()
            if found:
                d = found[0]
                dist_text = "right here" if d == 0 else f"{d} tiles away"
                p = fonts.render(f"{prompt}  ({dist_text})", (255, 220, 120))
                box = pygame.Surface((p.get_width() + 20, p.get_height() + 10), pygame.SRCALPHA)
                box.fill((20, 10, 5, 200))
                pygame.draw.rect(box, (180, 120, 50), box.get_rect(), 1)
                screen.blit(box, (SCREEN_W // 2 - p.get_width() // 2 - 10,
                                  SCREEN_H - 45))
                screen.blit(p, (SCREEN_W // 2 - p.get_width() // 2, SCREEN_H - 40))

        if self.player.sanity < 30:
            t = pygame.time.get_ticks() / 1000
            intensity = (30 - self.player.sanity) / 30
            gx = int(math.sin(t * 5) * 8 * intensity)
            tmp = screen.copy()
            screen.blit(tmp, (gx, 0))
            if random.random() < intensity * 0.1:
                gy = random.randint(0, SCREEN_H - 20)
                pygame.draw.rect(screen, (150, 0, 0), (0, gy, SCREEN_W, random.randint(5, 20)))

    def render_inventory(self):
        screen.fill((10, 5, 5))
        screen.blit(fonts.render("INVENTORY", (240, 130, 90), big=True),
                     (SCREEN_W // 2 - fonts.render("INVENTORY", (240, 130, 90), big=True).get_width() // 2, 30))
        screen.blit(fonts.render_band(self.player.name, (200, 50, 50)), (50, 80))

        stats = [f"Level: {self.player.level}   XP: {self.player.xp}/{self.player.xp_to_next}",
                 f"HP: {self.player.hp}/{self.player.max_hp}", f"ATK: {self.player.attack}",
                 f"DEF: {self.player.defense}", f"SANITY: {self.player.sanity}",
                 f"GRIT: {int(self.player.grit)}/100", f"KILLS: {self.player.kills}"]
        for i, s in enumerate(stats):
            screen.blit(fonts.render(s, (150, 150, 150)), (50, 120 + i * 30))

        # XP bar
        if self.player.xp_to_next:
            bar_w = 200
            filled = int(bar_w * self.player.xp / self.player.xp_to_next)
            bar_y = 120 + len(stats) * 30 + 4
            pygame.draw.rect(screen, (30, 15, 10), (50, bar_y, bar_w, 10))
            pygame.draw.rect(screen, (0, 160, 220), (50, bar_y, filled, 10))

        # Abilities
        screen.blit(fonts.render("Abilities:", (100, 140, 180)), (50, bar_y + 20))
        y_abil = bar_y + 50
        for sid in self.player.skills:
            sk = SKILLS[sid]
            screen.blit(fonts.render(f"  {sk['name']} ({sk['cost']} {sk['cost_type'].upper()})",
                                     (120, 190, 255)), (50, y_abil))
            y_abil += 24
        if not self.player.skills:
            screen.blit(fonts.render_small("  None yet", (80, 80, 80)), (50, y_abil))

        screen.blit(fonts.render("Gear:", (150, 100, 100)), (400, 120))
        names = {"mic": "Stage Mic (ATK+3)", "crypt_key": "DO NOT USE Key",
                 "broken_bottle": "Broken Bottle (ATK+8)", "guitaraxe": "Guitar-Axe (ATK+15)",
                 "mixer_fader": "Master Fader (ATK+12)", "vip_lamp": "Stage Lamp (ATK+10)"}
        if self.player.inventory:
            for i, item in enumerate(self.player.inventory):
                screen.blit(fonts.render(f"- {names.get(item, item)}", (180, 180, 180)), (420, 150 + i * 25))
        else:
            screen.blit(fonts.render("  (empty)", (80, 80, 80)), (420, 150))

        screen.blit(fonts.render_small("Press I or ESC to close", (80, 40, 40)),
                     (SCREEN_W // 2 - 80, SCREEN_H - 40))

    def render_game_over(self):
        screen.fill((0, 0, 0))
        t = pygame.time.get_ticks() / 1000
        go = fonts.render_title("KNOCKED OUT", (180, 0, 0))
        screen.blit(go, (SCREEN_W // 2 - go.get_width() // 2, 200 + int(math.sin(t * 2) * 10)))
        lines = ["The darkness swallows another vocalist.",
                 f"Kills: {self.player.kills}", f"Sanity: {self.player.sanity}%", "",
                 "ENTER to retry | Q to quit"]
        for i, l in enumerate(lines):
            st = fonts.render(l, (120, 0, 0))
            screen.blit(st, (SCREEN_W // 2 - st.get_width() // 2, 320 + i * 30))

    def render_credits(self):
        screen.fill((5, 0, 0))
        lines = [("T3MP3ST", fonts.render_title, (200, 0, 0)),
                 ("", None, None),
                 ("A BELLIGrant DICKHEAD Production", fonts.render_band, (200, 50, 50)),
                 ("", None, None),
                 ("Music: Belligerent Dickhead", fonts.render, (150, 100, 100)),
                 ("Concept: Belligerent Dickhead", fonts.render, (150, 100, 100)),
                 ("Code: Assisted by AI", fonts.render, (150, 100, 100)),
                 ("Suffering: Everyone", fonts.render, (150, 100, 100)),
                 ("", None, None),
                 ("No demons were harmed in the making of this game.", fonts.render, (100, 60, 60)),
                 ("Several were inconvenienced.", fonts.render, (100, 60, 60)),
                 ("", None, None),
                 ("Press any key to return.", fonts.render_small, (80, 40, 40))]
        for i, (text, fn, col) in enumerate(lines):
            if fn:
                screen.blit(fn(text, col), (SCREEN_W // 2 - fn(text, col).get_width() // 2, 60 + i * 38))

    def render(self):
        if self.state == GameState.MENU:
            self.render_menu()
        elif self.state == GameState.PLAYING:
            self.render_playing()
        elif self.state == GameState.HD_REVEAL:
            if self.hd_overlay:
                screen.blit(self.hd_overlay, (0, 0))
        elif self.state == GameState.GAME_OVER:
            self.render_game_over()
        elif self.state == GameState.INVENTORY:
            self.render_inventory()
        elif self.state == GameState.CREDITS:
            self.render_credits()

        if self.state in (GameState.PLAYING, GameState.INVENTORY):
            if self.transitioning or self.transition_alpha > 0:
                ov = pygame.Surface((SCREEN_W, SCREEN_H))
                ov.fill((0, 0, 0))
                ov.set_alpha(int(self.transition_alpha))
                screen.blit(ov, (0, 0))

        self.cutscene.render(screen)
        if self.combat.active:
            self.combat.render(screen, self.player)
        self.dialogue.render(screen)


def main():
    game = Game()
    game.generate_asset_manifest()
    sound.play_menu_music()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    if not game.combat.active and game.state == GameState.PLAYING:
                        game.state = GameState.MENU
                        sound.play_menu_music()
                    elif not game.combat.active and game.state == GameState.INVENTORY:
                        game.state = GameState.PLAYING

            if game.cutscene.active:
                game.cutscene.handle_input(event)
            elif game.dialogue.active:
                game.dialogue.handle_input(event)
            elif game.combat.active:
                game.handle_combat_input(event)
            elif game.state == GameState.MENU:
                game.handle_menu_input(event)
            elif game.state == GameState.PLAYING:
                game.handle_playing_input(event)
            elif game.state == GameState.INVENTORY:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_i, pygame.K_ESCAPE):
                        game.state = GameState.PLAYING
            elif game.state == GameState.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.state = GameState.MENU
                        sound.play_menu_music()
                    elif event.key == pygame.K_q:
                        running = False
            elif game.state == GameState.CREDITS:
                if event.type == pygame.KEYDOWN:
                    game.state = GameState.MENU
                    sound.play_menu_music()

        keys = pygame.key.get_pressed()
        if game.state == GameState.PLAYING and not game.dialogue.active and not game.combat.active:
            game.player.update(keys, game.current_room)

        game.update()
        game.render()

        fps = fonts.render_small(f"FPS: {int(clock.get_fps())}", (50, 50, 50))
        screen.blit(fps, (SCREEN_W - 70, SCREEN_H - 18))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
