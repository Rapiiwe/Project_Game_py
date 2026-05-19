import random
import math
import pygame
from .constants import S_WIDTH, S_HEIGHT, PARTICLE_SCALE


class Explosion:
    def __init__(self, x, y, color, amount=28, power=4, shockwave=True):
        amount = max(6, int(amount * PARTICLE_SCALE))
        self.particles = []
        self.sparks = []
        self.smoke = []
        self.timer = 46
        self.max_timer = 46
        self.color = color
        self.x = x
        self.y = y
        self.shockwave = shockwave

        for _ in range(amount):
            speed = random.uniform(1.0, power)
            ang = random.uniform(0, math.tau)
            self.particles.append([
                [x, y],
                [math.cos(ang) * speed, math.sin(ang) * speed],
                random.randint(3, 8),
                random.choice([color, (255, 220, 120), (255, 90, 40)])
            ])
        for _ in range(max(8, amount // 2)):
            speed = random.uniform(power * 0.7, power * 1.8)
            ang = random.uniform(0, math.tau)
            self.sparks.append([
                [x, y],
                [math.cos(ang) * speed, math.sin(ang) * speed],
                random.randint(12, 26)
            ])
        for _ in range(max(5, amount // 4)):
            speed = random.uniform(0.3, 1.7)
            ang = random.uniform(0, math.tau)
            self.smoke.append([
                [x, y],
                [math.cos(ang) * speed, math.sin(ang) * speed],
                random.randint(12, 28)
            ])

    def update(self):
        self.timer -= 1
        for p in self.particles:
            p[0][0] += p[1][0]
            p[0][1] += p[1][1]
            p[1][1] += 0.04
            p[2] -= 0.14
        for s in self.sparks:
            s[0][0] += s[1][0]
            s[0][1] += s[1][1]
            s[1][0] *= 0.94
            s[1][1] *= 0.94
            s[2] -= 0.6
        for sm in self.smoke:
            sm[0][0] += sm[1][0]
            sm[0][1] += sm[1][1] - 0.2
            sm[2] += 0.18

    def draw(self, surface):
        life = max(0, self.timer / self.max_timer)
        if self.shockwave:
            radius = int((1 - life) * 95)
            alpha = int(120 * life)
            if radius > 2 and alpha > 0:
                size = radius * 2 + 8
                layer = pygame.Surface((size, size), pygame.SRCALPHA)
                center = size // 2
                pygame.draw.circle(layer, (255, 210, 120, alpha), (center, center), radius, 3)
                surface.blit(layer, (int(self.x) - center, int(self.y) - center))
        for sm in self.smoke:
            pygame.draw.circle(surface, (70, 70, 78), (int(sm[0][0]), int(sm[0][1])), int(sm[2]))
        for p in self.particles:
            if p[2] > 0:
                pygame.draw.circle(surface, p[3], (int(p[0][0]), int(p[0][1])), int(p[2]))
        for s in self.sparks:
            if s[2] > 0:
                end = (int(s[0][0] - s[1][0] * 2.2), int(s[0][1] - s[1][1] * 2.2))
                pygame.draw.line(surface, (255, 230, 120), (int(s[0][0]), int(s[0][1])), end, 2)


class BackgroundParticle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        size = random.randint(1, 3)
        self.image = pygame.Surface([size, size], pygame.SRCALPHA)
        self.image.fill((180, 210, 255, 120))
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, S_WIDTH)
        self.rect.y = random.randrange(0, S_HEIGHT)
        self.speed = random.uniform(0.4, 1.4)

    def update(self):
        self.rect.y += self.speed
        if self.rect.y > S_HEIGHT:
            self.rect.y = -10
            self.rect.x = random.randrange(0, S_WIDTH)
