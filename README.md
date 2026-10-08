# Textack v1.0.00

> Side project just for fun — have fun!

Game terminal Linux 100% open source. **Typing = damage.**

Ketik perintah Linux secepatnya + Enter untuk menyerang benteng musuh.
Makin cepat dan akurat, damage makin besar. Salah ketik = diserang balik.

Sekaligus game edukasi: melatih kecepatan mengetik + hafal perintah Linux.

## Jalankan

```bash
python3 main.py
```

Butuh hanya Python 3 standar, tanpa install tambahan. Jalan native di Linux terminal.

## Cara main
- Kata target muncul, misal `sudo apt update`
- Ketik persis sama + Enter
- Combo beruntun = critical damage
- Salah ketik = diserang balik. Diam kelamaan = dicicil musuh.
- Tiap kena = XP. Naik level = pilih 1 dari 3 upgrade (14 macam):
  ATTACK / DEFENSE / SPEED / BASE ala Survivor.io.
- Musuh per wave: SCOUT → RAIDER → GOLEM → OVERLORD, tiap 5 wave BOSS.
- Operator waifu AIKA di panel kanan (terminal ≥102 kolom).
  Ganti art: edit `waifu.txt` atau `~/.config/textack/waifu.txt`.
- Suara: `sfx/*.wav` via paplay/aplay/mpv (fallback beep). F3 on/off.
  Bikin ulang: `python3 tools/make_sfx.py`. Ganti file wav sesukamu.
- `:q` untuk keluar

## Roadmap
1. [x] MVP single-player vs benteng (ini)
2. [ ] Skor + leaderboard lokal
3. [ ] Co-op / PvP online via websocket
4. [ ] Engine C opsional kalau butuh performa

## Lisensi
GPL-3.0-or-later. Lihat `LICENSE`. Bebas dipakai, diubah, disebar.
