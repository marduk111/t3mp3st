import pygame
import sys
import os
import math
import random
import json
import struct
import array
import re
from enum import Enum, auto

import battle_bridge
import fxkit

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

pygame.init()

try:
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=2)
except Exception:
    pass

SCREEN_W, SCREEN_H = 1024, 768
FPS = 30
TILE = 32

# Debut-album branding (working title from an older repo is retired).
GAME_TITLE = "THEATRE OF SORROW"

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption(GAME_TITLE + " - Marduk vs The Beast")
clock = pygame.time.Clock()

fullscreen = False


def toggle_fullscreen():
    global screen, fullscreen
    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H),
                                         pygame.FULLSCREEN | pygame.SCALED)
    else:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

ASSETS = os.path.dirname(__file__)
MUSIC_DIR = os.path.join(ASSETS, "assets", "music")
IMAGES_DIR = os.path.join(ASSETS, "assets", "images")
PORTRAITS_DIR = os.path.join(ASSETS, "assets", "portraits")
ANIM_DIR = os.path.join(ASSETS, "assets", "animations")
for _dir in (MUSIC_DIR, IMAGES_DIR, PORTRAITS_DIR, ANIM_DIR):
    os.makedirs(_dir, exist_ok=True)

# Story beats that can play a numbered PNG frame sequence from
# assets/animations/<key>/. Moments with no frames fall back to text-only
# (the intro's "fall" beat ships with a built-in procedural placeholder).
REEL_MOMENTS = {
    "fall": "Opening cutscene: fullscreen reel (stage gives way) between dialogue lines",
    "azrael_intro": "Opening cutscene: fullscreen AZRAEL kung fu reel between dialogue lines",
    "chamber": "Entering the Pit Lord's Chamber for the first time",
    "pit_lord": "Right before the Enforcer boss fight",
    "beast": "Right before the final battle with the Pit Lord",
    "zombie": "Right before the Zombie Fan fight",
    "corpse": "Right before the Reanimated Roadie fight",
    "shadow": "Right before the Stage Ninja fight",
    "demon": "Right before the Enforcer fight (non-boss)",
    "engineer": "Right before the Sound Engineer fight",
    "ending": "Ending cutscene: climbing back onto the stage",
}


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
    HELP = auto()
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

    def wrap(self, text, max_width, big=False):
        f = self.body_big if big else self.body
        out = []
        cur = ""
        for w in text.split():
            joined = cur + " " + w if cur else w
            if cur and f.size(joined)[0] > max_width:
                out.append(cur)
                cur = w
            else:
                cur = joined
        if cur:
            out.append(cur)
        return out, f

    def render_wrapped(self, text, color=(200, 200, 200), big=False, max_width=700):
        lines, f = self.wrap(text, max_width, big)
        sfs = [f.render(l, True, color) for l in lines]
        h = sum(s.get_height() for s in sfs) + 2 * (len(sfs) - 1)
        surf = pygame.Surface((max_width, h), pygame.SRCALPHA)
        y = 0
        for s in sfs:
            surf.blit(s, (0, y))
            y += s.get_height() + 2
        return surf


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
            sound = pygame.mixer.Sound(buffer=stereo.tobytes())
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

    @staticmethod
    def generate_room_drone():
        samples = []
        duration = 4.0
        n = int(ProceduralAudio.RATE * duration)
        for i in range(n):
            t = i / ProceduralAudio.RATE
            env = min(1, t * 2) * min(1, (duration - t) * 2)
            base = math.sin(2 * math.pi * 43.65 * t) * 0.3
            sub = math.sin(2 * math.pi * 21.8 * t) * 0.2
            wob = math.sin(2 * math.pi * 0.35 * t + math.sin(t * 0.5) * 1.5) * 0.25
            fifth = math.sin(2 * math.pi * 65.4 * t) * 0.12
            samples.append((base + sub + wob + fifth) * env)
        return ProceduralAudio._make_sound(samples)


