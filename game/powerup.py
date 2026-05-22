import pygame
import random
import math
from .constants import S_HEIGHT

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.type = random.choice(['health', 'speed', 'laser'])
        
        if self.type == 'health':
            self.color_base = (40, 200, 40)
            self.color_glow = (40, 200, 40, 90)
            self.color_icon = (255, 255, 255)
        elif self.type == 'speed':
            self.color_base = (240, 200, 20)
            self.color_glow = (240, 200, 20, 90)
            self.color_icon = (255, 255, 255)
        elif self.type == 'laser':
            self.color_base = (20, 200, 240)
            self.color_glow = (20, 200, 240, 90)
            self.color_icon = (255, 255, 255)

        self.size = 48
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed_y = 2.5
        self.pulse_time = random.uniform(0, math.tau)
        self.draw_icon(self.pulse_time)

    def draw_icon(self, pulse):
        self.image.fill((0, 0, 0, 0))
        center = self.size // 2
        
        #Outer glow
        glow_radius = 18 + int(4 * math.sin(pulse))
        pygame.draw.circle(self.image, self.color_glow, (center, center), glow_radius)
        
        #Base ring
        pygame.draw.circle(self.image, self.color_base, (center, center), 15)
        pygame.draw.circle(self.image, (255, 255, 255), (center, center), 15, 2)
        pygame.draw.circle(self.image, (255, 255, 255), (center, center), 11, 1)
        
        #Inner icon
        if self.type == 'health':
            pygame.draw.rect(self.image, self.color_icon, (center - 3, center - 8, 6, 16))
            pygame.draw.rect(self.image, self.color_icon, (center - 8, center - 3, 16, 6))
        elif self.type == 'speed':
            pts = [(center + 1, center - 8), (center + 6, center - 8), (center + 1, center), 
                (center + 5, center), (center - 3, center + 9), (center, center + 1),
                (center - 5, center + 1)]
            pygame.draw.polygon(self.image, self.color_icon, pts)
        elif self.type == 'laser':
            pygame.draw.rect(self.image, self.color_icon, (center - 2, center - 7, 4, 14))
            pygame.draw.circle(self.image, self.color_icon, (center, center - 7), 3)

    def update(self):
        self.rect.y += self.speed_y
        self.pulse_time += 0.15
        self.draw_icon(self.pulse_time)
        if self.rect.top > S_HEIGHT:
            self.kill()
