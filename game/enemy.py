import random
import math
import pygame
from .constants import S_WIDTH, S_HEIGHT
from .assets import load_image

_next_enemy_id = 1


def reset_enemy_id():
    global _next_enemy_id
    _next_enemy_id = 1


def _next_id():
    global _next_enemy_id
    val = _next_enemy_id
    _next_enemy_id += 1
    return val


class Enemy(pygame.sprite.Sprite):
    def __init__(self, is_boss=False, orbit_target=None, orbit_angle=0):
        super().__init__()
        self.net_id = _next_id()
        self.is_boss = is_boss
        self.orbit_target = orbit_target
        self.orbit_angle = orbit_angle

        if is_boss:
            self.image = load_image("Boss.png", None, True)
            self.laser_delay = 3500
            self.last_laser = pygame.time.get_ticks()
            self.laser_active = False
            if self.image is None:
                self.image = pygame.Surface([200, 150], pygame.SRCALPHA)
                pygame.draw.ellipse(self.image, (170, 60, 255),  [0, 35, 200, 80])
                pygame.draw.ellipse(self.image, (255, 80, 160), [55, 0, 90, 70])
            self.max_health = 2100
            self.shoot_delay = 2050
            self.attack_mode = 0
        else:
            self.image = load_image("EnemyShip.png", None, True)
            if self.image is None:
                self.image = pygame.Surface([70, 70], pygame.SRCALPHA)
                pygame.draw.polygon(self.image, (255, 60, 70), [(35, 70), (0, 0), (70, 0)])
            self.max_health = 85
            self.shoot_delay = random.randint(2000, 4000)

        self.rect = self.image.get_rect()
        self.health = self.max_health
        self.last_shot = pygame.time.get_ticks()
        self.has_escaped = False
        self.reset_pos()

    def reset_pos(self):
        self.timer = random.randint(0, 1000)
        if not self.orbit_target:
            self.rect.y = -180
            self.center_y = 150 if self.is_boss else random.randint(75, 210)
            self.start_x = S_WIDTH // 2 if self.is_boss else random.randint(120, S_WIDTH - 120)
            self.amplitude = 250 if self.is_boss else random.randint(70, 210)
            self.frequency = 0.006 if self.is_boss else random.uniform(0.011, 0.022)
            self.down_speed = 0 if self.is_boss else random.uniform(0.85, 1.85)

    def update(self):
        if self.orbit_target and self.orbit_target.alive():
            self.orbit_angle += 0.02
            self.rect.centerx = self.orbit_target.rect.centerx + math.cos(self.orbit_angle) * 205
            self.rect.centery = self.orbit_target.rect.centery + math.sin(self.orbit_angle) * 135
        else:
            self.timer += 1
            if self.is_boss:
                if self.rect.centery < self.center_y:
                    self.rect.y += 2
                self.rect.centerx = self.start_x + math.sin(self.timer * self.frequency) * self.amplitude
                self.rect.centery = self.center_y + math.cos(self.timer * 0.03) * 20
            else:
                self.rect.y += self.down_speed
                self.rect.centerx = self.start_x + math.sin(self.timer * self.frequency) * self.amplitude
        if not self.is_boss and self.rect.top > S_HEIGHT - 18:
            self.has_escaped = True

    def draw_hp_bar(self, surface):
        if self.health < self.max_health and not self.is_boss:
            width = self.rect.width
            fill = (max(0, self.health) / self.max_health) * width
            y = self.rect.y - 14
            pygame.draw.rect(surface, (40, 10, 20), [self.rect.x, y, width, 7], border_radius=3)
            pygame.draw.rect(surface, (255, 40, 40), [self.rect.x, y, fill, 7],  border_radius=3)
