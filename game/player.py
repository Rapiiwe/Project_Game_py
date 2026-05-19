import pygame
from .constants import S_WIDTH, S_HEIGHT, SHIP_OPTIONS
from .assets import load_image


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
        self.pos_x = S_WIDTH // 2
        self.pos_y = S_HEIGHT - 140

    def update(self):
        mx, my = pygame.mouse.get_pos()
        self.pos_x += (mx - self.pos_x) * self.follow_speed
        self.pos_y += (my - self.pos_y) * self.follow_speed
        self.rect.center = (self.pos_x, self.pos_y)
        self.rect.clamp_ip(pygame.display.get_surface().get_rect())

    def draw_hp_bar(self, surface):
        from .assets import get_font
        font = get_font(13, True)
        name_val = getattr(self, "name", "PILOT")
        name_img = font.render(name_val, True, (255, 255, 255))
        name_rect = name_img.get_rect(center=(self.rect.centerx, self.rect.bottom + 10))
        surface.blit(name_img, name_rect)

        bar_width = 105
        fill = (max(0, self.health) / self.max_health) * bar_width
        x = self.rect.centerx - bar_width // 2
        y = self.rect.bottom + 22
        pygame.draw.rect(surface, (20, 20, 30),   [x, y, bar_width, 8], border_radius=4)
        pygame.draw.rect(surface, (0, 255, 120),  [x, y, fill, 8],      border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), [x, y, bar_width, 8], 1, border_radius=4)


class OnlinePlayer(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.ship_index = None
        self.max_health = 100
        self.health = 100
        self.image = pygame.Surface((80, 80), pygame.SRCALPHA)  # temp until set_ship
        self.rect = self.image.get_rect()
        self.set_ship(1)
        self.name = "PILOT 2"

    def set_ship(self, ship_index):
        ship_index = max(0, min(len(SHIP_OPTIONS) - 1, ship_index))
        if ship_index == self.ship_index:
            return
        self.ship_index = ship_index
        ship = SHIP_OPTIONS[ship_index]
        self.max_health = ship["health"]
        self.image = load_image(ship["image"], None, True)
        if self.image is None:
            self.image = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.polygon(self.image, ship["color"], [(40, 0), (0, 80), (40, 60), (80, 80)])

    def update_network(self, data):
        self.set_ship(data.get("ship_index", self.ship_index or 0))
        center = self.rect.center
        self.rect = self.image.get_rect(center=center)
        self.rect.centerx = data.get("x", self.rect.centerx)
        self.rect.centery = data.get("y", self.rect.centery)
        self.max_health = data.get("max_health", self.max_health)
        self.health = data.get("health", self.health)
        self.name = data.get("name", "PILOT 2")

    def draw_hp_bar(self, surface):
        from .assets import get_font
        font = get_font(13, True)
        name_val = getattr(self, "name", "PILOT 2")
        name_img = font.render(name_val, True, (255, 255, 255))
        name_rect = name_img.get_rect(center=(self.rect.centerx, self.rect.bottom + 10))
        surface.blit(name_img, name_rect)

        bar_width = 105
        fill = (max(0, self.health) / max(1, self.max_health)) * bar_width
        x = self.rect.centerx - bar_width // 2
        y = self.rect.bottom + 22
        pygame.draw.rect(surface, (35, 16, 28),   [x, y, bar_width, 8], border_radius=4)
        pygame.draw.rect(surface, (255, 90, 120), [x, y, fill, 8],      border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), [x, y, bar_width, 8], 1, border_radius=4)
