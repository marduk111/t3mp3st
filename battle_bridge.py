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

    def start(self, enemy, player_ref):
        self.enemy = enemy
        self.player_ref = player_ref
        self.resolved = False
        self.result = None
        self.xp_gained = 0
        self.leveled_up = False
        self.skills_gained = []
        self.boss = bool(enemy.get("boss"))

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
            self.demo.log("THE PIT LORD descends on the stage.")
            self.demo.banner = "THE PIT LORD"
        else:
            self.demo.log("PIT LORD'S ENFORCER descends on the stage.")
            self.demo.banner = "PIT LORD'S ENFORCER"
        self.demo.banner_t = 3.0
        self.demo.music.combat_loop(4, boss=True)

    def handle_event(self, event):
        self.demo.handle_event(event)

    def update(self, player_ref):
        self.player_ref = player_ref
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
                sub = sm.render("XP +%d   GRIT +25   KILLS +%d   [ENTER]"
                                % (self.xp_gained, self.kills_on_win), True, (200, 200, 200))
            else:
                top = big.render("THE STAGE FALLS", True, (220, 60, 60))
                sub = sm.render("[ENTER]", True, (200, 200, 200))
            surface.blit(top, (rd.SCREEN_W // 2 - top.get_width() // 2, 300))
            surface.blit(sub, (rd.SCREEN_W // 2 - sub.get_width() // 2, 370))