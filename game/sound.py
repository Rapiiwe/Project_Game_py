import os
import pygame
from .constants import BASE_DIR

try:
    pygame.mixer.init()
    MIXER_READY = True
except Exception:
    MIXER_READY = False

_SOUND_FILES = {
    "shoot": "sfx_shoot.wav",
    "enemy": "sfx_enemy.wav",
    "boss":  "sfx_boss.wav",
    "laser": "sfx_laser.wav",
}

class SoundManager:
    def __init__(self):
        self.sound_on = True
        self.music_on = True
        self.ready = MIXER_READY
        self.sounds = {}

        if not self.ready:
            return

        sounds_dir = os.path.join(BASE_DIR, "assets", "sounds")
        for key, filename in _SOUND_FILES.items():
            path = os.path.join(sounds_dir, filename)
            if not os.path.exists(path):
                path = os.path.join(BASE_DIR, filename)
            try:
                self.sounds[key] = pygame.mixer.Sound(path)
            except Exception:
                pass

        bgm_path = os.path.join(sounds_dir, "bgm_battle.wav")
        if not os.path.exists(bgm_path):
            bgm_path = os.path.join(BASE_DIR, "bgm_battle.wav")
        try:
            pygame.mixer.music.load(bgm_path)
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
