# Space War X Pantai Padang

Game tembak-tembakan luar angkasa berbasis pygame, mendukung mode pemain tunggal dan co-op online.

## Struktur Proyek

```
SpaceWar/
├── main.py                  # Titik masuk utama — jalankan file ini untuk memulai game
├── requirements.txt
├── run_game.bat             # Launcher khusus Windows
│
├── assets/
│   ├── images/              # Semua sprite PNG & latar belakang
│   └── sounds/              # Semua efek suara & musik latar (WAV)
│
└── game/                    # Package utama game
    ├── __init__.py
    ├── constants.py         # Ukuran layar, FPS, konfigurasi pesawat, path
    ├── assets.py            # Fungsi load_image() & get_font() dengan sistem cache
    ├── sound.py             # SoundManager (toggle SFX & musik)
    ├── particles.py         # Efek ledakan & partikel bintang latar belakang
    ├── player.py            # Sprite Player & OnlinePlayer
    ├── enemy.py             # Sprite musuh biasa & boss
    ├── bullets.py           # Peluru pemain, peluru jaringan, & laser boss
    ├── network.py           # Thread host/client & data jaringan bersama
    └── game.py              # Kelas Game utama (loop, HUD, logika permainan)
```

## Cara Menjalankan

```bash
pip install -r requirements.txt
python main.py
```

Atau di Windows, klik dua kali `run_game.bat`.

## Kontrol

| Tombol       | Fungsi                              |
|--------------|-------------------------------------|
| Mouse        | Gerakkan pesawat pemain             |
| Space        | Tembak                              |
| H            | Buat sesi online (jadi host)        |
| J            | Gabung sesi online (masukkan IP)    |
| S            | Aktifkan/matikan efek suara         |
| M            | Aktifkan/matikan musik latar        |
| R            | Mulai ulang (dari layar game over)  |
| ESC / Q      | Keluar dari game                    |

## Penjelasan Setiap Modul

- **constants.py** — Menyimpan semua angka konfigurasi (ukuran layar, FPS) dan data ketiga jenis pesawat dalam satu tempat agar mudah diubah.
- **assets.py** — Mengurus pemuatan gambar dan font. Hasil yang sudah dimuat disimpan di cache sehingga tidak perlu dimuat ulang setiap saat.
- **sound.py** — Mengelola semua suara melalui kelas `SoundManager`. Tetap aman digunakan meski perangkat tidak mendukung audio.
- **particles.py** — Menangani semua efek visual: percikan ledakan, asap, dan bintang-bintang yang bergerak di latar belakang.
- **player.py** — Berisi kelas `Player` (bergerak mengikuti mouse) dan `OnlinePlayer` (posisinya disinkronkan dari jaringan).
- **enemy.py** — Mengatur pergerakan musuh biasa (bergelombang turun) dan boss (pola gerak sinusoidal).
- **bullets.py** — Tiga jenis proyektil: `Bullet` untuk peluru biasa, `NetworkBullet` untuk peluru dari pemain lain via jaringan, dan `BossLaser` untuk serangan laser boss.
- **network.py** — Menjalankan thread TCP untuk mode host maupun client, serta menyimpan data posisi & status yang dibagikan antar pemain.
- **game.py** — Inti dari seluruh permainan: mengelola loop utama, mesin status (MENU/PLAYING/WIN/dll), tampilan HUD, dan seluruh logika gameplay.