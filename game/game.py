import sys
import math
import pygame
from pygame.locals import *

from .constants import S_WIDTH, S_HEIGHT, FPS, SHIP_OPTIONS
from .assets import load_image, get_font
from .sound import SoundManager
from .particles import Explosion, BackgroundParticle
from .player import Player, OnlinePlayer
from .enemy import Enemy, reset_enemy_id
from .bullets import Bullet, NetworkBullet, BossLaser, reset_bullet_id
from . import network as net


class Game:
    def __init__(self):
        self.screen = pygame.display.get_surface()
        self.clock  = pygame.time.Clock()

        # UI overlays
        self.dark_overlay   = pygame.Surface((S_WIDTH, S_HEIGHT), pygame.SRCALPHA)
        self.dark_overlay.fill((0, 0, 0, 38))
        self.fog_overlay    = pygame.Surface((S_WIDTH, S_HEIGHT), pygame.SRCALPHA)
        self.fog_overlay.fill((30, 35, 55, 14))
        self.screen_overlay = pygame.Surface((S_WIDTH, S_HEIGHT), pygame.SRCALPHA)

        bg = load_image("pantai_padang_dark.png", (S_WIDTH, S_HEIGHT), alpha=False)
        if bg is None:
            bg = pygame.Surface((S_WIDTH, S_HEIGHT))
            bg.fill((5, 8, 22))
        self.bg_image = bg

        self.sound = SoundManager()

        self.selected_ship_index = 0
        self.ship_cards   = []
        self.join_ip_text = ""
        self.state        = "MENU"

        self.setup()
        self.run()

    # ── Setup / Reset ─────────────────────────────────────────────────
    def setup(self):
        reset_enemy_id()
        reset_bullet_id()

        self.all_sprites    = pygame.sprite.Group()
        self.enemies        = pygame.sprite.Group()
        self.bullets        = pygame.sprite.Group()
        self.remote_bullets = pygame.sprite.Group()
        self.enemy_bullets  = pygame.sprite.Group()
        self.bg_sprites     = pygame.sprite.Group()

        self.explosions       = []
        self.boss_lasers      = []
        self.remote_bullet_hits = set()

        self.score            = 0
        self.game_over        = False
        self.wave             = 1
        self.wave_targets     = {1: 5, 2: 10, 3: 15, 4: 1}
        self.killed_in_wave   = 0
        self.boss_spawned     = False
        self.shoot_cooldown   = 0
        self.shoot_delay      = SHIP_OPTIONS[self.selected_ship_index]["shoot_delay"]
        self.bullet_damage    = SHIP_OPTIONS[self.selected_ship_index]["damage"]
        self.game_over_alpha  = 0
        self.flash_alpha      = 0
        self.boss_attack_text = ""
        self.boss_attack_timer = 0

        for _ in range(60):
            self.bg_sprites.add(BackgroundParticle())

        self.player = Player(SHIP_OPTIONS[self.selected_ship_index])
        self.online_player = None
        if net.online_mode:
            self.online_player = OnlinePlayer()
            self.all_sprites.add(self.online_player)
        self.all_sprites.add(self.player)
        self.spawn_wave_enemies()
        self.update_network_snapshot()

    # ── Wave / Enemy spawning ─────────────────────────────────────────
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

    # ── Helpers ───────────────────────────────────────────────────────
    def draw_text(self, text, size, x, y, color=(255, 255, 255), pulse=False, center=True):
        if pulse:
            size = int(size * (1 + 0.05 * math.sin(pygame.time.get_ticks() * 0.005)))
        font = get_font(size, True)
        img  = font.render(text, True, color)
        rect = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))
        self.screen.blit(img, rect)
        return rect

    def draw_button(self, rect, text, border_color=(0, 255, 210), fill=(12, 18, 30), text_color=(255, 255, 255)):
        mouse_pos = pygame.mouse.get_pos()
        hovered   = rect.collidepoint(mouse_pos)
        color     = tuple(min(255, c + 25) for c in fill) if hovered else fill
        pygame.draw.rect(self.screen, color,        rect, border_radius=14)
        pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=14)
        self.draw_text(text, 22, rect.centerx, rect.centery, text_color, pulse=hovered)
        return hovered

    def draw_stat(self, label, value, max_value, x, y, color):
        self.draw_text(label, 15, x, y, (220, 230, 245), center=False)
        bar_x  = x + 70
        bar_w  = 145
        fill_w = int(max(0, min(1, value / max_value)) * bar_w)
        pygame.draw.rect(self.screen, (35, 35, 45), [bar_x, y + 3, bar_w,    10], border_radius=5)
        pygame.draw.rect(self.screen, color,         [bar_x, y + 3, fill_w, 10], border_radius=5)

    def draw_background(self):
        self.screen.blit(self.bg_image, (0, 0))
        self.bg_sprites.draw(self.screen)
        self.screen.blit(self.fog_overlay,  (0, 0))
        self.screen.blit(self.dark_overlay, (0, 0))

    # ── HUD draw methods ──────────────────────────────────────────────
    def draw_ship_select_menu(self):
        title_y = 70
        self.draw_text("SPACE WAR X PANTAI PADANG", 44, S_WIDTH // 2, title_y, (0, 255, 210), True)
        self.draw_text("PILIH PESAWAT PLAYER",      25, S_WIDTH // 2, title_y + 49, (255, 235, 0))
        self.ship_cards = []

        card_w, card_h = 300, 338
        start_x = (S_WIDTH - (card_w * 3 + 30 * 2)) // 2
        y = 170
        for i, ship in enumerate(SHIP_OPTIONS):
            x    = start_x + i * (card_w + 30)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.ship_cards.append(rect)
            selected = (i == self.selected_ship_index)
            border   = ship["color"] if selected else (100, 120, 150)
            fill     = (20, 30, 45) if selected else (12, 15, 25)
            pygame.draw.rect(self.screen, fill,   rect, border_radius=18)
            pygame.draw.rect(self.screen, border, rect, 3 if selected else 2, border_radius=18)

            img = load_image(ship["image"], (118, 118), True)
            if img:
                self.screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 88)))

            self.draw_text(ship["name"], 22, rect.centerx, rect.y + 169, ship["color"])
            self.draw_text(ship["desc"], 17, rect.centerx, rect.y + 202, (230, 240, 255))
            self.draw_stat("HP",   ship["health"],               130, rect.x + 42, rect.y + 237, ship["color"])
            self.draw_stat("RATE", 155 - ship["shoot_delay"],     90, rect.x + 42, rect.y + 268, ship["color"])
            self.draw_stat("DMG",  ship["damage"],                15, rect.x + 42, rect.y + 299, ship["color"])
            if selected:
                self.draw_text("DIPILIH", 18, rect.centerx, rect.bottom - 15, (255, 255, 255), True)

        self.start_button = pygame.Rect(S_WIDTH // 2 - 160, 540, 320, 56)
        self.sound_button = pygame.Rect(S_WIDTH // 2 - 260, 612, 230, 46)
        self.music_button = pygame.Rect(S_WIDTH // 2 +  30, 612, 230, 46)
        self.exit_button  = pygame.Rect(S_WIDTH // 2 - 125, 675, 250, 48)
        self.draw_button(self.start_button, "MULAI MISI",                                (0, 255, 210))
        self.draw_button(self.sound_button, f"SOUND: {'ON' if self.sound.sound_on else 'OFF'}", (255, 180, 60), (18, 16, 24))
        self.draw_button(self.music_button, f"MUSIC: {'ON' if self.sound.music_on else 'OFF'}", (180, 110, 255), (18, 16, 24))
        self.draw_button(self.exit_button,  "KELUAR",                                    (255, 85, 95), (25, 12, 18))
        self.draw_text("Klik pesawat untuk pilih | H = Host | J = Join | S = Sound | M = Music | ESC/Q = Keluar",
                       18, S_WIDTH // 2, 748, (210, 230, 255))

    def draw_waiting_screen(self):
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)
        panel = pygame.Rect(0, 0, 620, 270)
        panel.center = (S_WIDTH // 2, S_HEIGHT // 2)
        pygame.draw.rect(self.screen, (12, 18, 32),    panel, border_radius=22)
        pygame.draw.rect(self.screen, (0, 255, 210), panel, 3, border_radius=22)
        self.draw_text("WAITING PLAYER", 46, S_WIDTH // 2, panel.y + 70, (0, 255, 210), True)
        self.draw_text(net.network_status or "Menunggu player 2 join...", 24, S_WIDTH // 2, panel.y + 132, (255, 235, 0))
        self.draw_text("Game akan mulai otomatis setelah koneksi tersambung", 19, S_WIDTH // 2, panel.y + 180, (220, 240, 255))
        dots = "." * (1 + int(pulse * 3))
        self.draw_text(f"READY CHECK{dots}", 20, S_WIDTH // 2, panel.y + 224, (255, 255, 255))

    def draw_join_input_screen(self):
        panel = pygame.Rect(0, 0, 650, 300)
        panel.center = (S_WIDTH // 2, S_HEIGHT // 2)
        pygame.draw.rect(self.screen, (12, 18, 32),    panel, border_radius=22)
        pygame.draw.rect(self.screen, (255, 235, 0), panel, 3, border_radius=22)
        input_rect = pygame.Rect(panel.x + 75, panel.y + 130, panel.width - 150, 56)
        pygame.draw.rect(self.screen, (8, 12, 22),    input_rect, border_radius=12)
        pygame.draw.rect(self.screen, (0, 255, 210), input_rect, 2, border_radius=12)
        display_ip = self.join_ip_text or "contoh: 192.168.1.10"
        text_color = (245, 250, 255) if self.join_ip_text else (110, 130, 150)
        self.draw_text("JOIN HOST", 46, S_WIDTH // 2, panel.y + 70, (255, 235, 0), True)
        self.draw_text(display_ip, 24, input_rect.x + 18, input_rect.centery, text_color, center=False)
        self.draw_text("Enter = Join  |  Backspace = Hapus  |  M = Menu", 18, S_WIDTH // 2, panel.y + 230, (220, 240, 255))

    def draw_boss_hp_ui(self):
        boss = next((e for e in self.enemies if e.is_boss), None)
        if not boss:
            return
        panel = pygame.Rect(S_WIDTH // 2 - 330, 18, 660, 62)
        pulse = int(35 + 25 * math.sin(pygame.time.get_ticks() * 0.008))
        pygame.draw.rect(self.screen, (18, 8, 28),                panel, border_radius=20)
        pygame.draw.rect(self.screen, (170 + pulse, 45, 255), panel, 3, border_radius=20)
        self.draw_text("FINAL BOSS  //  VOID BOSSSHIP", 18, S_WIDTH // 2, 32, (255, 215, 255))
        bar  = pygame.Rect(panel.x + 28, panel.y + 34, panel.width - 56, 15)
        fill = int((max(0, boss.health) / boss.max_health) * bar.width)
        pygame.draw.rect(self.screen, (45, 8, 45),      bar, border_radius=8)
        pygame.draw.rect(self.screen, (160, 40, 255), [bar.x, bar.y, fill, bar.height], border_radius=8)
        pygame.draw.rect(self.screen, (255, 240, 255), bar, 1, border_radius=8)
        for i in range(9):
            x = bar.x + int(bar.width * i / 8)
            pygame.draw.line(self.screen, (255, 255, 255), (x, bar.y), (x, bar.bottom), 1)

    def draw_game_over_screen(self):
        self.game_over_alpha = min(190, self.game_over_alpha + 5)
        self.screen_overlay.fill((0, 0, 0, self.game_over_alpha))
        self.screen.blit(self.screen_overlay, (0, 0))
        if self.game_over_alpha >= 150:
            panel = pygame.Rect(0, 0, 590, 325)
            panel.center = (S_WIDTH // 2, S_HEIGHT // 2)
            pygame.draw.rect(self.screen, (18, 18, 35),  panel, border_radius=22)
            pygame.draw.rect(self.screen, (255, 70, 90), panel, 3, border_radius=22)
            self.draw_text("MISSION FAILED", 56, S_WIDTH // 2, S_HEIGHT // 2 - 95, (255, 70, 90), True)
            self.draw_text(f"FINAL SCORE: {self.score}", 28, S_WIDTH // 2, S_HEIGHT // 2 - 25)
            self.draw_text("R = Restart  |  M = Menu  |  Q/ESC = Quit", 21, S_WIDTH // 2, S_HEIGHT // 2 + 35, (0, 255, 210), True)
            self.end_restart_button = pygame.Rect(S_WIDTH // 2 - 210, S_HEIGHT // 2 + 80,  190, 48)
            self.end_menu_button    = pygame.Rect(S_WIDTH // 2 +  20, S_HEIGHT // 2 + 80,  190, 48)
            self.end_exit_button    = pygame.Rect(S_WIDTH // 2 -  95, S_HEIGHT // 2 + 140, 190, 46)
            self.draw_button(self.end_restart_button, "RESTART", (0, 255, 210))
            self.draw_button(self.end_menu_button,    "MENU",    (255, 235, 0))
            self.draw_button(self.end_exit_button,    "QUIT",    (255, 85, 95), (25, 12, 18))

    def draw_win_screen(self):
        self.screen_overlay.fill((0, 0, 0, 150))
        self.screen.blit(self.screen_overlay, (0, 0))
        panel = pygame.Rect(0, 0, 650, 340)
        panel.center = (S_WIDTH // 2, S_HEIGHT // 2)
        pygame.draw.rect(self.screen, (12, 24, 30),    panel, border_radius=24)
        pygame.draw.rect(self.screen, (0, 255, 120), panel, 3, border_radius=24)
        self.draw_text("GALAXY SAVED!", 64, S_WIDTH // 2, S_HEIGHT // 2 - 100, (0, 255, 120), True)
        self.draw_text(f"FINAL SCORE: {self.score}", 30, S_WIDTH // 2, S_HEIGHT // 2 - 25)
        self.draw_text("Boss terakhir sudah hancur.", 21, S_WIDTH // 2, S_HEIGHT // 2 + 23, (220, 240, 255))
        self.draw_text("R = Restart  |  M = Menu  |  Q/ESC = Quit", 20, S_WIDTH // 2, S_HEIGHT // 2 + 65, (0, 255, 210), True)
        self.end_restart_button = pygame.Rect(S_WIDTH // 2 - 210, S_HEIGHT // 2 + 105, 190, 48)
        self.end_menu_button    = pygame.Rect(S_WIDTH // 2 +  20, S_HEIGHT // 2 + 105, 190, 48)
        self.end_exit_button    = pygame.Rect(S_WIDTH // 2 -  95, S_HEIGHT // 2 + 165, 190, 46)
        self.draw_button(self.end_restart_button, "RESTART", (0, 255, 210))
        self.draw_button(self.end_menu_button,    "MENU",    (255, 235, 0))
        self.draw_button(self.end_exit_button,    "QUIT",    (255, 85, 95), (25, 12, 18))

    # ── Game logic ────────────────────────────────────────────────────
    def spawn_player_bullets(self):
        ship   = SHIP_OPTIONS[self.selected_ship_index]
        color  = ship["color"]
        damage = ship["damage"]
        offsets = [-22, 0, 22] if ship["bullet_count"] == 3 else [-18, 18]
        for offset in offsets:
            b = Bullet(self.player.rect.centerx + offset, self.player.rect.top + 6, color, -15, damage, 7, 20)
            self.bullets.add(b)
            self.all_sprites.add(b)
        self.sound.play("shoot")

    def update_network_snapshot(self):
        ship = SHIP_OPTIONS[self.selected_ship_index]
        net.network_data["x"]          = self.player.rect.centerx
        net.network_data["y"]          = self.player.rect.centery
        net.network_data["health"]     = self.player.health
        net.network_data["max_health"] = self.player.max_health
        net.network_data["ship_index"] = self.selected_ship_index
        net.network_data["bullets"]    = [
            {"id": b.net_id, "x": b.rect.centerx, "y": b.rect.centery,
             "color": ship["color"], "damage": b.damage}
            for b in self.bullets
        ]
        if net.is_host or not net.online_mode:
            net.network_data["game_state"] = self.build_game_state()
        else:
            net.network_data["game_state"] = {}

    def build_game_state(self):
        return {
            "wave":           self.wave,
            "killed_in_wave": self.killed_in_wave,
            "score":          self.score,
            "game_over":      self.game_over,
            "state":          self.state,
            "enemies": [
                {"id": e.net_id, "x": e.rect.centerx, "y": e.rect.centery,
                 "health": e.health, "max_health": e.max_health,
                 "is_boss": e.is_boss, "has_escaped": e.has_escaped}
                for e in self.enemies
            ],
        }

    def apply_host_game_state(self):
        state = net.enemy_network_data.get("game_state") or {}
        if not state:
            return
        self.wave           = state.get("wave",           self.wave)
        self.killed_in_wave = state.get("killed_in_wave", self.killed_in_wave)
        self.score          = state.get("score",          self.score)
        self.game_over      = state.get("game_over",      self.game_over)
        if state.get("state") == "WIN":
            self.state = "WIN"

        existing = {e.net_id: e for e in self.enemies}
        seen_ids = set()
        for ed in state.get("enemies", []):
            eid = ed.get("id")
            if eid is None:
                continue
            enemy = existing.get(eid)
            if enemy is None:
                enemy = Enemy(ed.get("is_boss", False))
                enemy.net_id = eid
                self.enemies.add(enemy)
                self.all_sprites.add(enemy)
            enemy.is_boss     = ed.get("is_boss",     enemy.is_boss)
            enemy.health      = ed.get("health",      enemy.health)
            enemy.max_health  = ed.get("max_health",  enemy.max_health)
            enemy.has_escaped = ed.get("has_escaped", False)
            enemy.rect.centerx = ed.get("x", enemy.rect.centerx)
            enemy.rect.centery = ed.get("y", enemy.rect.centery)
            seen_ids.add(eid)
        for eid, enemy in existing.items():
            if eid not in seen_ids:
                enemy.kill()

    def sync_remote_bullets(self):
        bullet_data = net.enemy_network_data.get("bullets", [])
        current     = list(self.remote_bullets)
        for i, data in enumerate(bullet_data):
            if i < len(current):
                current[i].update_network(data)
            else:
                self.remote_bullets.add(NetworkBullet(data))
        for bullet in current[len(bullet_data):]:
            bullet.kill()

    def spawn_boss_spread(self, boss):
        self.sound.play("laser")
        self.boss_attack_text  = "BOSS MODE: BULLET STORM"
        self.boss_attack_timer = 95
        ox, oy = boss.rect.centerx, boss.rect.bottom - 18
        for i in range(11):
            dx    = (i - 6) * 1.25
            speed = 3.1 + abs(i - 6) * 0.11
            b = Bullet(ox, oy, (255, 55, 190), speed, 12, 9, 22, dx)
            self.enemy_bullets.add(b)
            self.all_sprites.add(b)
        for offset in [-72, -36, 36, 72]:
            dx = (self.player.rect.centerx - (ox + offset)) / max(1, abs(self.player.rect.centery - oy)) * 4.5
            b  = Bullet(ox + offset, oy, (255, 120, 60), 5.6, 14, 11, 24, dx)
            self.enemy_bullets.add(b)
            self.all_sprites.add(b)

    def damage_player(self, amount):
        self.player.health -= amount
        self.explosions.append(Explosion(self.player.rect.centerx, self.player.rect.centery, (0, 200, 255), 14, 3, False))
        if self.player.health <= 0:
            self.game_over = True

    # ── Input handlers ────────────────────────────────────────────────
    def handle_menu_click(self, pos):
        for i, rect in enumerate(self.ship_cards):
            if rect.collidepoint(pos):
                self.selected_ship_index = i
                return
        if hasattr(self, "start_button") and self.start_button.collidepoint(pos):
            net.reset_network()
            self.setup()
            self.state = "PLAYING"
        elif hasattr(self, "sound_button") and self.sound_button.collidepoint(pos):
            self.sound.toggle_sound()
        elif hasattr(self, "music_button") and self.music_button.collidepoint(pos):
            self.sound.toggle_music()
        elif hasattr(self, "exit_button") and self.exit_button.collidepoint(pos):
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

    def start_join_server(self):
        ip = self.join_ip_text.strip()
        if not ip:
            net.network_status = "IP host belum diisi"
            return
        net.is_host          = False
        net.online_mode      = True
        net.online_connected = False
        net.network_status   = "Menghubungkan ke host..."
        net.start_join_thread(ip)
        self.state = "WAITING"

    # ── Update loop ───────────────────────────────────────────────────
    def update_playing(self):
        now = pygame.time.get_ticks()
        self.bg_sprites.update()

        if self.online_player:
            self.online_player.update_network(net.enemy_network_data)
            self.sync_remote_bullets()

        if net.online_mode and not net.is_host:
            # Client: apply authoritative state from host
            self.apply_host_game_state()
            self.player.update()
            self.bullets.update()
            self.remote_bullets.update()
            self.enemy_bullets.update()
            self.boss_attack_timer = max(0, self.boss_attack_timer - 1)
            keys = pygame.key.get_pressed()
            if keys[K_SPACE] and now - self.shoot_cooldown > self.shoot_delay:
                self.spawn_player_bullets()
                self.shoot_cooldown = now
            if pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
                self.damage_player(7)
            self.update_network_snapshot()
            return

        # Host / solo
        self.all_sprites.update()
        self.boss_attack_timer = max(0, self.boss_attack_timer - 1)

        keys = pygame.key.get_pressed()
        if keys[K_SPACE] and now - self.shoot_cooldown > self.shoot_delay:
            self.spawn_player_bullets()
            self.shoot_cooldown = now

        # Enemies that escaped
        for enemy in list(self.enemies):
            if not enemy.is_boss and enemy.has_escaped:
                self.explosions.append(Explosion(enemy.rect.centerx, S_HEIGHT - 24, (255, 120, 40), 24, 4, True))
                self.sound.play("enemy")
                if abs(enemy.rect.centerx - self.player.rect.centerx) < 95 and self.player.rect.bottom > S_HEIGHT - 170:
                    self.damage_player(8)
                enemy.kill()

        # Wave progression
        if self.wave <= 3:
            if self.killed_in_wave >= self.wave_targets[self.wave]:
                self.wave += 1
                self.killed_in_wave = 0
                for b in self.enemy_bullets:
                    b.kill()
                self.spawn_wave_enemies()
            elif len(self.enemies) < min(6, self.wave_targets[self.wave] - self.killed_in_wave):
                self.spawn_wave_enemies()

        # Enemy shooting
        for enemy in list(self.enemies):
            if now - enemy.last_shot > enemy.shoot_delay:
                if enemy.is_boss:
                    if enemy.attack_mode == 0:
                        self.boss_lasers.append(BossLaser(enemy))
                        self.boss_attack_text  = "BOSS MODE: PLASMA LASER"
                        self.boss_attack_timer = 118
                        self.sound.play("laser")
                    else:
                        self.spawn_boss_spread(enemy)
                    enemy.attack_mode = 1 - enemy.attack_mode
                else:
                    eb = Bullet(enemy.rect.centerx, enemy.rect.bottom, (255, 70, 70), 5, 10, 7, 18)
                    self.enemy_bullets.add(eb)
                    self.all_sprites.add(eb)
                enemy.last_shot = now

        # Boss lasers
        self.flash_alpha = max(0, self.flash_alpha - 18)
        for laser in self.boss_lasers[:]:
            was_warning = laser.in_warning
            laser.update()
            if was_warning and laser.active and not laser.flash_done:
                laser.flash_done = True
                self.flash_alpha = 130
                self.explosions.append(Explosion(laser.x, laser.start_y + 8, (255, 70, 255), 28, 5, True))
                self.explosions.append(Explosion(laser.x, S_HEIGHT - 26,     (255, 170, 90), 34, 6, True))
                self.sound.play("laser")
            if laser.can_damage() and laser.get_rect().colliderect(self.player.rect):
                self.damage_player(5)
            if not laser.alive:
                self.boss_lasers.remove(laser)

        # Player bullets hit enemies
        def _handle_enemy_kill(enemy):
            self.explosions.append(Explosion(
                enemy.rect.centerx, enemy.rect.centery,
                (255, 150, 0), 95 if enemy.is_boss else 32, 9 if enemy.is_boss else 4.5, True))
            self.sound.play("boss" if enemy.is_boss else "enemy")
            self.score += 1000 if enemy.is_boss else 100
            if enemy.is_boss:
                enemy.kill()
                self.boss_lasers.clear()
                self.state = "WIN"
            else:
                if not enemy.orbit_target:
                    self.killed_in_wave += 1
                enemy.kill()

        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, False, True)
        for enemy, hit_bullets in hits.items():
            enemy.health -= sum(b.damage for b in hit_bullets)
            if enemy.health <= 0:
                _handle_enemy_kill(enemy)

        remote_hits = pygame.sprite.groupcollide(self.enemies, self.remote_bullets, False, True)
        for enemy, hit_bullets in remote_hits.items():
            new_hits = [b for b in hit_bullets
                        if b.remote_id is None or b.remote_id not in self.remote_bullet_hits]
            for b in new_hits:
                if b.remote_id is not None:
                    self.remote_bullet_hits.add(b.remote_id)
            if not new_hits:
                continue
            enemy.health -= sum(b.damage for b in new_hits)
            if enemy.health <= 0:
                _handle_enemy_kill(enemy)

        if pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
            self.damage_player(7)

        self.update_network_snapshot()

    # ── Main loop ─────────────────────────────────────────────────────
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
                        self.sound.toggle_sound()
                    if self.state == "MENU" and event.key == K_m:
                        self.sound.toggle_music()

                    if self.state == "MENU":
                        if event.key == K_h:
                            net.is_host          = True
                            net.online_mode      = True
                            net.online_connected = False
                            net.network_status   = "Menunggu player 2 join..."
                            net.start_host_thread()
                            self.state = "WAITING"
                        elif event.key == K_j:
                            self.join_ip_text  = ""
                            net.network_status = ""
                            self.state = "JOIN_INPUT"
                        elif event.key in (K_1, K_2, K_3):
                            self.selected_ship_index = event.key - K_1
                        elif event.key in (K_RETURN, K_SPACE):
                            net.reset_network()
                            self.setup()
                            self.state = "PLAYING"

                    elif self.game_over or self.state == "WIN":
                        if event.key == K_r:
                            self.setup()
                            self.state = "PLAYING"
                        elif event.key == K_m:
                            self.setup()
                            self.state = "MENU"

                    elif self.state == "JOIN_INPUT":
                        if event.key == K_RETURN:
                            self.start_join_server()
                        elif event.key == K_BACKSPACE:
                            self.join_ip_text = self.join_ip_text[:-1]
                        elif event.key == K_m:
                            net.reset_network()
                            self.state = "MENU"
                        elif len(self.join_ip_text) < 45 and event.unicode and event.unicode.isprintable():
                            if event.unicode not in " \t\r\n":
                                self.join_ip_text += event.unicode

                    elif self.state == "WAITING" and event.key == K_m:
                        net.reset_network()
                        self.state = "MENU"

                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "MENU":
                        self.handle_menu_click(event.pos)
                    elif self.game_over or self.state == "WIN":
                        self.handle_end_click(event.pos)

            if self.state == "PLAYING" and not self.game_over:
                self.update_playing()
            elif self.state == "WAITING" and net.online_connected:
                self.setup()
                self.state = "PLAYING"

            self.draw_background()

            if self.state == "MENU":
                self.draw_ship_select_menu()

            elif self.state == "JOIN_INPUT":
                self.draw_join_input_screen()

            elif self.state == "WAITING":
                self.draw_waiting_screen()

            elif self.state == "PLAYING":
                self.all_sprites.draw(self.screen)
                if self.online_player:
                    self.remote_bullets.draw(self.screen)
                for laser in self.boss_lasers:
                    laser.draw(self.screen)
                self.player.draw_hp_bar(self.screen)
                if self.online_player:
                    self.online_player.draw_hp_bar(self.screen)
                for e in self.enemies:
                    e.draw_hp_bar(self.screen)
                for exp in self.explosions[:]:
                    exp.update()
                    exp.draw(self.screen)
                    if exp.timer <= 0:
                        self.explosions.remove(exp)
                if self.flash_alpha > 0:
                    self.screen_overlay.fill((255, 210, 255, self.flash_alpha))
                    self.screen.blit(self.screen_overlay, (0, 0))

                status = f"WAVE {self.wave}" if self.wave < 4 else "FINAL BOSS"
                self.draw_text(status, 25, 160, 42, (255, 235, 0))
                if self.wave < 4:
                    self.draw_text(f"TARGET: {self.killed_in_wave}/{self.wave_targets[self.wave]}", 20, 160, 76)
                    self.draw_text("Enemy yang lolos akan meledak di bawah!", 17, 240, 108, (255, 160, 110))
                else:
                    self.draw_boss_hp_ui()
                    if self.boss_attack_timer > 0:
                        self.draw_text(self.boss_attack_text, 21, S_WIDTH // 2, 98, (255, 130, 230), True)
                self.draw_text(f"SCORE: {self.score}", 25, S_WIDTH - 160, 42)
                self.draw_text(
                    f"SFX:{'ON' if self.sound.sound_on else 'OFF'}  BGM:{'ON' if self.sound.music_on else 'OFF'}",
                    16, S_WIDTH - 163, 76, (220, 240, 255))

                if self.game_over:
                    self.draw_game_over_screen()

            elif self.state == "WIN":
                self.all_sprites.draw(self.screen)
                for exp in self.explosions[:]:
                    exp.update()
                    exp.draw(self.screen)
                    if exp.timer <= 0:
                        self.explosions.remove(exp)
                self.draw_win_screen()

            pygame.display.flip()
            self.clock.tick(FPS)
