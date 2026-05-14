import sys
import random
import math
import os
import pygame
from pygame.locals import *
import socket
import threading
import pickle

pygame.init()

s_width, s_height = 1080, 800
screen = pygame.display.set_mode((s_width, s_height))
pygame.display.set_caption("Space War X Pantai Padang")
clock = pygame.time.Clock()
FPS = 60
HOST = "0.0.0.0"
PORT = 5555
PARTICLE_SCALE = 0.72

is_host = False
conn = None
client_socket = None
network_data = {
    "x": 0,
    "y": 0,
    "health": 100
}
enemy_network_data = {
    "x": 0,
    "y": 0,
    "health": 100
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_CACHE = {}
FONT_CACHE = {}

try:
    pygame.mixer.init()
    MIXER_READY = True
except Exception:
    MIXER_READY = False

def load_image(filename, size=None, alpha=True):
    cache_key = (filename, size, alpha)
    if cache_key in IMAGE_CACHE:
        return IMAGE_CACHE[cache_key]

    path = os.path.join(BASE_DIR, filename)
    try:
        img = pygame.image.load(path)
        img = img.convert_alpha() if alpha else img.convert()
        if size:
            img = pygame.transform.smoothscale(img, size)
        IMAGE_CACHE[cache_key] = img
        return img
    except Exception:
        return None

def get_font(size, bold=True):
    cache_key = (size, bold)
    if cache_key not in FONT_CACHE:
        FONT_CACHE[cache_key] = pygame.font.SysFont("Verdana", size, bold=bold)
    return FONT_CACHE[cache_key]

bg_image = load_image("pantai_padang_dark.png", (s_width, s_height), alpha=False)
if bg_image is None:
    bg_image = pygame.Surface((s_width, s_height))
    bg_image.fill((5, 8, 22))

dark_overlay = pygame.Surface((s_width, s_height), pygame.SRCALPHA)
dark_overlay.fill((0, 0, 0, 38))
fog_overlay = pygame.Surface((s_width, s_height), pygame.SRCALPHA)
fog_overlay.fill((30, 35, 55, 14))
screen_overlay = pygame.Surface((s_width, s_height), pygame.SRCALPHA)

SHIP_OPTIONS = [
    {"name": "SKY PHOENIX", "image": "player_1.png", "health": 80, "shoot_delay": 100, "damage": 9, "bullet_count": 2, "speed": 0.25, "color": (0, 255, 255), "desc": "Seimbang"},
    {"name": "BLAZE FALCON", "image": "player_2.png", "health": 100, "shoot_delay": 75, "damage": 7, "bullet_count": 3, "speed": 0.10, "color": (255, 165, 35), "desc": "Tembakan cepat"},
    {"name": "TITAN WASP", "image": "player_3.png", "health": 70, "shoot_delay": 125, "damage": 20, "bullet_count": 2, "speed": 0.30, "color": (120, 255, 80), "desc": "Damage besar"},
]

class SoundManager:
    def __init__(self):
        self.sound_on = True
        self.music_on = True
        self.ready = MIXER_READY
        self.sounds = {}
        if self.ready:
            for key, filename in {
                "shoot": "sfx_shoot.wav",
                "enemy": "sfx_enemy.wav",
                "boss": "sfx_boss.wav",
                "laser": "sfx_laser.wav",
            }.items():
                try:
                    self.sounds[key] = pygame.mixer.Sound(os.path.join(BASE_DIR, filename))
                except Exception:
                    pass
            try:
                pygame.mixer.music.load(os.path.join(BASE_DIR, "bgm_battle.wav"))
                pygame.mixer.music.set_volume(0.27)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

    def play(self, key):
        if self.ready and self.sound_on and key in self.sounds:
            self.sounds[key].play()

    def toggle_sound(self):
        self.sound_on = not self.sound_on

    def toggle_music(self):
        self.music_on = not self.music_on
        if not self.ready:
            return
        if self.music_on:
            try:
                pygame.mixer.music.unpause()
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.play(-1)
            except Exception:
                pass
        else:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

sound = SoundManager()

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
            self.particles.append([[x, y], [math.cos(ang) * speed, math.sin(ang) * speed], random.randint(3, 8), random.choice([color, (255, 220, 120), (255, 90, 40)])])
        for _ in range(max(8, amount // 2)):
            speed = random.uniform(power * 0.7, power * 1.8)
            ang = random.uniform(0, math.tau)
            self.sparks.append([[x, y], [math.cos(ang) * speed, math.sin(ang) * speed], random.randint(12, 26)])
        for _ in range(max(5, amount // 4)):
            speed = random.uniform(0.3, 1.7)
            ang = random.uniform(0, math.tau)
            self.smoke.append([[x, y], [math.cos(ang) * speed, math.sin(ang) * speed], random.randint(12, 28)])

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
            alpha = int(38 * life)
            if alpha > 0:
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
        self.rect.x = random.randrange(0, s_width)
        self.rect.y = random.randrange(0, s_height)
        self.speed = random.uniform(0.4, 1.4)

    def update(self):
        self.rect.y += self.speed
        if self.rect.y > s_height:
            self.rect.y = -10
            self.rect.x = random.randrange(0, s_width)

class Player(pygame.sprite.Sprite):
    def __init__(self, ship_data):
        super().__init__()
        self.ship_data = ship_data
        self.image = load_image(ship_data["image"], None, True)
        if self.image is None:
            self.image = pygame.Surface([82, 82], pygame.SRCALPHA)
            pygame.draw.polygon(self.image, ship_data["color"], [(41, 0), (8, 78), (41, 58), (74, 78)])
            pygame.draw.polygon(self.image, (230, 255, 255), [(41, 10), (29, 50), (53, 50)])
        self.rect = self.image.get_rect()
        self.max_health = ship_data["health"]
        self.health = self.max_health
        self.follow_speed = ship_data["speed"]
        self.pos_x, self.pos_y = s_width // 2, s_height - 140

    def update(self):
        mx, my = pygame.mouse.get_pos()
        self.pos_x += (mx - self.pos_x) * self.follow_speed
        self.pos_y += (my - self.pos_y) * self.follow_speed
        self.rect.center = (self.pos_x, self.pos_y)
        self.rect.clamp_ip(screen.get_rect())

    def draw_hp_bar(self, surface):
        bar_width = 105
        fill = (max(0, self.health) / self.max_health) * bar_width
        x = self.rect.centerx - bar_width // 2
        y = self.rect.bottom + 12
        pygame.draw.rect(surface, (20, 20, 30), [x, y, bar_width, 8], border_radius=4)
        pygame.draw.rect(surface, (0, 255, 120), [x, y, fill, 8], border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), [x, y, bar_width, 8], 1, border_radius=4)

class OnlinePlayer(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()

        self.image = load_image("player_2.png", None, True)

        if self.image is None:
            self.image = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.polygon(
                self.image,
                (255, 100, 100),
                [(40, 0), (0, 80), (40, 60), (80, 80)]
            )

        self.rect = self.image.get_rect()
        self.health = 100

    def update_network(self, data):
        self.rect.centerx = data["x"]
        self.rect.centery = data["y"]
        self.health = data["health"]

class Enemy(pygame.sprite.Sprite):
    def __init__(self, is_boss=False, orbit_target=None, orbit_angle=0):
        super().__init__()
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
                pygame.draw.ellipse(self.image, (170, 60, 255), [0, 35, 200, 80])
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
            self.start_x = s_width // 2 if self.is_boss else random.randint(120, s_width - 120)
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
        if not self.is_boss and self.rect.top > s_height - 18:
            self.has_escaped = True

    def draw_hp_bar(self, surface):
        if self.health < self.max_health and not self.is_boss:
            width = self.rect.width
            fill = (max(0, self.health) / self.max_health) * width
            y = self.rect.y - 14
            pygame.draw.rect(surface, (40, 10, 20), [self.rect.x, y, width, 7], border_radius=3)
            pygame.draw.rect(surface, (255, 40, 40), [self.rect.x, y, fill, 7], border_radius=3)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, color=(0, 255, 255), speed=-15, damage=10, width=6, height=18, dx=0):
        super().__init__()
        self.image = pygame.Surface([width + 10, height + 10], pygame.SRCALPHA)
        pygame.draw.rect(self.image, (*color[:3], 65), [4, 4, width + 2, height + 2], border_radius=max(2, width // 2))
        pygame.draw.rect(self.image, color, [5, 2, max(2, width), height], border_radius=max(2, width // 2))
        self.rect = self.image.get_rect(centerx=x, centery=y)
        self.speed = speed
        self.dx = dx
        self.damage = damage

    def update(self):
        self.rect.y += self.speed
        self.rect.x += self.dx
        if self.rect.bottom < 0 or self.rect.top > s_height or self.rect.right < 0 or self.rect.left > s_width:
            self.kill()

class BossLaser:
    def __init__(self, boss):
        self.boss = boss
        self.warning_time = 80
        self.active_time = 80
        self.fade_time = 35
        self.timer = self.warning_time + self.active_time + self.fade_time
        self.width = 88
        self.core_width = 22
        self.damage_tick = 0
        self.flash_done = False
        self.x = boss.rect.centerx
        self.start_y = boss.rect.bottom - 4

    def update(self):
        self.timer -= 1
        self.damage_tick += 1
        if self.boss and self.boss.alive():
            self.x = self.boss.rect.centerx
            self.start_y = self.boss.rect.bottom - 4

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
        return pygame.Rect(self.x - hit_w // 2, self.start_y, hit_w, s_height - self.start_y)

    def can_damage(self):
        return self.active and self.damage_tick % 6 == 0

    def draw_warning(self, surface):
        ticks = pygame.time.get_ticks()
        progress = 1 - ((self.timer - (self.active_time + self.fade_time)) / self.warning_time)
        pulse = 0.5 + 0.5 * math.sin(ticks * 0.025)
        alpha = int(90 + 115 * pulse)
        line_h = s_height - self.start_y
        warn_w = 190
        cx = warn_w // 2
        warn_surface = pygame.Surface((warn_w, line_h), pygame.SRCALPHA)

        # Garis peringatan dimulai tepat di bawah boss sehingga terasa menyatu dengan meriam.
        pygame.draw.rect(warn_surface, (255, 30, 70, alpha), [cx - 7, 0, 14, line_h], border_radius=6)
        pygame.draw.line(warn_surface, (255, 240, 240, alpha), (cx, 0), (cx, line_h), 2)

        # Cahaya Laser Terhubung dengan meriam Boss
        ring_radius = int(24 + progress * 28 + pulse * 4)
        pygame.draw.circle(warn_surface, (255, 55, 140, 125), (cx, 2), ring_radius, 4)
        pygame.draw.circle(warn_surface, (255, 255, 255, 165), (cx, 2), max(10, ring_radius // 3), 2)
        pygame.draw.circle(warn_surface, (180, 50, 255, 120), (cx, 2), 14 + int(progress * 5))

        ground_y = line_h - 24
        outer = int(18 + progress * 18)
        inner = max(8, outer // 2)
        pygame.draw.circle(warn_surface, (255, 70, 90, alpha), (cx, ground_y), outer, 3)
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
        ticks = pygame.time.get_ticks()
        scale = self.current_alpha_scale()
        beam_h = s_height - self.start_y
        glow_w = self.width
        core_w = self.core_width + int(3 * math.sin(ticks * 0.05))
        beam_surface = pygame.Surface((glow_w + 100, beam_h + 120), pygame.SRCALPHA)
        cx = beam_surface.get_width() // 2

        # Laser utama dimulai tepat di bawah meriam boss, tanpa celah.
        pygame.draw.rect(beam_surface, (120, 0, 255, int(95 * scale)), [cx - glow_w // 2, 0, glow_w, beam_h], border_radius=26)
        pygame.draw.rect(beam_surface, (255, 40, 220, int(170 * scale)), [cx - 26, 0, 52, beam_h], border_radius=18)
        pygame.draw.rect(beam_surface, (255, 245, 255, int(255 * scale)), [cx - core_w // 2, 0, core_w, beam_h], border_radius=10)

        ring_spacing = 64
        t = ticks * 0.22
        for i in range(10):
            ring_y = int((i * ring_spacing + t) % max(1, beam_h))
            width = 46 + int(8 * math.sin(i + ticks * 0.03))
            pygame.draw.ellipse(beam_surface, (255, 170, 255, int(135 * scale)), [cx - width // 2, ring_y + 2, width, 10], 2)

        # Kilatan api dari moncong senjata dengan bagian bawah boss, sehingga terasa seperti berasal dari kapal.
        pygame.draw.circle(beam_surface, (180, 50, 255, int(170 * scale)), (cx, 6), 40)
        pygame.draw.circle(beam_surface, (255, 90, 245, int(215 * scale)), (cx, 6), 24)
        pygame.draw.circle(beam_surface, (255, 255, 255, int(255 * scale)), (cx, 6), 10)

        # Busur energi samping di dekat moncong
        for side in (-1, 1):
            points = []
            base_x = cx + side * 20
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
            px = int(cx + math.cos(ang) * 54)
            py = int(impact_y + math.sin(ang) * 10)
            pygame.draw.line(beam_surface, (255, 180, 100, int(185 * scale)), (cx, impact_y), (px, py + 18), 3)

        surface.blit(beam_surface, (self.x - cx, self.start_y))

    def draw(self, surface):
        if self.in_warning:
            self.draw_warning(surface)
        else:
            self.draw_active_beam(surface)

def host_server():
    global conn

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    print("Menunggu player masuk...")

    conn, addr = server.accept()

    print("Player connected:", addr)

    while True:
        try:
            data = conn.recv(4096)

            if not data:
                break

            received = pickle.loads(data)

            enemy_network_data["x"] = received["x"]
            enemy_network_data["y"] = received["y"]
            enemy_network_data["health"] = received["health"]

            send_data = pickle.dumps(network_data)
            conn.send(send_data)

        except Exception:
            break

    server.close()


def connect_to_server(ip):
    global client_socket

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((ip, PORT))

    while True:
        try:
            send_data = pickle.dumps(network_data)
            client_socket.send(send_data)

            data = client_socket.recv(4096)

            if not data:
                break

            received = pickle.loads(data)

            enemy_network_data["x"] = received["x"]
            enemy_network_data["y"] = received["y"]
            enemy_network_data["health"] = received["health"]

        except:
            break

class Game:
    def __init__(self):
        self.selected_ship_index = 0
        self.ship_cards = []
        self.setup()
        self.state = "MENU"
        self.run()

    def setup(self):
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.bg_sprites = pygame.sprite.Group()
        self.explosions = []
        self.boss_lasers = []
        self.score = 0
        self.game_over = False
        self.wave = 1
        self.wave_targets = {1: 5, 2: 10, 3: 15, 4: 1}
        self.killed_in_wave = 0
        self.boss_spawned = False
        self.shoot_cooldown = 0
        self.shoot_delay = SHIP_OPTIONS[self.selected_ship_index]["shoot_delay"]
        self.bullet_damage = SHIP_OPTIONS[self.selected_ship_index]["damage"]
        self.game_over_alpha = 0
        self.flash_alpha = 0
        self.boss_attack_text = ""
        self.boss_attack_timer = 0
        for _ in range(60):
            self.bg_sprites.add(BackgroundParticle())
        self.player = Player(SHIP_OPTIONS[self.selected_ship_index])
        self.online_player = OnlinePlayer()
        self.all_sprites.add(self.online_player)
        self.all_sprites.add(self.player)
        self.spawn_wave_enemies()

    def spawn_wave_enemies(self):
        if self.wave <= 3:
            current_count = len(self.enemies)
            needed = min(6, self.wave_targets[self.wave] - self.killed_in_wave)
            for _ in range(max(0, needed - current_count)):
                e = Enemy(False)
                self.enemies.add(e)
                self.all_sprites.add(e)
        elif self.wave == 4 and not self.boss_spawned:
            self.boss = Enemy(True)
            self.enemies.add(self.boss)
            self.all_sprites.add(self.boss)
            for i in range(5):
                angle = (2 * math.pi / 5) * i
                guard = Enemy(False, self.boss, angle)
                self.enemies.add(guard)
                self.all_sprites.add(guard)
            self.boss_spawned = True

    def draw_text(self, text, size, x, y, color=(255, 255, 255), pulse=False, center=True):
        if pulse:
            size = int(size * (1 + 0.05 * math.sin(pygame.time.get_ticks() * 0.005)))
        font = get_font(size, True)
        img = font.render(text, True, color)
        rect = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))
        screen.blit(img, rect)
        return rect

    def draw_button(self, rect, text, border_color=(0, 255, 210), fill=(12, 18, 30), text_color=(255, 255, 255)):
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        color = tuple(min(255, c + 25) for c in fill) if hovered else fill
        pygame.draw.rect(screen, color, rect, border_radius=14)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=14)
        self.draw_text(text, 22, rect.centerx, rect.centery, text_color, pulse=hovered)
        return hovered

    def draw_background(self):
        screen.blit(bg_image, (0, 0))
        self.bg_sprites.draw(screen)
        screen.blit(fog_overlay, (0, 0))
        screen.blit(dark_overlay, (0, 0))

    def draw_ship_select_menu(self):
        title_y = 70
        self.draw_text("SPACE WAR X PANTAI PADANG", 44, s_width // 2, title_y, (0, 255, 210), True)
        self.draw_text("PILIH PESAWAT PLAYER", 25, s_width // 2, title_y + 49, (255, 235, 0))
        self.ship_cards = []

        card_w, card_h = 300, 338
        start_x = (s_width - (card_w * 3 + 30 * 2)) // 2
        y = 170
        for i, ship in enumerate(SHIP_OPTIONS):
            x = start_x + i * (card_w + 30)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.ship_cards.append(rect)
            selected = i == self.selected_ship_index
            border = ship["color"] if selected else (100, 120, 150)
            fill = (20, 30, 45) if selected else (12, 15, 25)
            pygame.draw.rect(screen, fill, rect, border_radius=18)
            pygame.draw.rect(screen, border, rect, 3 if selected else 2, border_radius=18)

            img = load_image(ship["image"], (118, 118), True)
            if img:
                screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 88)))

            self.draw_text(ship["name"], 22, rect.centerx, rect.y + 169, ship["color"])
            self.draw_text(ship["desc"], 17, rect.centerx, rect.y + 202, (230, 240, 255))
            self.draw_stat("HP", ship["health"], 130, rect.x + 42, rect.y + 237, ship["color"])
            self.draw_stat("RATE", 155 - ship["shoot_delay"], 90, rect.x + 42, rect.y + 268, ship["color"])
            self.draw_stat("DMG", ship["damage"], 15, rect.x + 42, rect.y + 299, ship["color"])
            if selected:
                self.draw_text("DIPILIH", 18, rect.centerx, rect.bottom - 15, (255, 255, 255), True)

        self.start_button = pygame.Rect(s_width // 2 - 160, 540, 320, 56)
        self.sound_button = pygame.Rect(s_width // 2 - 260, 612, 230, 46)
        self.music_button = pygame.Rect(s_width // 2 + 30, 612, 230, 46)
        self.exit_button = pygame.Rect(s_width // 2 - 125, 675, 250, 48)
        self.draw_button(self.start_button, "MULAI MISI", (0, 255, 210))
        self.draw_button(self.sound_button, f"SOUND: {'ON' if sound.sound_on else 'OFF'}", (255, 180, 60), (18, 16, 24))
        self.draw_button(self.music_button, f"MUSIC: {'ON' if sound.music_on else 'OFF'}", (180, 110, 255), (18, 16, 24))
        self.draw_button(self.exit_button, "KELUAR", (255, 85, 95), (25, 12, 18))
        self.draw_text("Klik pesawat untuk pilih | H = Host | J = Join | S = Sound | M = Music | ESC/Q = Keluar", 18, s_width // 2, 748, (210, 230, 255))

    def draw_stat(self, label, value, max_value, x, y, color):
        self.draw_text(label, 15, x, y, (220, 230, 245), center=False)
        bar_x = x + 70
        bar_w = 145
        fill_w = int(max(0, min(1, value / max_value)) * bar_w)
        pygame.draw.rect(screen, (35, 35, 45), [bar_x, y + 3, bar_w, 10], border_radius=5)
        pygame.draw.rect(screen, color, [bar_x, y + 3, fill_w, 10], border_radius=5)

    def draw_boss_hp_ui(self):
        boss = None
        for enemy in self.enemies:
            if enemy.is_boss:
                boss = enemy
                break
        if not boss:
            return
        panel = pygame.Rect(s_width // 2 - 330, 18, 660, 62)
        pulse = int(35 + 25 * math.sin(pygame.time.get_ticks() * 0.008))
        pygame.draw.rect(screen, (18, 8, 28), panel, border_radius=20)
        pygame.draw.rect(screen, (170 + pulse, 45, 255), panel, 3, border_radius=20)
        self.draw_text("FINAL BOSS  //  VOID BOSSSHIP", 18, s_width // 2, 32, (255, 215, 255))
        bar = pygame.Rect(panel.x + 28, panel.y + 34, panel.width - 56, 15)
        fill = int((max(0, boss.health) / boss.max_health) * bar.width)
        pygame.draw.rect(screen, (45, 8, 45), bar, border_radius=8)
        pygame.draw.rect(screen, (160, 40, 255), [bar.x, bar.y, fill, bar.height], border_radius=8)
        pygame.draw.rect(screen, (255, 240, 255), bar, 1, border_radius=8)
        for i in range(9):
            x = bar.x + int(bar.width * i / 8)
            pygame.draw.line(screen, (255, 255, 255), (x, bar.y), (x, bar.bottom), 1)

    def draw_game_over_screen(self):
        self.game_over_alpha = min(190, self.game_over_alpha + 5)
        screen_overlay.fill((0, 0, 0, self.game_over_alpha))
        screen.blit(screen_overlay, (0, 0))
        if self.game_over_alpha >= 150:
            panel = pygame.Rect(0, 0, 590, 325)
            panel.center = (s_width // 2, s_height // 2)
            pygame.draw.rect(screen, (18, 18, 35), panel, border_radius=22)
            pygame.draw.rect(screen, (255, 70, 90), panel, 3, border_radius=22)
            self.draw_text("MISSION FAILED", 56, s_width // 2, s_height // 2 - 95, (255, 70, 90), True)
            self.draw_text(f"FINAL SCORE: {self.score}", 28, s_width // 2, s_height // 2 - 25)
            self.draw_text("R = Restart  |  M = Menu  |  Q/ESC = Quit", 21, s_width // 2, s_height // 2 + 35, (0, 255, 210), True)
            self.end_restart_button = pygame.Rect(s_width // 2 - 210, s_height // 2 + 80, 190, 48)
            self.end_menu_button = pygame.Rect(s_width // 2 + 20, s_height // 2 + 80, 190, 48)
            self.end_exit_button = pygame.Rect(s_width // 2 - 95, s_height // 2 + 140, 190, 46)
            self.draw_button(self.end_restart_button, "RESTART", (0, 255, 210))
            self.draw_button(self.end_menu_button, "MENU", (255, 235, 0))
            self.draw_button(self.end_exit_button, "QUIT", (255, 85, 95), (25, 12, 18))

    def draw_win_screen(self):
        screen_overlay.fill((0, 0, 0, 150))
        screen.blit(screen_overlay, (0, 0))
        panel = pygame.Rect(0, 0, 650, 340)
        panel.center = (s_width // 2, s_height // 2)
        pygame.draw.rect(screen, (12, 24, 30), panel, border_radius=24)
        pygame.draw.rect(screen, (0, 255, 120), panel, 3, border_radius=24)
        self.draw_text("GALAXY SAVED!", 64, s_width // 2, s_height // 2 - 100, (0, 255, 120), True)
        self.draw_text(f"FINAL SCORE: {self.score}", 30, s_width // 2, s_height // 2 - 25)
        self.draw_text("Boss terakhir sudah hancur.", 21, s_width // 2, s_height // 2 + 23, (220, 240, 255))
        self.draw_text("R = Restart  |  M = Menu  |  Q/ESC = Quit", 20, s_width // 2, s_height // 2 + 65, (0, 255, 210), True)
        self.end_restart_button = pygame.Rect(s_width // 2 - 210, s_height // 2 + 105, 190, 48)
        self.end_menu_button = pygame.Rect(s_width // 2 + 20, s_height // 2 + 105, 190, 48)
        self.end_exit_button = pygame.Rect(s_width // 2 - 95, s_height // 2 + 165, 190, 46)
        self.draw_button(self.end_restart_button, "RESTART", (0, 255, 210))
        self.draw_button(self.end_menu_button, "MENU", (255, 235, 0))
        self.draw_button(self.end_exit_button, "QUIT", (255, 85, 95), (25, 12, 18))

    def spawn_player_bullets(self):
        ship = SHIP_OPTIONS[self.selected_ship_index]
        color = ship["color"]
        damage = ship["damage"]
        offsets = [-22, 0, 22] if ship["bullet_count"] == 3 else [-18, 18]
        for offset in offsets:
            b = Bullet(self.player.rect.centerx + offset, self.player.rect.top + 6, color, -15, damage, 7, 20)
            self.bullets.add(b)
            self.all_sprites.add(b)
        sound.play("shoot")

    def spawn_boss_spread(self, boss):
        sound.play("laser")
        self.boss_attack_text = "BOSS MODE: BULLET STORM"
        self.boss_attack_timer = 95
        origin_x = boss.rect.centerx
        origin_y = boss.rect.bottom - 18
        for i in range(11):
            dx = (i - 6) * 1.25
            speed = 3.1 + abs(i - 6) * 0.11
            b = Bullet(origin_x, origin_y, (255, 55, 190), speed, 12, 9, 22, dx)
            self.enemy_bullets.add(b)
            self.all_sprites.add(b)
        for offset in [-72, -36, 36, 72]:
            dx = (self.player.rect.centerx - (origin_x + offset)) / max(1, abs(self.player.rect.centery - origin_y)) * 4.5
            b = Bullet(origin_x + offset, origin_y, (255, 120, 60), 5.6, 14, 11, 24, dx)
            self.enemy_bullets.add(b)
            self.all_sprites.add(b)

    def damage_player(self, amount):
        self.player.health -= amount
        self.explosions.append(Explosion(self.player.rect.centerx, self.player.rect.centery, (0, 200, 255), 14, 3, False))
        if self.player.health <= 0:
            self.game_over = True

    def handle_menu_click(self, pos):
        for i, rect in enumerate(self.ship_cards):
            if rect.collidepoint(pos):
                self.selected_ship_index = i
                return
        if hasattr(self, "start_button") and self.start_button.collidepoint(pos):
            self.setup()
            self.state = "PLAYING"
            return
        if hasattr(self, "sound_button") and self.sound_button.collidepoint(pos):
            sound.toggle_sound()
            return
        if hasattr(self, "music_button") and self.music_button.collidepoint(pos):
            sound.toggle_music()
            return
        if hasattr(self, "exit_button") and self.exit_button.collidepoint(pos):
            pygame.quit()
            sys.exit()

    def handle_end_click(self, pos):
        if hasattr(self, "end_restart_button") and self.end_restart_button.collidepoint(pos):
            self.setup()
            self.state = "PLAYING"
        elif hasattr(self, "end_menu_button") and self.end_menu_button.collidepoint(pos):
            self.setup()
            self.state = "MENU"
        elif hasattr(self, "end_exit_button") and self.end_exit_button.collidepoint(pos):
            pygame.quit()
            sys.exit()

    def update_playing(self):
        now = pygame.time.get_ticks()
        self.bg_sprites.update()
        network_data["x"] = self.player.rect.centerx
        network_data["y"] = self.player.rect.centery
        network_data["health"] = self.player.health

        self.online_player.update_network(enemy_network_data)
        self.all_sprites.update()
        self.boss_attack_timer = max(0, self.boss_attack_timer - 1)

        keys = pygame.key.get_pressed()
        if keys[K_SPACE] and now - self.shoot_cooldown > self.shoot_delay:
            self.spawn_player_bullets()
            self.shoot_cooldown = now

        for enemy in list(self.enemies):
            if not enemy.is_boss and enemy.has_escaped:
                self.explosions.append(Explosion(enemy.rect.centerx, s_height - 24, (255, 120, 40), 24, 4, True))
                sound.play("enemy")
                if abs(enemy.rect.centerx - self.player.rect.centerx) < 95 and self.player.rect.bottom > s_height - 170:
                    self.damage_player(8)
                enemy.kill()

        if self.wave <= 3:
            if self.killed_in_wave >= self.wave_targets[self.wave]:
                self.wave += 1
                self.killed_in_wave = 0
                for b in self.enemy_bullets:
                    b.kill()
                self.spawn_wave_enemies()
            elif len(self.enemies) < min(6, self.wave_targets[self.wave] - self.killed_in_wave):
                self.spawn_wave_enemies()

        for enemy in list(self.enemies):
            if now - enemy.last_shot > enemy.shoot_delay:
                if enemy.is_boss:
                    if enemy.attack_mode == 0:
                        self.boss_lasers.append(BossLaser(enemy))
                        self.boss_attack_text = "BOSS MODE: PLASMA LASER"
                        self.boss_attack_timer = 118
                        sound.play("laser")
                    else:
                        self.spawn_boss_spread(enemy)
                    enemy.attack_mode = 1 - enemy.attack_mode
                else:
                    eb = Bullet(enemy.rect.centerx, enemy.rect.bottom, (255, 70, 70), 5, 10, 7, 18)
                    self.enemy_bullets.add(eb)
                    self.all_sprites.add(eb)
                enemy.last_shot = now

        self.flash_alpha = max(0, self.flash_alpha - 18)
        for laser in self.boss_lasers[:]:
            was_warning = laser.in_warning
            laser.update()
            if was_warning and laser.active and not laser.flash_done:
                laser.flash_done = True
                self.flash_alpha = 130
                self.explosions.append(Explosion(laser.x, laser.start_y + 8, (255, 70, 255), 28, 5, True))
                self.explosions.append(Explosion(laser.x, s_height - 26, (255, 170, 90), 34, 6, True))
                sound.play("laser")
            if laser.can_damage() and laser.get_rect().colliderect(self.player.rect):
                self.damage_player(5)
            if not laser.alive:
                self.boss_lasers.remove(laser)

        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, False, True)
        for enemy, hit_bullets in hits.items():
            enemy.health -= sum(b.damage for b in hit_bullets)
            if enemy.health <= 0:
                self.explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, (255, 150, 0), 95 if enemy.is_boss else 32, 9 if enemy.is_boss else 4.5, True))
                sound.play("boss" if enemy.is_boss else "enemy")
                self.score += 1000 if enemy.is_boss else 100
                if enemy.is_boss:
                    enemy.kill()
                    self.boss_lasers.clear()
                    self.state = "WIN"
                else:
                    if not enemy.orbit_target:
                        self.killed_in_wave += 1
                    enemy.kill()

        if pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
            self.damage_player(7)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == KEYDOWN:
                    if event.key in (K_ESCAPE, K_q):
                        pygame.quit()
                        sys.exit()
                    if event.key == K_s:
                        sound.toggle_sound()
                    if self.state == "MENU" and event.key == K_m:
                        sound.toggle_music()

                    if self.state == "MENU":
                        if event.key == K_h:
                            global is_host
                            is_host = True
                            threading.Thread(
                                target=host_server,
                                daemon=True
                            ).start()
                            self.setup()
                            self.state = "PLAYING"
                        elif event.key == K_j:
                            ip = input("Masukkan IP Host: ")
                            threading.Thread(
                                target=connect_to_server,
                                args=(ip,),
                                daemon=True
                            ).start()
                            self.setup()
                            self.state = "PLAYING"
                        elif event.key in (K_1, K_2, K_3):
                            self.selected_ship_index = event.key - K_1
                        elif event.key in (K_RETURN, K_SPACE):
                            self.setup()
                            self.state = "PLAYING"
                    elif self.game_over or self.state == "WIN":
                        if event.key == K_r:
                            self.setup()
                            self.state = "PLAYING"
                        elif event.key == K_m:
                            self.setup()
                            self.state = "MENU"

                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "MENU":
                        self.handle_menu_click(event.pos)
                    elif self.game_over or self.state == "WIN":
                        self.handle_end_click(event.pos)

            if self.state == "PLAYING" and not self.game_over:
                self.update_playing()

            self.draw_background()

            if self.state == "MENU":
                self.draw_ship_select_menu()

            elif self.state == "PLAYING":
                self.all_sprites.draw(screen)
                for laser in self.boss_lasers:
                    laser.draw(screen)
                self.player.draw_hp_bar(screen)
                for e in self.enemies:
                    e.draw_hp_bar(screen)
                for exp in self.explosions[:]:
                    exp.update()
                    exp.draw(screen)
                    if exp.timer <= 0:
                        self.explosions.remove(exp)
                if self.flash_alpha > 0:
                    screen_overlay.fill((255, 210, 255, self.flash_alpha))
                    screen.blit(screen_overlay, (0, 0))

                status = f"WAVE {self.wave}" if self.wave < 4 else "FINAL BOSS"
                self.draw_text(status, 25, 160, 42, (255, 235, 0))
                if self.wave < 4:
                    self.draw_text(f"TARGET: {self.killed_in_wave}/{self.wave_targets[self.wave]}", 20, 160, 76)
                    self.draw_text("Enemy yang lolos akan meledak di bawah!", 17, 240, 108, (255, 160, 110))
                else:
                    self.draw_boss_hp_ui()
                    if self.boss_attack_timer > 0:
                        self.draw_text(self.boss_attack_text, 21, s_width // 2, 98, (255, 130, 230), True)
                self.draw_text(f"SCORE: {self.score}", 25, s_width - 160, 42)
                self.draw_text(f"SFX:{'ON' if sound.sound_on else 'OFF'}  BGM:{'ON' if sound.music_on else 'OFF'}", 16, s_width - 163, 76, (220, 240, 255))

                if self.game_over:
                    self.draw_game_over_screen()

            elif self.state == "WIN":
                self.all_sprites.draw(screen)
                for exp in self.explosions[:]:
                    exp.update()
                    exp.draw(screen)
                    if exp.timer <= 0:
                        self.explosions.remove(exp)
                self.draw_win_screen()

            pygame.display.flip()
            clock.tick(FPS)

if __name__ == "__main__":
    Game()
