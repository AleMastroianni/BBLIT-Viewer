# Branding

The logo and icon of the public BBLIT Viewer. Everything here is drawn from
scratch by the scripts in `source/`: no game art, no official lettering.

| file | what |
|---|---|
| `logo.png` | the logo: golden carrot and "BBLIT Viewer" on the blue background (1280 × 400) |
| `banner_background.png` | the blue background alone |
| `social_preview.png` | the logo at 1280 × 640, for GitHub's social preview |
| `background.png` | the viewer's background without levels (1920 × 1080) |
| `icon_goldcarrot.ico`, `icon_goldcarrot_*.png` | the icon, 16 to 256 pixels |
| `fonts/` | Luckiest Guy (Apache 2.0, used), Titan One and Bangers (OFL, tried), with their licences |
| `source/golden_carrot.py` | draws the carrot and writes the icons |
| `source/logo.py` | draws the background and the logo |

To regenerate: `python branding/source/golden_carrot.py`, then
`python branding/source/logo.py` (Pillow needed).