class SoundManager:
    # Narrative music slots. Players can drop files matching these names
    # (or numbered variants like 01-stage.mp3) into assets/music/ and they
    # play at the matching moment in-game.
    MUSIC_SLOTS = [
        "menu", "intro", "stage", "backstage", "merch", "pit", "greenroom",
        "booth", "chamber", "combat", "zombie", "corpse", "shadow", "demon",
        "engineer", "boss", "levelup", "discovery",
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

    # Music slots that play during a fight (any non-boss enemy type or a boss).
    BATTLE_SLOTS = frozenset({"combat", "zombie", "corpse", "shadow", "demon", "engineer", "boss"})

    def __init__(self):
        self.external_tracks = load_music_files()
        self.current_track = -1
        self.music_volume = 0.4
        self.sfx_volume = 0.7
        self.muted = False
        self.sfx_cache = {}
        self.music_channel = None
        self.jingle_channel = None
        self.voice_channel = None
        self.using_external = False

        try:
            pygame.mixer.set_num_channels(8)
            self.music_channel = pygame.mixer.Channel(0)
            self.jingle_channel = pygame.mixer.Channel(1)
            self.voice_channel = pygame.mixer.Channel(2)
        except Exception:
            self.jingle_channel = None
            self.voice_channel = None

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
        self.room_drone = ProceduralAudio.generate_room_drone()

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
                        cand = os.path.join(MUSIC_DIR, f)
                        prev = slots.get(slot)
                        if prev is None or (cand.lower().endswith(".ogg")
                                            and not prev.lower().endswith(".ogg")):
                            slots[slot] = cand
        return slots

    def play_ambient(self, slot, force=True):
        if self.muted:
            return
        path = self.slots.get(slot)
        if not path:
            if slot in ("menu", "intro", "ending", "credits"):
                self._play_procedural("menu")
            elif slot in self.BATTLE_SLOTS:
                self._play_procedural("combat")
            else:
                self._play_procedural("room")
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
        self._stop_procedural()
        if kind == "menu":
            snd = self.menu_drone
        elif kind == "combat":
            snd = self.combat_riff
        else:
            snd = self.room_drone
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
            self.room_drone.stop()
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
        if self.ambient_slot in self.BATTLE_SLOTS:
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

    def play_voice(self, slot):
        """Play a music-slot file exactly ONCE, layered over whatever track is
        already playing (it never touches pygame.mixer.music, so ambient stays).
        Used to sync a clip with an animation reel (e.g. the zombie clip during
        the pre-battle reel). A new call or stop_voice() cuts it off."""
        if self.muted or not self.voice_channel:
            return
        path = self.slots.get(slot)
        if not path:
            return
        snd = self.jingle_cache.get(slot)
        if snd is None:
            try:
                snd = pygame.mixer.Sound(path)
            except Exception:
                return
            self.jingle_cache[slot] = snd
        try:
            self.voice_channel.set_volume(self.music_volume)
            self.voice_channel.play(snd)
        except Exception:
            pass

    def stop_voice(self):
        if self.voice_channel is not None:
            try:
                self.voice_channel.stop()
            except Exception:
                pass

    def current_track_name(self):
        if self.ambient_slot:
            path = self.slots.get(self.ambient_slot)
            if path:
                return os.path.basename(path)
            if self.ambient_slot == "menu":
                return "Procedural Hellnoise (menu drone)"
            if self.ambient_slot in self.BATTLE_SLOTS:
                return "Procedural Combat Riff"
            return "Procedural Room Drone"
        return "silence"

    def take_announce(self):
        if not self._pending_announce:
            return None
        self._pending_announce = False
        return self.current_track_name()

    def stop_music(self):
        pygame.mixer.music.stop()
        self._stop_procedural()
        self.stop_voice()
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
                elif kind == "nose":
                    nc = spec[1] if len(spec) > 1 else (200, 40, 40)
                    for dx in (15, 16):
                        for dy in (15, 16):
                            art.set_at((dx, dy), nc)
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
        if key in ("bludgeon", "bludgeon_the_clown"):
            return self._surface((215, 195, 165),
                                 [("nose",), ("glow",), ("teeth", 8, 24), ("mouth", 12, 20, 22)])
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
        self.name = "Marduk"

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
            "Stage Ninja: 'I'll open for your funeral, Marduk.'",
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
        "Marduk: 'You should've stayed a one-hit wonder.'",
        "Marduk: 'My dog plays better than you, and he's a corpse too.'",
        "Marduk: 'I've headlined worse crowds than hell.'",
        "Marduk: 'Let me autograph your face. Real close. With my boot.'",
        "Marduk: 'You're all gimmick, no substance. Extra disembowelment for that.'",
        "Marduk: 'This is the shortest opening set you've ever done.'",
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


class Reel:
    """Short authored clip player. Looks for PNG/JPG frame sequences in
    `assets/animations/<key>/NNNN.png` and plays them at one frame per engine
    tick (30 FPS). With no frames present and `placeholder=True`, draws a
    procedural scene so the beat is visible before real art exists.

    Frames are decoded lazily at a reduced internal resolution and kept in a
    small window around the playhead (prefetched ahead, pruned behind), so
    long reels cost a fixed amount of memory and cutscenes no longer pause to
    decode every frame up front. The reduced frame is smooth-scaled up at blit
    time."""

    PROC_TICKS = 90  # 3 seconds of the placeholder scene at FPS 30

    # Internal decode resolution, as a fraction of the full screen. Lower =
    # faster loads, less memory, and a softer upscale. 1.0 = pixel-perfect.
    RENDER_SCALE = 0.75
    PREFETCH = 18          # frames decoded ahead of the playhead
    KEEP_BEHIND = 4        # frames kept behind the playhead before pruning
    PREFILL_PER_TICK = 2   # frames decoded per engine tick (keeps ticks short)

    # (x, phase, speed, palette-index) so the embers are deterministic and cheap
    EMBERS = [(x, (k * 0.17 + x * 0.013) % 1.0, 0.5 + (k % 3) * 0.28, k % 4)
              for x in range(20, 1024, 16) for k in range(3)]

    def __init__(self, key="", placeholder=True):
        self.key = key
        self.placeholder = placeholder
        self.frame_paths = []
        self.frames = {}
        self.tick = 0
        self._decoded = -1
        self._work = (int(SCREEN_W * self.RENDER_SCALE),
                      int(SCREEN_H * self.RENDER_SCALE))
        self._gradient = None
        self._flash = None
        if key:
            self.load(key)

    def load(self, key):
        self.key = key
        self.frame_paths = []
        self.frames = {}
        self._decoded = -1
        folder = os.path.join(ANIM_DIR, key)
        if os.path.isdir(folder):
            names = []
            for f in os.listdir(folder):
                if not f.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue
                stem = os.path.splitext(f)[0]
                try:
                    n = int(stem)
                except ValueError:
                    continue
                names.append((n, os.path.join(folder, f)))
            names.sort()
            self.frame_paths = [p for _, p in names]
        return self

    def is_placeholder(self):
        return not self.frame_paths

    def total_frames(self):
        return len(self.frame_paths)

    def preload(self):
        # Lightweight: decode only the first frame so the clip can start
        # instantly; the rest stream in via prefill() during dialogue/play.
        if self.frame_paths and 0 not in self.frames:
            self._decode(0)

    def reset(self):
        self.tick = 0

    def advance(self):
        self.tick += 1

    def duration(self):
        return self.total_frames() if self.frame_paths else (
            self.PROC_TICKS if self.placeholder else 0)

    def prefill(self, budget=None):
        # Decode a few frames ahead of the playhead each call, then drop
        # frames well behind it so memory stays bounded for any reel length.
        if not self.frame_paths:
            return
        if budget is None:
            budget = self.PREFILL_PER_TICK
        limit = min(self.tick + self.PREFETCH, self.total_frames() - 1)
        while budget > 0 and self._decoded < limit:
            self._decoded += 1
            self._decode(self._decoded)
            budget -= 1
        self._prune()

    def _prune(self):
        if not self.frames:
            return
        lo = self.tick - self.KEEP_BEHIND
        for k in [k for k in self.frames if k < lo]:
            del self.frames[k]

    def _decode(self, idx):
        try:
            img = pygame.image.load(self.frame_paths[idx])
            try:
                img = img.convert()
            except pygame.error:
                pass
            tw, th = self._work
            sw, sh = img.get_size()
            if (sw, sh) != (tw, th):
                # Cover-fit: scale up to fill the whole working size (no
                # distortion), then crop the overflow centered.
                scale = max(tw / sw, th / sh)
                nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
                img = pygame.transform.scale(img, (nw, nh))
                ox, oy = max(0, (nw - tw) // 2), max(0, (nh - th) // 2)
                img = img.subsurface((ox, oy, tw, th)).copy()
            self.frames[idx] = img
        except Exception:
            pass

    def frame(self):
        if self.frame_paths:
            idx = min(self.tick, self.total_frames() - 1)
            if idx not in self.frames:
                self._decode(idx)
            return self.frames.get(idx)
        if self.placeholder:
            return self._procedural_frame()
        return None

    def blit(self, surface, pos=(0, 0)):
        f = self.frame()
        if f is None:
            return
        if f.get_size() != surface.get_size():
            f = pygame.transform.smoothscale(f, surface.get_size())
        surface.blit(f, pos)

    def _procedural_frame(self):
        if self._gradient is None:
            g = pygame.Surface((SCREEN_W, SCREEN_H))
            for y in range(SCREEN_H):
                k = y / SCREEN_H
                col = (int(16 - 9 * k), int(4 - 2 * k), int(18 - 6 * k))
                pygame.draw.line(g, col, (0, y), (SCREEN_W, y))
            self._gradient = g
        if self._flash is None:
            self._flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            self._flash.fill((255, 205, 130))
        s = pygame.Surface((SCREEN_W, SCREEN_H))
        s.blit(self._gradient, (0, 0))
        t = self.tick / float(self.PROC_TICKS)
        half = 0.5 * self.PROC_TICKS

        if t < 0.18:
            for i in range(6):
                x0 = 100 + i * 150 + (i % 3) * 30
                y0 = SCREEN_H * (0.66 + 0.05 * i)
                fade = 1.0 - t / 0.18
                col = (int(255 * fade), int(190 * fade), int(80 * fade))
                pygame.draw.line(s, col, (x0, y0), (x0 + (90 + 25 * i), y0 + 18 * (1 if i % 2 else -1)), 3)

        for x, ph, sp, ci in self.EMBERS:
            yy = SCREEN_H - (((ph + t * sp) % 1.0) * SCREEN_H)
            cols = [(236, 182, 112), (200, 172, 90), (214, 152, 244), (168, 112, 220)]
            pygame.draw.circle(s, cols[ci], (x, int(yy)), 2 if ci else 3)

        cx = SCREEN_W // 2 + int(math.sin(t * 7.0) * 8)
        p = max(0.0, min(1.0, (t - 0.12) / 0.58))
        py = int(SCREEN_H * (0.06 + 0.9 * p * p))
        tail = int(90 + 150 * (1.0 - p))
        pygame.draw.line(s, (255, 190, 80), (cx, py),
                         (cx + int(math.sin(t * 7.0) * 5), py + tail), 8)
        pygame.draw.line(s, (255, 245, 215), (cx - 1, py),
                         (cx + int(math.sin(t * 7.0) * 5), py + tail // 2), 3)
        pygame.draw.circle(s, (255, 240, 190), (cx, py), 7)

        if t > 0.86:
            k = min(1.0, (t - 0.86) / 0.08)
            a = int(150 * k)
            if t > 0.94:
                a = int(150 * max(0.0, 1.0 - (t - 0.94) / 0.06))
            self._flash.set_alpha(a)
            s.blit(self._flash, (0, 0))
        return s


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
        self.reel = None
        self.reel_segments = []
        self.reel_lines = set()
        self.reel_after = False
        self.reel_voice = ""
        self.reel_phase = False
        self.reel_breaks = {}
        self._break_resume = False
        self.portrait_map = {}
        self._stripped = []
        self._speakers = []

    def start(self, lines, bg_color=(5, 0, 0), callback=None, portrait=None, label="",
              reel_key="", reel_lines=(), reel_placeholder=True,
              reel_after=False, reel_voice="", portrait_map=None, reel_plan=None,
              reel_breaks=None):
        self.active = True
        self.lines = lines
        self.current = 0
        self.char_index = 0
        self.timer = 0
        self.bg_color = bg_color
        self.callback = callback
        self.portrait_img = portraits.get(portrait) if portrait else None
        self.portrait_label = label
        self.reel_lines = set(reel_lines)
        self.reel_after = reel_after
        self.reel_voice = reel_voice
        self.reel_phase = False
        self._break_resume = False
        self.portrait_map = portrait_map or {}
        self._stripped = []
        self._speakers = []
        if self.portrait_map:
            for line in lines:
                text, speaker = self._strip_speaker(line)
                self._stripped.append(text)
                self._speakers.append(speaker)
        else:
            self._stripped = list(lines)
            self._speakers = [None] * len(lines)
        if reel_plan:
            self.reel_segments = []
            for start_line, end_line, key in reel_plan:
                r = Reel(key, placeholder=reel_placeholder)
                r.preload()
                r.reset()
                self.reel_segments.append((start_line, end_line, r))
            self.reel = None
            self.reel_lines = set()
            self.current_reel_index = 0
        elif reel_key:
            self.reel = Reel(reel_key, placeholder=reel_placeholder)
            self.reel.preload()
            self.reel.reset()
            self.reel_segments = []
        else:
            self.reel = None
            self.reel_segments = []
        self.reel_breaks = {}
        if reel_breaks:
            for line_idx, key in reel_breaks.items():
                br = Reel(key, placeholder=reel_placeholder)
                br.preload()
                br.reset()
                self.reel_breaks[line_idx] = br
        if reel_after and self.reel is not None and self.reel.duration() > 0:
            self.reel.reset()

    def _strip_speaker(self, line):
        upper = line.upper()
        for prefix in ("AZRAEL:", "MARDUK:", "PIT LORD:", "ZOMBIE FAN:"):
            if upper.startswith(prefix):
                return line[len(prefix):].lstrip(" '"), prefix[:-1]
        for key in self.portrait_map:
            ukey = key.upper() + ":"
            if upper.startswith(ukey):
                return line[len(ukey):].lstrip(" '"), key
        return line, None

    def _shown_line(self):
        text = self._stripped[self.current]
        if self.char_index < len(text):
            return text[:self.char_index]
        return text

    def _current_speaker_portrait(self):
        speaker = self._speakers[self.current]
        if speaker:
            entry = self.portrait_map.get(speaker)
            if entry:
                key, label = entry
                return portraits.get(key), label
        return self.portrait_img, self.portrait_label

    def _active_reel(self):
        if self.reel_segments:
            for start_line, end_line, r in self.reel_segments:
                if start_line <= self.current <= end_line:
                    return r
            return None
        if self.reel is not None and self.current in self.reel_lines:
            return self.reel
        return None

    def _finish(self):
        self.active = False
        self.reel_phase = False
        self._break_resume = False
        if self.callback:
            self.callback()

    def update(self):
        if not self.active:
            return
        self.timer += 1
        if self.reel_phase:
            if self.reel is not None:
                self.reel.advance()
                self.reel.prefill()
                if self.reel.tick >= self.reel.duration():
                    if self._break_resume:
                        self.reel_phase = False
                        self._break_resume = False
                        self.reel = None
                    else:
                        self._finish()
            return
        if self.timer % 2 == 0:
            if self.char_index < len(self._stripped[self.current]):
                self.char_index += 1
        active = self._active_reel()
        if active is not None:
            active.advance()
            active.prefill()
        # Stream frames ahead while the player reads, so the reel is warm
        # (or fully seeded) by the time it plays.
        for br in self.reel_breaks.values():
            br.prefill()
        if self.reel is not None:
            self.reel.prefill()

    def handle_input(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.reel_phase:
                    if self._break_resume:
                        self.reel_phase = False
                        self._break_resume = False
                        self.reel = None
                    else:
                        self._finish()
                    return
                if self.char_index < len(self._stripped[self.current]):
                    self.char_index = len(self._stripped[self.current])
                else:
                    prev = self.current
                    self.current += 1
                    self.char_index = 0
                    if prev in self.reel_breaks and self.reel_breaks[prev].duration() > 0:
                        self.reel_phase = True
                        self._break_resume = True
                        self.reel = self.reel_breaks[prev]
                        self.reel.reset()
                        return
                    if self.current >= len(self.lines):
                        if (self.reel_after and self.reel is not None
                                and self.reel.duration() > 0):
                            self.reel_phase = True
                            self.reel.reset()
                            if self.reel_voice:
                                sound.play_voice(self.reel_voice)
                        else:
                            self._finish()

    def render(self, surface):
        if not self.active:
            return
        surface.fill(self.bg_color)
        if self.reel_phase:
            if self.reel is not None:
                self.reel.blit(surface)
            hint = fonts.render_small("[ENTER] skip", (110, 110, 110))
            surface.blit(hint, (SCREEN_W - hint.get_width() - 12, SCREEN_H - 26))
            return
        active = self._active_reel()
        if active is not None:
            active.blit(surface)
        text_y = SCREEN_H // 2 - 20
        portrait_img, portrait_label = self._current_speaker_portrait()
        if portrait_img:
            px = SCREEN_W // 2 - portrait_img.get_width() // 2
            py = 40
            surface.blit(portrait_img, (px, py))
            if portrait_label:
                lb = fonts.render(portrait_label, (200, 120, 50), big=True)
                surface.blit(lb, (SCREEN_W // 2 - lb.get_width() // 2, py + portrait_img.get_height() + 4))
            text_y = py + portrait_img.get_height() + 60
        full = self.char_index >= len(self._stripped[self.current])
        if full:
            ts = fonts.render_wrapped(self._shown_line(), (200, 200, 200), big=True,
                                      max_width=SCREEN_W - 120)
        else:
            ts = fonts.render(self._shown_line(), (200, 200, 200), big=True)
        surface.blit(ts, (SCREEN_W // 2 - ts.get_width() // 2, text_y))
        if full:
            hint = fonts.render_small("[ENTER]", (100, 100, 100))
            surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2,
                                text_y + ts.get_height() + 10))


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
        self.combat.ambient = sound
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
                          objective="AZRAEL: 'Get your bearings. Grab what's on the floor, talk to the Roadie, find the exit door.'",
                         objective_portrait="azrael")
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
            {"x": 6, "y": 5, "color": (240, 200, 60), "active": True,
             "name": "Bludgeon the Clown", "interact": "bludgeon"},
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
                         objective="AZRAEL: 'Search the Backstage. Bottle and drink first. That south door needs a DO-NOT-USE key.'",
                         objective_portrait="azrael")
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
             "locked_msg": "AZRAEL: 'A heavy rusted door. The lock is shaped for a key that insists it should never be used.'"},
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
                          objective="AZRAEL: 'Talk to the vendor, stock up. Mosh Pit's beyond the east door.'",
                         objective_portrait="azrael")
        room_merch.enemies = [
            {"x": 10, "y": 7, "type": "demon", "active": True, "hp": 70,
             "defense": 8, "interact": "merch_demon"},
        ]
        room_merch.npcs = [
            {"x": 3, "y": 7, "color": (150, 50, 150), "active": True,
             "name": "Sketchy Vendor", "interact": "vendor"},
            {"x": 16, "y": 4, "color": (240, 200, 60), "active": True,
             "name": "Bludgeon the Clown", "interact": "bludgeon"},
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
                        objective="AZRAEL: 'Slay the Enforcer to break the chains on the east gate.'",
                        objective_portrait="azrael")
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
             "locked_msg": "AZRAEL: 'A colossal iron gate, chained shut by the Enforcer's ego. Kill him and the chains pop like a champagne cork.'"},
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
                          objective="AZRAEL: 'VIP lounge. Talk to the Last Roadie. Loot the green room.'",
                          objective_portrait="azrael")
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
                            objective="AZRAEL: 'The Pit Lord. End the set. Escape. He drops no mercy.'",
                            objective_portrait="azrael")
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
                          objective="AZRAEL: 'The sound booth. Grab the fader, grab the tomes, break the mix.'",
                          objective_portrait="azrael")
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
                               "AZRAEL: 'The band is leveling up. Select a member and use the panel buttons - new noise, new rules.'",
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
                               "AZRAEL: 'GRIT is FULL, little singer. Press F to SCREAM - heal 40 HP for 20 sanity.'")
        if p.sanity < 30 and not self.story_flags.get("tut_sanity", False):
            self.tutorial_once("tut_sanity",
                               "AZRAEL: 'Your sanity is dropping. Low sanity flickers the world. Screaming costs sanity. Choose your noise.'")
        if not self.story_flags.get("tut_mthud", False) and self.player.kills >= 1:
            self.tutorial_once("tut_mthud",
                               "AZRAEL: 'Defeat enough enemies and GRIT floods in faster. Save your Scream for the encore that matters.'")

    def tutorial_combat_start(self):
        self.tutorial_once("tut_combat",
                           "AZRAEL: 'The stage darkens. Select a band member with the mouse, move and strike (each action spends AP), end your turn on SPACE. Keep the Core alive!'",
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
            "They call me AZRAEL D DESTROYER.",
            "I am the band's spirit. The screaming in the distortion.",
            "The cat who streaks in from range three and shreds whatever needs shredding.",
            "And tonight... I am also your narrator.",
            "Listen closely. The gig was going great.",
            "Three hundred bodies screaming the singer's name.",
            "Then the floor opened up like a swallowed pick.",
            "He fell. Down through the stage, into the abyss.",
            "This place runs on screams now. His crowd? They're the chorus.",
            "They're not screaming for an encore anymore. They're screaming for help.",
            "So here we are, Marduk. You, me, and a setlist written in blood.",
            "Fight to the Pit Lord, end the set, climb out through the trapdoor.",
            "And if you ever get stuck... ask. I see the whole venue from up here.",
            "Now go warm up the strings. The encore is going to be loud.",
        ], bg_color=(16, 4, 12), callback=self.after_intro,
            portrait="azrael", label="AZRAEL D DESTROYER",
            reel_breaks={3: "azrael_intro", 7: "fall"})

    def after_intro(self):
        self.state = GameState.PLAYING
        self._sync_room_music()
        self.show_room_objective()
        self.tutorial_once("tut_move",
                           "AZRAEL: 'Walk with WASD or the arrows, Marduk. Approach things and press SPACE/ENTER. I can't carry you - but I can point.'",
                           frames=360)

    def _sync_room_music(self):
        if self.current_room:
            slot = SoundManager.ROOM_SLOT.get(self.current_room.name)
            if slot:
                sound.play_ambient(slot, force=True)

    def generate_asset_manifest(self, path=None):
        path = path or os.path.join(ASSETS, "ASSET_MANIFEST.md")
        lines = [
            "# %s - Asset Manifest" % GAME_TITLE,
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
        rows["player"] = ("The protagonist (Marduk)", "menu, cutscenes, HUD banners")
        rows["azrael"] = ("AZRAEL D DESTROYER (narrator, hint-giver, ranged weapon)",
                          "introduction cutscene, battle appearances")
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
            lines.append(f"| {key} | {status} | {label} - {where} |")

        lines += ["", "## Music - key moments", "",
                  "Folder: `assets/music/`.  File: `<slot>.mp3` (or `.ogg` / `.wav`).",
                  "Numbered variants work too: `01-stage.mp3` is the same slot as `stage.mp3`.",
                  "Combat/boss tracks rotate through playlist files `combat1.mp3`, `combat2.mp3`, ...",
                  "and `boss1.mp3`, `boss2.mp3`, ... so each battle airs a different song.",
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
            "combat": "Any normal fight (battle playlist combat1/2/3...)",
            "zombie": "Zombie Fan pre-battle reel voice (room music stops; plays once)",
            "corpse": "Reanimated Roadie pre-battle reel voice (room music stops; plays once)",
            "shadow": "Stage Ninja pre-battle reel voice (room music stops; plays once)",
            "demon": "Enforcer (non-boss) pre-battle reel voice (room music stops; plays once)",
            "engineer": "Sound Engineer pre-battle reel voice (room music stops; plays once)",
            "boss": "Boss pre-battle reel voice (room music stops; plays once)",
            "levelup": "LEVEL UP banner (one-shot sting)",
            "discovery": "Unlocking a new ability tome (one-shot sting)",
            "victory": "Beast defeated (one-shot sting)",
            "ending": "Ending cutscene",
            "credits": "Credits roll",
        }
        def _playlist_files(kind):
            found = []
            if os.path.isdir(MUSIC_DIR):
                pat = re.compile(r"^%s(\d*)\.(mp3|ogg|wav)$" % kind, re.I)
                for f in sorted(os.listdir(MUSIC_DIR)):
                    if pat.match(f):
                        found.append(f)
            return found

        for slot in SoundManager.MUSIC_SLOTS:
            if slot in ("combat", "boss"):
                files = _playlist_files(slot)
                status = "+".join(sorted(files, key=lambda f: (int(re.sub(r"\D", "", f) or 0), f))) if files else "missing"
                lines.append(f"| {slot} | {slot}1.mp3, {slot}2.mp3, ... | {moment.get(slot, slot)} | {status} |")
            else:
                file_status = "found" if slot in sound.slots else "missing"
                lines.append(f"| {slot} | {slot}.mp3 | {moment.get(slot, slot)} | {file_status} |")

        lines += ["", "## Animations (short reels)", "",
                  "Folder: `assets/animations/<key>/`. Frames: `0001.png`, `0002.png`, ...",
                  "(any numbered name, sorted numerically), played one per engine tick at 30 FPS.",
                  "Exact 1024x768 frames recommended; portrait frames are cover-fitted (cropped",
                  "top/bottom) to fill the screen without distortion.",
                  "Moments with no frames fall back to a plain cutscene (the intro 'fall' and",
                  "'azrael_intro' beats use built-in procedural placeholder scenes so you can",
                  "see how they work before real art exists).",
                  "",
                  "| Key | Plays when | Frames found |", "|---|---|---|"]
        for key, when in REEL_MOMENTS.items():
            folder = os.path.join(ANIM_DIR, key)
            frames = 0
            if os.path.isdir(folder):
                for f in os.listdir(folder):
                    stem = os.path.splitext(f)[0]
                    if f.lower().endswith((".png", ".jpg", ".jpeg")) and stem.isdigit():
                        frames += 1
            if frames:
                status = "READY (%d frames)" % frames
            elif key in ("fall", "azrael_intro"):
                status = "NO FRAMES - procedural placeholder scene"
            else:
                status = "NO FRAMES - text-only"
            lines.append(f"| {key} | {when} | {status} |")

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
            "AZRAEL: 'The Pit Lord folds into the pit he came from. Kevin. Forever. Kevin.'",
            "AZRAEL: 'The lights come up. The PA crackles alive - like an old friend.'",
            "AZRAEL: 'Somewhere above, the trapdoor grinds open.'",
            "AZRAEL: 'You climb back onto the stage... and it feels real again.'",
            "AZRAEL: 'The crowd is gone. The blood is gone. His guitar is still in tune.'",
            "AZRAEL: 'He steps to the mic and screams the last verse of the set.'",
            "AZRAEL: 'I sat this one out. Some encores belong to the singer alone.'",
            "MARDUK: '...Azrael?'",
            "AZRAEL: 'I'll be up there. Shredding. As always.'",
            "AZRAEL: 'Somewhere in the void below, a demon applauds politely. You love to see it.'",
            "THE END",
            "...FOR NOW",
        ], bg_color=(0, 5, 0), callback=self.after_ending,
            reel_key="ending", reel_lines=(3, 9), reel_placeholder=False)

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
            elif event.key == pygame.K_i:
                self.tutorial_once("tut_inventory",
                                   "I opens your inventory. Press I or ESC to close it.")
                self.state = GameState.INVENTORY
            elif event.key == pygame.K_F5:
                self.save_game()
            elif event.key == pygame.K_h:
                self.tutorial_once("tut_help",
                                   "AZRAEL: 'H reopens my FIELD MANUAL anytime - controls and mechanics. Study it. I like a prepared singer.'")
                self.state = GameState.HELP
            elif event.key == pygame.K_f:
                self.use_scream()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.interact_forward()

    def use_scream(self):
        if not self.player.can_scream():
            self.dialogue.start(["AZRAEL: 'Little singer. The scream isn't ready. Keep hitting things.'",
                                 "AZRAEL: 'Build GRIT - land hits, take hits. Then we roar.'"],
                                "AZRAEL", (255, 190, 80))
            return
        self.player.spend_grit()
        restored = self.player.scream_heal(40)
        self.player.sanity = max(0, self.player.sanity - 20)
        if restored > 0:
            sound.play_sfx("heal")
            self.dialogue.start(["AZRAEL: 'THERE it is. The scream that moves the air.'",
                                 "MARDUK: 'AAAAARGH!'",
                                 f"+{restored} HP. Your chords are wrecked... SANITY -20"],
                                "AZRAEL", (255, 190, 80))
        else:
            self.dialogue.start(["AZRAEL: 'A magnificent roar. Shame nothing was bleeding.'",
                                 "AZRAEL: 'Waste of a good growl. SANITY -20'"],
                                "AZRAEL", (255, 190, 80))

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
                               "AZRAEL: 'You grabbed it! SPACE when the cue glows. I'd say meow, but the cue works better.'",
                               frames=240)
        elif kind == "npc":
            self.interact_npc(target)
            self.tutorial_once("tut_npc",
                               "AZRAEL: 'You talked to a soul. Pick with UP/DOWN and SPACE, little singer.'",
                               frames=240)
        elif kind == "enemy":
            self._engage_enemy(target)
        elif kind == "door":
            locked_reason = self.door_locked_reason(target)
            if locked_reason:
                self.dialogue.start([locked_reason], "AZRAEL", (255, 190, 80))
                return
            dest = target["target"]
            if dest in self.room_map:
                sound.play_sfx("door")
                cb = None
                if dest == "The Pit Lord's Chamber" and not self.story_flags.get("chamber_seen", False):
                    cb = self.after_chamber_transition
                self.transition_to(dest, target.get("spawn_x", 2), target.get("spawn_y", 2),
                                   callback=cb)

    def _engage_enemy(self, target):
        if target.get("boss"):
            self._pending_battle = target
            key = "beast" if target["type"] == "beast" else "pit_lord"
            beat_lines = {
                "beast": [
                    "AZRAEL: 'There he is. The headliner. You've been booked as his opener.'",
                    "MARDUK: 'I didn't come here to open. I came to close the show.'",
                ],
                "pit_lord": [
                    "AZRAEL: 'The Enforcer steps onto the throne-room floor. He's the warm-up act. You're the encore.'",
                    "MARDUK: 'Warm-up's over.'",
                ],
            }
            lines = list(beat_lines[key])
            portrait_map = {
                "AZRAEL": ("azrael", "AZRAEL D DESTROYER"),
                "MARDUK": ("player", "MARDUK"),
            }
            boss_banter = battle_bridge.BANTER.get(target["type"], [])
            boss_name = CombatSystem.ENEMY_NAMES.get(target["type"], "the Pit Lord")
            if boss_banter:
                boss_line = boss_banter[0]
                boss_speaker = boss_line.split(":", 1)[0].upper()
                lines.insert(0, boss_line)
                portrait_map[boss_speaker] = (target["type"], boss_name)
            else:
                lines.insert(0, "THE PIT LORD: 'You think your noise scares me?'")
                portrait_map["THE PIT LORD"] = ("beast", boss_name)
            sound.stop_music()
            self.cutscene.start(lines, bg_color=(24, 2, 2),
                                callback=self._start_pending_battle,
                                reel_key=key, reel_placeholder=False,
                                reel_after=True, reel_voice="boss",
                                portrait_map=portrait_map)
            self.state = GameState.CUTSCENE
            return

        self._pending_battle = target
        enemy_name = CombatSystem.ENEMY_NAMES.get(target.get("type", ""), target.get("type", "").title())
        enemy_lines = battle_bridge.BANTER.get(target.get("type", ""), [])
        pre_battle_lines = {
            "zombie": [
                "AZRAEL: 'Zombie Fan. They paid for the front row and never went home.'",
                "MARDUK: 'Then unbook them. Loudly.'",
            ],
            "corpse": [
                "AZRAEL: 'The Reanimated Roadie. Still trying to fix the monitors in death.'",
                "MARDUK: 'I am the only monitor he needs to worry about.'",
            ],
            "shadow": [
                "AZRAEL: 'Stage Ninja. Believes the spotlight was stolen from him. It was.'",
                "MARDUK: 'And I just booked the replacement.'",
            ],
            "demon": [
                "AZRAEL: 'The Pit Lord sent an Enforcer to warm up the room for you.'",
                "MARDUK: 'Tell the Pit Lord I do my own warm-ups.'",
            ],
            "engineer": [
                "AZRAEL: 'The Sound Engineer. The mix was wrong. Your face was wrong. Everything was wrong.'",
                "MARDUK: 'Then let me remix him.'",
            ],
        }
        key = target.get("type", "")
        if key in pre_battle_lines and key in REEL_MOMENTS:
            lines = list(pre_battle_lines[key])
            portrait_map = {
                "AZRAEL": ("azrael", "AZRAEL D DESTROYER"),
                "MARDUK": ("player", "MARDUK"),
            }
            if enemy_lines:
                enemy_line = enemy_lines[0]
                enemy_speaker = enemy_line.split(":", 1)[0].upper()
                lines.insert(0, enemy_line)
                portrait_map[enemy_speaker] = (key, enemy_name)
            else:
                enemy_speaker = ("THE " + enemy_name).upper()
                lines.insert(0, f"{enemy_speaker}: 'You think you headline this stage?'")
                portrait_map[enemy_speaker] = (key, enemy_name)
            sound.stop_music()
            self.cutscene.start(lines, bg_color=(16, 4, 12),
                                callback=self._start_pending_battle,
                                reel_key=key, reel_placeholder=False,
                                reel_after=True, reel_voice=key,
                                portrait_map=portrait_map)
            self.state = GameState.CUTSCENE
            return
        self._pending_battle = None
        self._start_enemy_battle(target)

    def _start_pending_battle(self):
        self._start_enemy_battle(self._pending_battle)
        self._pending_battle = None

    def _start_enemy_battle(self, target):
        self.tutorial_combat_start()
        self.combat.start(target, self.player)

    def after_chamber_transition(self):
        self.story_flags["chamber_seen"] = True
        self.cutscene.start([
            "AZRAEL: 'The Chamber of the Pit Lord. His house lights. The throne room of the pit.'",
            "AZRAEL: 'Somewhere in the dark, the Beast is tuning up its setlist.'",
        ], bg_color=(18, 2, 2), callback=self.after_chamber_intro,
            reel_key="chamber", reel_lines=(0, 1), reel_placeholder=False)
        self.state = GameState.CUTSCENE

    def after_chamber_intro(self):
        self.state = GameState.PLAYING
        self.tutorial_once("tut_chamber",
                           "AZRAEL: 'This is the last room on the bill, little singer. The vial heals. The Beast does not.'",
                           frames=300)

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
            return "AZRAEL: 'A heavy gate. It opens when the Pit Lord's Enforcer stops existing. Theatrical, I know.'"
        if door.get("requires_item") and door["requires_item"] not in self.player.inventory:
            if door.get("locked_msg"):
                return door["locked_msg"]
            return "AZRAEL: 'Locked. It wants a specific, oddly-labeled key. You know the one.'"
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
            self.show_help("AZRAEL: 'Enforcer's headlining the pit now. The gate to the Chamber swings open - chains and all.'",
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
                "MARDUK: 'Warm beer. You've got to be kidding me.'",
                "AZRAEL: 'Down here, warm means ALIVE. Drink it, little singer.'",
                "AZRAEL: 'It won't close the wounds. It just makes them feel like art.'",
                "HP +15, SANITY -5"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "mic":
            self.player.inventory.append("mic")
            self.player.attack += 3
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'A microphone. Heavy. Real metal.'",
                "AZRAEL: 'The last singer's fingerprints are still melted into the grip.'",
                "MARDUK: 'And the walls?'",
                "AZRAEL: 'Separately. Moving on.'",
                "ATTACK +3"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "crypt_key":
            self.player.inventory.append("crypt_key")
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'A key with a tag that reads DO NOT USE.'",
                "MARDUK: '...'",
                "AZRAEL: 'Yes. Pocket it. I knew we'd get along.'",
            ], "AZRAEL", (255, 190, 80))

        elif ix == "broken_bottle":
            self.player.inventory.append("broken_bottle")
            self.player.attack += 8
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'A broken bottle. The signature weapon of every punk show you've ever played.'",
                "AZRAEL: 'Hold it low, hold it right. It has one good show in it.'",
                "ATTACK +8"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "energy_drink":
            self.player.hp = min(self.player.max_hp, self.player.hp + 25)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "AZRAEL: 'An energy drink labeled PAIN. It is exactly what it claims.'",
                "MARDUK: 'Cheers.'",
                "AZRAEL: 'He drinks it anyway. Of course he does. It tastes like regret and taurine.'",
                "HP +25"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "blood_puddle":
            self.dialogue.start([
                "AZRAEL: 'A puddle of blood. Whose? At a metal show - everyone's.'",
                "MARDUK: 'M. For the wall. Branding.'",
                "AZRAEL: 'He writes his initial in someone else's blood. Stay metal, my friend.'",
            ], "AZRAEL", (255, 190, 80))

        elif ix == "mysterious_lager":
            self.player.hp = min(self.player.max_hp, self.player.hp + 10)
            self.player.attack += 5
            self.player.sanity -= 10
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'The label is in a language even I don't purr in.'",
                "MARDUK: 'Tastes like lightning and poor decisions.'",
                "AZRAEL: 'He's not wrong.'",
                "HP +10, ATTACK +5, SANITY -10"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "merch_bloody_rag":
            self.player.hp = min(self.player.max_hp, self.player.hp + 20)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "AZRAEL: 'A rag. Bloody. Medicinal. Go on.'",
                "AZRAEL: 'Hygiene left the building several lifetimes ago.'",
                "HP +20"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "guitaraxe":
            self.player.inventory.append("guitaraxe")
            self.player.attack += 15
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'A guitar shaped like an axe. The universe finally stops teasing.'",
                "AZRAEL: 'Tuned to Drop Z. The strings hum with malice.'",
                "MARDUK: 'The most metal thing I've ever held.'",
                "AZRAEL: 'You say that now, little singer.'",
                "ATTACK +15"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "mixer_fader":
            self.player.inventory.append("mixer_fader")
            self.player.attack += 12
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'The master fader, ripped clean from the sound board.'",
                "AZRAEL: 'Steel. Sharp. The label reads MASTER.'",
                "MARDUK: 'The first swing felt like a chord change.'",
                "AZRAEL: 'The feedback peaks. Perfect.'",
                "ATTACK +12"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "pit_mystery_vial":
            self.player.hp = self.player.max_hp
            self.player.sanity = max(0, self.player.sanity - 20)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "AZRAEL: 'A vial of unknown fluid. Do not - he's drinking it.'",
                "MARDUK: 'Nghhh.'",
                "AZRAEL: 'Wounds close. Vision goes red, then purple.'",
                "MARDUK: 'Tastes like copper.'",
                "AZRAEL: 'He feels... complete. Terrifying.'",
                "FULL HP RESTORED, SANITY -20"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "vip_broken_lamp":
            self.player.inventory.append("vip_lamp")
            self.player.attack += 10
            item["active"] = False
            sound.play_sfx("pickup")
            self.dialogue.start([
                "AZRAEL: 'A stage lamp cracked off its rig.'",
                "AZRAEL: 'Glass. Tungsten. The souls of a thousand burned-out bulbs.'",
                "MARDUK: 'It hums like feedback.'",
                "AZRAEL: 'Perfect.'",
                "ATTACK +10"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "vip_energy_drink":
            self.player.hp = min(self.player.max_hp, self.player.hp + 30)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "AZRAEL: 'Unlabeled. Duct-taped shut. The VIP rider said VOMIT - somebody honored it literally.'",
                "MARDUK: 'Whatever. It tastes like the encore.'",
                "AZRAEL: 'The encore is 30 hit points, apparently.'",
                "HP +30"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "vip_blood":
            self.player.sanity = max(0, self.player.sanity - 8)
            self.dialogue.start([
                "AZRAEL: 'Blood on the green-room couch. Someone famous, probably.'",
                "MARDUK: 'Handprint. For the wall.'",
                "AZRAEL: 'He leaves a mark and keeps walking. On brand.'",
                "SANITY -8"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "chamber_vial":
            self.player.hp = self.player.max_hp
            self.player.sanity = max(0, self.player.sanity + 15)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "AZRAEL: 'Pit Lord blood. It glows faintly crimson.'",
                "MARDUK: 'To the headline slot.'",
                "AZRAEL: 'Mind clears. Body screams MORE.'",
                "FULL HP RESTORED, SANITY +15"
            ], "AZRAEL", (255, 190, 80))

        elif ix == "tome_power_chord":
            item["active"] = False
            sound.play_sfx("pickup")
            if self.player.unlock_skill("power_chord"):
                sound.jingle("discovery")
                self.dialogue.start([
                    "AZRAEL: 'A torn setlist scrawled in crayon. The riffs are written in blood.'",
                    "AZRAEL: 'Study it, Marduk. The first note splits the air.'",
                    "New ability unlocked: POWER CHORD (1.6x damage, costs 30 GRIT)"
                ], "AZRAEL", (255, 190, 80))
                self.tutorial_once("tut_skills",
                                   "AZRAEL: 'The band is leveling up. Select a member and use the panel buttons - new noise, new rules.'")
            else:
                self.dialogue.start([
                    "AZRAEL: 'You know this riff already. The setlist crumbles to ash.'"
                ], "AZRAEL", (255, 190, 80))

        elif ix == "tome_double_down":
            item["active"] = False
            sound.play_sfx("pickup")
            if self.player.unlock_skill("double_down"):
                sound.jingle("discovery")
                self.dialogue.start([
                    "AZRAEL: 'A cursed vinyl etched with anger. Every groove is a scream.'",
                    "AZRAEL: 'He listens until the anger becomes his. That's the deal.'",
                    "New ability unlocked: DOUBLE DOWN (2.0x damage, costs 12 SANITY)"
                ], "AZRAEL", (255, 190, 80))
                self.tutorial_once("tut_skills",
                                   "AZRAEL: 'The band is leveling up. Select a member and use the panel buttons - new noise, new rules.'")
            else:
                self.dialogue.start([
                    "AZRAEL: 'Already internalized. The vinyl melts from sheer recognition.'"
                ], "AZRAEL", (255, 190, 80))

        elif ix == "tome_feedback_howl":
            item["active"] = False
            sound.play_sfx("pickup")
            if self.player.unlock_skill("feedback_howl"):
                sound.jingle("discovery")
                self.dialogue.start([
                    "AZRAEL: 'A rusted pedal marked DO NOT STEP.'",
                    "MARDUK: 'I'm stepping on it.'",
                    "AZRAEL: 'Of course you are.'",
                    "New ability unlocked: FEEDBACK HOWL (2.5x damage, costs 55 GRIT)"
                ], "AZRAEL", (255, 190, 80))
                self.tutorial_once("tut_skills",
                                   "AZRAEL: 'The band is leveling up. Select a member and use the panel buttons - new noise, new rules.'")
            else:
                self.dialogue.start([
                    "AZRAEL: 'The pedal screams the old song. You've got this one.'"
                ], "AZRAEL", (255, 190, 80))

        elif ix == "booth_earplugs":
            self.player.sanity = min(100, self.player.sanity + 15)
            item["active"] = False
            sound.play_sfx("heal")
            self.dialogue.start([
                "AZRAEL: 'Earplugs. Label reads FOR INTERNAL USE ONLY.'",
                "MARDUK: '...'",
                "AZRAEL: 'He's wearing them. I've never been prouder of a human.'",
                "SANITY +15"
            ], "AZRAEL", (255, 190, 80))

        else:
            self.dialogue.start(["AZRAEL: 'Nothing useful here, little singer. Keep moving.'"])
        self.dialogue.set_default_portrait(None)

    def interact_npc(self, npc):
        name = npc.get("name", "")
        if name == "Roadie":
            if not self.story_flags.get("roadie_talked"):
                self.story_flags["roadie_talked"] = True
                self.dialogue.start_choice(
                    "Roadie",
                    "AZRAEL: 'A survivor. The roadie lives - small miracles. Listen.' ROADIE: 'Bro. The acoustics down here are UNREAL. But also everything is trying to kill us. The vendor through backstage... he's got the good stuff. And the bad stuff. And the stuff that makes you see God.'",
                    ["'Where's the exit?'", "'What happened to the band?'", "'You got any gear?'"],
                    self._roadie_choice, (230, 90, 90))
            else:
                self.dialogue.start([
                    "AZRAEL: 'The roadie again. His lines never change. Reliability.'",
                    "'The stage is up north. Backstage leads deeper in.'",
                    "'Also, the drummer's holding it down backstage. Says he'll sit in once the set proves it.'"
], "Roadie", (230, 90, 90))
        elif name == "Sketchy Vendor":
            if not self.story_flags.get("vendor_talked"):
                self.story_flags["vendor_talked"] = True
                self.dialogue.start_choice(
                    "Sketchy Vendor",
                    "AZRAEL: 'A vendor in hell. Cursed, probably. Worth the conversation.' VENDOR: 'Welcome to the merch table! We got shirts, patches, and things that were alive ten minutes ago! What can I do for ya?'",
                    ["'What are you selling?'", "'Are you human?'", "'Weirdest item.'"],
                    self._vendor_choice, (215, 95, 215))
            else:
                grit = int(self.player.grit)
                self.dialogue.start_choice(
                    "Sketchy Vendor",
                    f"AZRAEL: 'Commerce waits for no cat.' VENDOR: 'Back so soon? You have {grit} GRIT. That's currency down here. Spend it or keep screaming.' Pick an upgrade:",
                    ["Max HP +10 (25 GRIT)", "Attack +3 (30 GRIT)", "Defense +1 (20 GRIT)", "Not today. I'm saving it."],
                    self._vendor_upgrade_choice, (215, 95, 215))

        elif name == "Last Roadie":
            if not self.story_flags.get("last_roadie_talked"):
                self.story_flags["last_roadie_talked"] = True
                self.player.hp = min(self.player.max_hp, self.player.hp + 20)
                self.dialogue.start([
                    "AZRAEL: 'A VIP lounge. The last honest roadie in the abyss.'",
                    "'Hey. You made it to the VIP room. Real ones come here.'",
                    "'The Pit Lord's real name is Kevin. He's insecure about it.'",
                    "'Hit him in the ego. That's the only weak spot he's got.'",
                    "'Also I patched you up. You're welcome.'",
                    "HP +20 (bandage courtesy of the Last Roadie)"
                ], "Last Roadie", (110, 230, 110))
            else:
                self.dialogue.start([
                    "AZRAEL: 'More intel on Kevin. It never stops being funny.'",
                    "'Kevin's got horns, big teeth, and a terrible sense of humor.'",
                    "'Knock him into the pit. That's how you close a set.'"
                ], "Last Roadie", (110, 230, 110))

        elif name == "Bludgeon the Clown":
            talks = self.story_flags.get("bludgeon_talked", 0) + 1
            self.story_flags["bludgeon_talked"] = talks
            if self.story_flags.get("pit_lord_defeated"):
                self.dialogue.start([
                    "BLUDGEON THE CLOWN: 'The Enforcer is GONE?! That was my warm-up crowd, headliner! Do you know how expensive RED is on this merch table?!'",
                    "BLUDGEON THE CLOWN: 'Fine. FINE. The Beast headlines next. When you drop him I'll print the commemorative shirts MYSELF. With my OWN bits. You'll buy four.'"
                ], "Bludgeon the Clown", (240, 200, 60))
            elif talks == 1:
                self.dialogue.start([
                    "AZRAEL: 'The band's blood-and-confetti promoter. Marduk doesn't pay him so much as keep him breathing - he calls it marketing synergy with a blackmail garnish. His words.'",
                    "BLUDGEON THE CLOWN: 'GOOD EVENING, SCREAMERS! I am BLUDGEON THE CLOWN! Undead, unhinged, and UNBOUGHT! Well - blackmailed. SEMANTICS! Marduk keeps the corpse warm and I keep the crowds HYPED!'",
                    "BLUDGEON THE CLOWN: 'Every show I crawl out in full getup for the support gig - hoarse from screaming my own name before the proper act. The crowd thinks I'm the warm-up. I'm the WARNING LABEL.'",
                    "BLUDGEON THE CLOWN: 'Tonight you headline alongside me. Out-destroy me, little singer. And TRY the merch! I'm on ALL the shirts. Nobody asks for a refund twice!'"
                ], "Bludgeon the Clown", (240, 200, 60))
            else:
                self.dialogue.start([
                    "BLUDGEON THE CLOWN: 'Back for more of the brand, are we? Excellent! The shirts are printed in premium abyss-grade gore now. VERY limited edition. VERY. LIMITED.'",
                    "BLUDGEON THE CLOWN: 'A fan BIT my nose for luck back in the green room. Third time this tour. I call it POSITIVE ENGAGEMENT - the crowd REMEMBERS the clown.'",
                    "AZRAEL: 'Statistically he gets heavier every show. Theatrically? A miracle. Stay near the vendor, little singer.'"
                ], "Bludgeon the Clown", (240, 200, 60))

    def _vendor_upgrade_choice(self, choice):
        costs = [25, 30, 20]
        if choice == 3:
            self.dialogue.start([
                "AZRAEL: 'Keeping the grit. A disciplined little singer.'",
                "'Smart. Hoard your grit. When the moment comes, spend it on something that hurts.'"
            ], "Sketchy Vendor", (215, 95, 215))
            return
        cost = costs[choice]
        if self.player.grit < cost:
            self.dialogue.start([
                f"AZRAEL: 'Not enough GRIT. Busy mosh, then spend.' VENDOR: 'That's {cost} GRIT. You've got {int(self.player.grit)}. Go mosh, then come back.'"
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
            "AZRAEL: 'He twists something under the table. Some deals write themselves.'",
            f"'Deal.' He twists something under the table. You feel {stat}.",
            "Your bones rattle in a way that suggests improvement.",
            f"{stat}. Spend wisely, or scream harder."
        ], "Sketchy Vendor", (215, 95, 215))
        self.tutorial_once("tut_vendor_upgrade",
                           "AZRAEL: 'The vendor upgrades bodies for GRIT. GRIT fills as you fight - budget for the Scream.'",
                           frames=300)

    def _roadie_choice(self, choice):
        if choice == 0:
            self.dialogue.start([
                "AZRAEL: 'The exit. He asked. Let him dream.'",
                "'Exit? EXIT? Brother, the only exit is through the Pit.'",
                "'The Pit Lord guards the way out. Big fella. Red. Likes to talk.'",
                "'Pro tip: don't let him talk. He's very persuasive.'"
            ], "Roadie", (230, 90, 90))
        elif choice == 1:
            self.dialogue.start([
                "AZRAEL: 'The story of the band. I could tell it better - but hear the roadie.'",
                "'The band? Oh man... they're still playing.'",
                "'The guitarist is headlining the third circle now.'",
                "'Bass player went full method. Became the monster.'",
                "'Drummer's back there, keeping time to the void. He'll find us when it counts.'"
            ], "Roadie", (230, 90, 90))
        elif choice == 2:
            self.player.sanity -= 5
            self.dialogue.start([
                "AZRAEL: 'Marduk asks a roadie for gear at the gates of hell. Priorities.'",
                "'Take this.' He hands you a pair of earplugs.",
                "'Won't stop the demons. But it'll muffle their screaming.'",
                "SANITY -5"
            ], "Roadie", (230, 90, 90))

    def _vendor_choice(self, choice):
        if choice == 0:
            self.dialogue.start([
                "AZRAEL: 'Merch. In hell. Of course.'",
                "'We got the usual: suffering, existential dread, regret.'",
                "'Oh, and t-shirts. The shirts are made of... let's call it leather.'",
                "'Don't ask what kind of leather.'"
            ], "Sketchy Vendor", (215, 95, 215))
        elif choice == 1:
            self.dialogue.start([
                "AZRAEL: 'He asks the demon if it is human. Bold. I respect the audacity.'",
                "'Human? Friend, nobody down here is human anymore.'",
                "'I used to sell bootleg CDs in a parking lot.'",
                "'Now I sell bootleg CDs in hell. Same job, different tax bracket.'"
            ], "Sketchy Vendor", (215, 95, 215))
        elif choice == 2:
            self.player.sanity -= 10
            self.player.attack += 5
            self.dialogue.start([
                "AZRAEL: 'Weirdest item. Oh, this is going to be good.'",
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

        title = fonts.render_title(GAME_TITLE, (200, 0, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))
        band = fonts.render_band("BELLIGERENT DICKHEAD", (200, 50, 50))
        screen.blit(band, (SCREEN_W // 2 - band.get_width() // 2, 160))
        sub = fonts.render_small("present the debut album - LIVE from the abyss", (120, 40, 40))
        screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 210))
        sub2 = fonts.render_small("narrated by AZRAEL D DESTROYER", (120, 70, 50))
        screen.blit(sub2, (SCREEN_W // 2 - sub2.get_width() // 2, 226))

        options = ["New Game", "Load Game", "Credits", "Quit"]
        for i, opt in enumerate(options):
            c = (255, 50, 50) if i == self.menu_select else (120, 60, 60)
            prefix = "> " if i == self.menu_select else "  "
            ot = fonts.render(prefix + opt, c, big=True)
            screen.blit(ot, (SCREEN_W // 2 - ot.get_width() // 2, 300 + i * 50))

        hints = [
            "WASD: Move | SPACE/ENTER: Interact | I: Inventory | H: Help | F: Scream (Heal when GRIT full) | F11: Fullscreen",
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
            at = fonts.render_wrapped(self.track_announcement, (200, 200, 200),
                                      max_width=SCREEN_W - 160)
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
            rt = fonts.render_wrapped(reveal, (255, 220, 150), max_width=500)
            r = pygame.Rect(SCREEN_W // 2 - 260, 150, 520, rt.get_height() + 24)
            panel = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            panel.fill((15, 10, 5, 235))
            pygame.draw.rect(panel, (200, 120, 40), panel.get_rect(), 2)
            panel.blit(rt, (10, 12))
            screen.blit(panel, r.topleft)
            if self.objective_banner_portrait:
                screen.blit(self.objective_banner_portrait, (r.x + r.width + 10, r.y + r.height - 160))
            if r.collidepoint(pygame.mouse.get_pos()):
                pass

        # Help banner (one-time tips)
        if self.help_banner and self.help_banner_timer > 0:
            hb = fonts.render_wrapped(self.help_banner, (255, 220, 50),
                                      max_width=SCREEN_W - 80)
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

    def render_help(self):
        screen.fill((12, 8, 8))
        hl = fonts.render("AZRAEL D DESTROYER'S FIELD MANUAL", (240, 130, 90), big=True)
        screen.blit(hl, (SCREEN_W // 2 - hl.get_width() // 2, 22))

        def title(txt):
            screen.blit(fonts.render_small(txt, (160, 140, 190)), (28, y[0]))
            y[0] += 24

        def row(txt):
            screen.blit(fonts.render_small(txt, (205, 205, 205)), (44, y[0]))
            y[0] += 20

        y = [70]
        title("WORLD CONTROLS")
        for t in [
            "WASD / Arrows ............ Move",
            "SPACE / ENTER ............. Interact / talk / advance dialogue",
            "I ......................... Inventory",
            "F ......................... Scream (heal when GRIT is full)",
            "H ......................... This help screen",
            "M ......................... Mute audio",
            "F5 ........................ Save game",
            "F11 ....................... Toggle fullscreen",
            "ESC ....................... Back to menu",
        ]:
            row(t)
        y[0] += 6

        title("BATTLE CONTROLS")
        for t in [
            "Mouse ..................... Select a band member, click a foe to attack",
            "Panel buttons ............. END TURN / UNDO / BUILD TOWER / HIRE GROUPIE",
            "ESC ....................... Pause",
            "R ......................... Restart the current battle",
            "Q ......................... Retreat from the battle (no reward)",
            "ENTER .................... Confirm when a battle ends",
        ]:
            row(t)
        y[0] += 6

        title("BATTLE MECHANICS")
        for t in [
            "Move = 1 AP per tile | melee = 3 AP | ranged = 4 AP",
            "Hold the Stage (core) until all 4 waves fall",
            "GRIT: start 60, +8 per kill, +40 + wave*20 per wave cleared",
            "Watchtower = 45 GRIT (2 turns to build, then auto-fires at",
            "  every enemy within range 4 each round)",
            "Groupie = 20 GRIT from the Support Van (max 6 at once)",
            "Band XP is shared: need 30 + (level-1)*26 to level up",
            "Frontman skills: SCREAM (5 AP) at level 2, BLITZ (5 AP) at level 4",
            "Boss battles are a single powerful enemy - win for big rewards",
        ]:
            row(t)
        y[0] += 6

        title("RPG MECHANICS")
        for t in [
            "Every battle win grants XP, kills, and +25 GRIT",
            "Level ups heal fully and raise HP/ATK/DEF",
            "GRIT also buys vendor upgrades: MaxHP+10 (25G), ATK+3 (30G), DEF+1 (20G)",
            "Screaming costs sanity; low sanity makes the world flicker",
            "Some doors need a key item or a defeated boss",
            "Check the objective banner (top center) for what to do next",
        ]:
            row(t)

        screen.blit(fonts.render_small("Press H, I, or ESC to close", (80, 40, 40)),
                    (SCREEN_W // 2 - 115, SCREEN_H - 30))

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
        lines = [(GAME_TITLE, fonts.render_title, (200, 0, 0)),
                 ("", None, None),
                 ("A BELLIGERENT DICKHEAD Production", fonts.render_band, (200, 50, 50)),
                 ("", None, None),
                 ("Featured Singer: Marduk Gault", fonts.render, (150, 100, 100)),
                 ("Music: Marduk Gault", fonts.render, (150, 100, 100)),
                 ("Concept: Marduk Gault", fonts.render, (150, 100, 100)),
                 ("Narration: AZRAEL D DESTROYER", fonts.render, (150, 100, 100)),
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
        elif self.state == GameState.HELP:
            self.render_help()
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
                    game.tutorial_once("tut_fullscreen",
                                       "F11 toggles fullscreen. F11 again to go back to windowed.")
                elif event.key == pygame.K_ESCAPE:
                    if not game.combat.active and game.state == GameState.PLAYING:
                        game.state = GameState.MENU
                        sound.play_menu_music()
                    elif not game.combat.active and game.state == GameState.INVENTORY:
                        game.state = GameState.PLAYING
                    elif not game.combat.active and game.state == GameState.HELP:
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
            elif game.state == GameState.HELP:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_h, pygame.K_ESCAPE, pygame.K_i):
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
