import random

import pygame

import rts_demo as rd

XP_BASE = {
    "zombie": 18,
    "corpse": 14,
    "shadow": 22,
    "demon": 45,
    "engineer": 30,
    "beast": 150,
}

BANTER = {
    "zombie": [
        "Zombie Fan: 'I still have your setlist, dude... it's... the only thing... I ever loved...'",
        "Zombie Fan: 'The mosh pit... never ends... down here...'",
    ],
    "corpse": [
        "Reanimated Roadie: 'Even roadies die... but the tour... continues...'",
        "Reanimated Roadie: 'I just wanted... to fix the monitors... why... why...'",
    ],
    "shadow": [
        "Stage Ninja: 'Your stage presence... is misplaced. It belongs to me now.'",
        "Stage Ninja: 'In the dark of the wings, I am the only real performer.'",
    ],
    "demon": [
        "Pit Lord's Enforcer: 'The Beast has evolved the setlist. You're opening for oblivion.'",
        "Pit Lord's Enforcer: 'I'll show you a breakdown.'",
    ],
    "engineer": [
        "Sound Engineer: 'THE MIX IS WRONG. YOUR FACE IS WRONG. EVERYTHING IS WRONG.'",
        "Sound Engineer: 'You hear that feedback? That's my soul. Still ringing.'",
    ],
    "beast": [
        "PIT LORD: 'Little singer. You think your noise scares me?'",
        "PIT LORD: 'Your band. Your crowd. Your soul. All booked. All mine.'",
    ],
}

RETORT = [
    "Marduk: 'You should've stayed a one-hit wonder.'",
    "Marduk: 'My dog plays better than you, and he's a corpse too.'",
    "Marduk: 'Let me autograph your face. Real close. With my boot.'",
    "AZRAEL: 'Careful, little singer. You're about to make him feel something.'",
    "AZRAEL: 'That's my boy. Wrong, but passionate.'",
    "AZRAEL: 'I'd narrate his funeral, but I'm saving the good lines for the Pit Lord.'",
]

VICTORY_LINES = {
    "zombie": ["That's a review you won't recover from.", "Rest in pieces, groupie.",
               "AZRAEL: 'Groupie down. The venue's cleaner already.'"],
    "corpse": ["Next time, keep the monitors level with the living.", "Load-out's over, buddy.",
               "AZRAEL: 'Monitors fixed. Permanently.'"],
    "shadow": ["Looks like the lights found you after all.", "Nope, still the loudest thing here.",
               "AZRAEL: 'The spotlight belongs to us now.'"],
    "demon": ["Your breakdown was mid. Mine's a knockout.", "Tell the Beast I want my own merch table.",
              "AZRAEL: 'The Beast's opener just got replaced. Leave the flyers.'"],
    "engineer": ["Check the meters now. Flatlining.", "Rest of the board and board of rest.",
                 "AZRAEL: 'I'd remix his screams, but the levels are finally right.'"],
    "beast": ["The noise won. Souls stay. Set's over.", "I'll handle the encore. You handle the pit.",
              "AZRAEL: 'Headline slot secured. I'll take the merch cut.'"],
}


def _pick_victory_line(enemy_type):
    pool = VICTORY_LINES.get(enemy_type)
    import random
    return random.choice(pool or ["And that's the encore."])


