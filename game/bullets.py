import math
import pygame
from .constants import S_WIDTH, S_HEIGHT

_next_bullet_id = 1


def reset_bullet_id():
    global _next_bullet_id
    _next_bullet_id = 1


def _next_id():
    global _next_bullet_id
    val = _next_bullet_id
    _next_bullet_id += 1
    return val


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, color=(0, 255, 255), speed=-15, damage=10, width=6, height=18, dx=0):
        super().__init__()
        self.net_id = _next_id()
        self.image = pygame.Surface([width + 10, height + 10], pygame.SRCALPHA)
        pygame.draw.rect(self.image, (*color[:3], 65), [4, 4, width + 2, height + 2], border_radius=max(2, width // 2))
        pygame.draw.rect(self.image, color,             [5, 2, max(2, width), height], border_radius=max(2, width // 2))
        self.rect = self.image.get_rect(centerx=x, centery=y)
        self.speed = speed
        self.dx = dx
        self.damage = damage

    def update(self):
        self.rect.y += self.speed
        self.rect.x += self.dx
        if (self.rect.bottom < 0 or self.rect.top > S_HEIGHT
                or self.rect.right < 0 or self.rect.left > S_WIDTH):
            self.kill()


class NetworkBullet(pygame.sprite.Sprite):
    def __init__(self, data):
        super().__init__()
        self.image = pygame.Surface([18, 30], pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.damage = 10
        self.remote_id = None
        self.update_network(data)

    def update_network(self, data):
        self.remote_id = data.get("id", self.remote_id)
        color = tuple(data.get("color", (255, 90, 120)))
        damage = data.get("damage", self.damage)
        if damage != self.damage:
            self.damage = damage
        self.image.fill((0, 0, 0, 0))
        pygame.draw.rect(self.image, (*color[:3], 65), [4, 4, 9, 22], border_radius=4)
        pygame.draw.rect(self.image, color,             [5, 2, 7, 20], border_radius=3)
        self.rect.centerx = data.get("x", self.rect.centerx)
        self.rect.centery = data.get("y", self.rect.centery)


class BossLaser:
    def __init__(self, boss):
        self.boss = boss
        self.warning_time = 80
        self.active_time  = 80
        self.fade_time    = 35
        self.timer = self.warning_time + self.active_time + self.fade_time
        self.width      = 88
        self.core_width = 22
        self.damage_tick = 0
        self.flash_done  = False
        self.x       = boss.rect.centerx
        self.start_y = boss.rect.bottom - 4

    def update(self):
        self.timer -= 1
        self.damage_tick += 1
        if self.boss and self.boss.alive():
            self.x       = self.boss.rect.centerx
            self.start_y = self.boss.rect.bottom - 4

    # ── state properties ──────────────────────────────────────────────
    @property
    def in_warning(self):
        return self.timer > self.active_time + self.fade_time

    @property
    def active(self):
        return self.fade_time < self.timer <= self.active_time + self.fade_time

    @property
    def fading(self):
        return 0 < self.timer <= self.fade_time

    @property
    def alive(self):
        return self.timer > 0

    def current_alpha_scale(self):
        if self.active:
            return 1.0
        if self.fading:
            return max(0.0, self.timer / self.fade_time)
        return 0.0

    def get_rect(self):
        hit_w = 62
        return pygame.Rect(self.x - hit_w // 2, self.start_y, hit_w, S_HEIGHT - self.start_y)

    def can_damage(self):
        return self.active and self.damage_tick % 6 == 0

    # ── drawing ──────────────────────────────────────────────────────
    def draw_warning(self, surface):
        ticks    = pygame.time.get_ticks()
        progress = 1 - ((self.timer - (self.active_time + self.fade_time)) / self.warning_time)
        pulse    = 0.5 + 0.5 * math.sin(ticks * 0.025)
        alpha    = int(90 + 115 * pulse)
        line_h   = S_HEIGHT - self.start_y
        warn_w   = 190
        cx       = warn_w // 2
        warn_surface = pygame.Surface((warn_w, line_h), pygame.SRCALPHA)

        pygame.draw.rect(warn_surface,  (255, 30, 70,  alpha), [cx - 7, 0, 14, line_h], border_radius=6)
        pygame.draw.line(warn_surface,  (255, 240, 240, alpha), (cx, 0), (cx, line_h), 2)

        ring_radius = int(24 + progress * 28 + pulse * 4)
        pygame.draw.circle(warn_surface, (255, 55,  140, 125), (cx, 2), ring_radius, 4)
        pygame.draw.circle(warn_surface, (255, 255, 255, 165), (cx, 2), max(10, ring_radius // 3), 2)
        pygame.draw.circle(warn_surface, (180, 50,  255, 120), (cx, 2), 14 + int(progress * 5))

        ground_y = line_h - 24
        outer    = int(18 + progress * 18)
        inner    = max(8, outer // 2)
        pygame.draw.circle(warn_surface, (255, 70,  90,  alpha), (cx, ground_y), outer, 3)
        pygame.draw.circle(warn_surface, (255, 220, 220, alpha), (cx, ground_y), inner, 2)
        pygame.draw.line(warn_surface, (255, 70, 90, alpha), (cx - outer - 10, ground_y), (cx + outer + 10, ground_y), 1)
        pygame.draw.line(warn_surface, (255, 70, 90, alpha), (cx, ground_y - outer - 10), (cx, ground_y + outer + 10), 1)

        for i in range(6):
            angle = ticks * 0.01 + i * (math.pi / 3)
            px = int(cx + math.cos(angle) * (outer + 12))
            py = int(ground_y + math.sin(angle) * (outer + 12))
            pygame.draw.circle(warn_surface, (255, 180, 120, 150), (px, py), 3)

        surface.blit(warn_surface, (int(self.x) - cx, self.start_y))

    def draw_active_beam(self, surface):
        ticks  = pygame.time.get_ticks()
        scale  = self.current_alpha_scale()
        beam_h = S_HEIGHT - self.start_y
        glow_w = self.width
        core_w = self.core_width + int(3 * math.sin(ticks * 0.05))
        beam_surface = pygame.Surface((glow_w + 100, beam_h + 120), pygame.SRCALPHA)
        cx = beam_surface.get_width() // 2

        pygame.draw.rect(beam_surface, (120, 0,   255, int(95  * scale)), [cx - glow_w // 2, 0, glow_w, beam_h], border_radius=26)
        pygame.draw.rect(beam_surface, (255, 40,  220, int(170 * scale)), [cx - 26, 0, 52, beam_h],              border_radius=18)
        pygame.draw.rect(beam_surface, (255, 245, 255, int(255 * scale)), [cx - core_w // 2, 0, core_w, beam_h], border_radius=10)

        ring_spacing = 64
        t = ticks * 0.22
        for i in range(10):
            ring_y = int((i * ring_spacing + t) % max(1, beam_h))
            width  = 46 + int(8 * math.sin(i + ticks * 0.03))
            pygame.draw.ellipse(beam_surface, (255, 170, 255, int(135 * scale)), [cx - width // 2, ring_y + 2, width, 10], 2)

        pygame.draw.circle(beam_surface, (180, 50,  255, int(170 * scale)), (cx, 6), 40)
        pygame.draw.circle(beam_surface, (255, 90,  245, int(215 * scale)), (cx, 6), 24)
        pygame.draw.circle(beam_surface, (255, 255, 255, int(255 * scale)), (cx, 6), 10)

        for side in (-1, 1):
            points   = []
            base_x   = cx + side * 20
            for step in range(6):
                yy = 4 + step * 12
                xx = base_x + side * int(8 * math.sin(step + ticks * 0.03))
                points.append((xx, yy))
            if len(points) > 1:
                pygame.draw.lines(beam_surface, (255, 140, 255, int(155 * scale)), False, points, 2)

        impact_y = beam_h - 2
        for radius, a in [(64, 75), (42, 135), (24, 230)]:
            pygame.draw.circle(beam_surface, (255, 110, 90, int(a * scale)), (cx, impact_y), radius)
        for i in range(12):
            ang = (i / 12.0) * math.tau + ticks * 0.01
            px  = int(cx + math.cos(ang) * 54)
            py  = int(impact_y + math.sin(ang) * 10)
            pygame.draw.line(beam_surface, (255, 180, 100, int(185 * scale)), (cx, impact_y), (px, py + 18), 3)

        surface.blit(beam_surface, (self.x - cx, self.start_y))

    def draw(self, surface):
        if self.in_warning:
            self.draw_warning(surface)
        else:
            self.draw_active_beam(surface)
