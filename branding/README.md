# Branding

English · [Italiano](#italiano)

The logo and icon of the public BBLIT Viewer. Everything here is drawn from
scratch by the scripts in `source/`: no game art, no official lettering.

| file | what |
|---|---|
| `logo.png` | the logo: golden carrot and "BBLIT Viewer" on the blue background (1280 × 400) |
| `banner_background.png` | the blue background alone |
| `background.png` | the viewer's background without levels (1920 × 1080) |
| `icon_goldcarrot.ico`, `icon_goldcarrot_*.png` | the icon, 16 to 256 pixels |
| `fonts/` | Luckiest Guy (Apache 2.0, used), Titan One and Bangers (OFL, tried), with their licences |
| `source/golden_carrot.py` | draws the carrot and writes the icons |
| `source/logo.py` | draws the background and the logo |

To regenerate: `python branding/source/golden_carrot.py`, then
`python branding/source/logo.py` (Pillow needed).

---

## Italiano

Il logo e l'icona del BBLIT Viewer pubblico. Tutto e' disegnato da zero dagli
script in `source/`: niente grafica del gioco, niente lettering ufficiale.

| file | cosa |
|---|---|
| `logo.png` | il logo: carota d'oro e "BBLIT Viewer" sullo sfondo blu (1280 × 400) |
| `banner_background.png` | lo sfondo blu da solo |
| `background.png` | lo sfondo del viewer senza livelli (1920 × 1080) |
| `icon_goldcarrot.ico`, `icon_goldcarrot_*.png` | l'icona, da 16 a 256 pixel |
| `fonts/` | Luckiest Guy (Apache 2.0, usato), Titan One e Bangers (OFL, provati), con le loro licenze |
| `source/golden_carrot.py` | disegna la carota e scrive le icone |
| `source/logo.py` | disegna lo sfondo e il logo |

Per rigenerare: `python branding/source/golden_carrot.py`, poi
`python branding/source/logo.py` (serve Pillow).
