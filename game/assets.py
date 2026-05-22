import os
import pygame
from .constants import BASE_DIR

IMAGE_CACHE = {}
FONT_CACHE = {}

def load_image(filename, size=None, alpha=True):
    cache_key = (filename, size, alpha)
    if cache_key in IMAGE_CACHE:
        return IMAGE_CACHE[cache_key]

    path = os.path.join(BASE_DIR, "assets", "images", filename)
    
    if not os.path.exists(path):
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
