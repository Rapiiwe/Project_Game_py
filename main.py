import pygame
from game.constants import S_WIDTH, S_HEIGHT
from game import Game

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((S_WIDTH, S_HEIGHT))
    pygame.display.set_caption("Space War X Pantai Padang")
    Game()
