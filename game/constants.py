import os

#Screen
S_WIDTH, S_HEIGHT = 1080, 800
FPS = 60
PARTICLE_SCALE = 0.72

#Network
HOST = "0.0.0.0"
PORT = 5555

#Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#Ship options
SHIP_OPTIONS = [
    {"name": "SKY PHOENIX",  "image": "player_1.png", "health": 80,  "shoot_delay": 100, "damage": 9,  "bullet_count": 2, "speed": 0.25, "color": (0, 255, 255),    "desc": "Seimbang"},
    {"name": "BLAZE FALCON", "image": "player_2.png", "health": 100, "shoot_delay": 75,  "damage": 7,  "bullet_count": 3, "speed": 0.10, "color": (255, 165, 35),   "desc": "Tembakan cepat"},
    {"name": "TITAN WASP",   "image": "player_3.png", "health": 70,  "shoot_delay": 125, "damage": 20, "bullet_count": 2, "speed": 0.30, "color": (120, 255, 80),   "desc": "Damage besar"},
]
