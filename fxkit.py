import math
import random

import pygame


def make_glow(radius, color, max_alpha=180):
    size = radius * 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for i in range(radius, 0, -1):
        t = i / radius
        a = int(max_alpha * t * t)
        pygame.draw.circle(surf, (color[0], color[1], color[2], a), (cx, cy), i)
    return surf


def shadow_ellipse(w, h, alpha=60):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (0, 0, 0, alpha), surf.get_rect())
    return surf


class Drift:
    def __init__(self, w, h, colors, n=24, rise_min=12, rise_max=30):
        self.w = w
        self.h = h
        self.colors = colors
        self.n = n
        self.rise_min = rise_min
        self.rise_max = rise_max
        self.parts = [self._new() for _ in range(n)]

    def _new(self):
        life = random.uniform(2.4, 5.0)
        return {
            "x": random.uniform(0, self.w),
            "y": random.uniform(0, self.h),
            "vx": random.uniform(-7, 7),
            "vy": random.uniform(-self.rise_max, -self.rise_min),
            "life": life,
            "t": random.uniform(0, life),
            "size": random.randint(1, 3),
            "col": random.choice(self.colors),
        }

    def update(self, dt):
        for p in self.parts:
            p["t"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["t"] >= p["life"] or p["y"] < -8 or p["x"] < -8 or p["x"] > self.w + 8:
                self.parts.remove(p)
                self.parts.append(self._new())

    def render(self, surface, ox=0, oy=0):
        for p in self.parts:
            fade = 1.0 - p["t"] / p["life"]
            if fade <= 0:
                continue
            sz = max(1, int(p["size"] * (0.5 + fade)))
            k = 0.35 + 0.65 * fade
            col = (min(255, int(p["col"][0] * k)),
                   min(255, int(p["col"][1] * k)),
                   min(255, int(p["col"][2] * k)))
            pygame.draw.rect(surface, col,
                             (int(p["x"]) + ox, int(p["y"]) + oy, sz, sz))