class BattleBridge:
    is_bridge = True

    def __init__(self, surface):
        self.surface = surface
        self.battle_surf = pygame.Surface((rd.SCREEN_W, rd.SCREEN_H))
        self.demo = rd.Demo(self.battle_surf, autostart_music=False)
        self.active = False
        self.resolved = False
        self.result = None
        self.enemy = None
        self.player_ref = None
        self.xp_gained = 0
        self.leveled_up = False
        self.skills_gained = []
        self.player_turn = False
        self.options = []
        self.boss = False
        self.kills_on_win = 0
        self.victory_line = ""

    def start(self, enemy, player_ref):
        self.enemy = enemy
        self.player_ref = player_ref
        self.resolved = False
        self.result = None
        self.xp_gained = 0
        self.leveled_up = False
        self.skills_gained = []
        self.boss = bool(enemy.get("boss"))
        self.victory_line = ""

        self.demo.reset()
        self.demo.state = rd.STATE_PLAY
        self.demo.level = max(1, player_ref.level)
        self.demo.grit = rd.START_GRIT + player_ref.grit // 2
        if self.boss:
            self.kills_on_win = 1
            self._seed_boss(enemy)
        else:
            self.kills_on_win = sum(len(w) for w in rd.WAVES)
        fm = next((u for u in self.demo.player_units() if u["kind"] == "frontman"), None)
        if fm is not None:
            fm["atk"] = player_ref.attack
            fm["rng_atk"] = player_ref.attack
        for line in BANTER.get(enemy.get("type"), []):
            self.demo.log(line)
            break
        self.demo.log(random.choice(RETORT))
        if not self.boss:
            self.demo.banner = "CLICK A BAND MEMBER TO SELECT THEM"
            self.demo.banner_t = 3.0
        self.active = True

    def _seed_boss(self, enemy):
        for e in list(self.demo.enemy_units()):
            self.demo.units.remove(e)
        self.demo.wave = 4
        px, py = self.demo.ports[0]
        self.demo._add_unit("enforcer", px, py)
        boss = self.demo.units[-1]
        hp = max(80, enemy.get("hp", 150))
        boss["hp"] = hp
        boss["max_hp"] = hp
        boss["atk"] = 8 + enemy.get("defense", 5)
        if enemy.get("type") == "beast":
            boss["name"] = "THE PIT LORD"
            self.demo.log("AZRAEL: 'The headliner descends. Don't get a review written in your ribs, Marduk.'")
            self.demo.banner = "THE PIT LORD"
        else:
            boss["name"] = "PIT LORD'S ENFORCER"
            self.demo.log("AZRAEL: 'Enforcer incoming. He's the warm-up act. You're the encore.'")
            self.demo.banner = "PIT LORD'S ENFORCER"
        self.demo.banner_t = 3.0
        self.demo.music.combat_loop(4, boss=True)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.demo.state != rd.STATE_TITLE:
            self.start(self.enemy, self.player_ref)
            return
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_q
                and self.demo.state != rd.STATE_TITLE and not self.resolved):
            self.retreat()
            return
        self.demo.handle_event(event)

    def retreat(self):
        self.demo.log("AZRAEL: 'And so the singer leaves the stage today. A cliffhanger the roadies will gossip about for decades.'")
        self.result = "flee"
        self.resolved = True
        pygame.mixer.music.stop()

    def update(self, player_ref):
        self.player_ref = player_ref
        if self.resolved:
            return
        self.demo.update(self.demo.clock.tick(rd.FPS) / 1000.0)
        if self.demo.state == rd.STATE_WON and not self.resolved:
            self._apply_win(player_ref)
        elif self.demo.state == rd.STATE_LOST and not self.resolved:
            self._apply_lose()

    def _apply_win(self, player_ref):
        player_ref.add_grit(25)
        player_ref.kills += self.kills_on_win
        self.xp_gained = XP_BASE.get(self.enemy.get("type"), 15) + self.kills_on_win + self.demo.level * 3
        self.leveled_up, self.skills_gained = player_ref.add_xp(self.xp_gained)
        self.victory_line = _pick_victory_line(self.enemy.get("type"))
        self.result = "win"
        self.resolved = True
        pygame.mixer.music.stop()

    def _apply_lose(self):
        self.result = "lose"
        self.resolved = True
        pygame.mixer.music.stop()

    def render(self, surface, player_ref):
        self.demo.render()
        surface.blit(self.battle_surf, (0, 0))
        if self.resolved:
            dim = pygame.Surface((rd.SCREEN_W, rd.SCREEN_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            surface.blit(dim, (0, 0))
            big = pygame.font.SysFont("consolas", 40)
            sm = pygame.font.SysFont("consolas", 18)
            if self.result == "win":
                top = big.render("THE STAGE HOLDS", True, (255, 220, 90))
                line = sm.render(self.victory_line, True, (255, 200, 120))
                sub = sm.render("XP +%d   GRIT +25   KILLS +%d   [ENTER]"
                                % (self.xp_gained, self.kills_on_win), True, (200, 200, 200))
            elif self.result == "flee":
                top = big.render("BATTLE ABANDONED", True, (220, 200, 100))
                line = None
                sub = sm.render("[ENTER]", True, (200, 200, 200))
            else:
                top = big.render("THE STAGE FALLS", True, (220, 60, 60))
                line = None
                sub = sm.render("[ENTER]", True, (200, 200, 200))
            surface.blit(top, (rd.SCREEN_W // 2 - top.get_width() // 2, 290))
            if line is not None:
                surface.blit(line, (rd.SCREEN_W // 2 - line.get_width() // 2, 345))
            surface.blit(sub, (rd.SCREEN_W // 2 - sub.get_width() // 2, 375))