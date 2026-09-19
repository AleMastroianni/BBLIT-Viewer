"""All the interface texts, in Italian and in English.

A single place for translations, as in the CTR viewer: menus ask for a key
and get the text in the current language, so changing language rebuilds
nothing. A missing key is shown on screen as is.
"""

from __future__ import annotations

LANGUAGES = ("it", "en")
LANGUAGE_NAMES = {"it": "Italiano", "en": "English"}

_language = "en"

TEXTS: dict[str, tuple[str, str]] = {
    # window and status bar
    "title": ("BBLIT Viewer", "BBLIT Viewer"),
    "status.menu": ("Esc menu", "Esc menu"),
    "status.game": ("gioco", "game"),
    "status.speed": ("velocità {v:.0f} m/s", "speed {v:.0f} m/s"),
    "status.paused": ("animazioni ferme", "animations paused"),
    "status.pose": ("posa iniziale", "starting pose"),

    # main menu
    "menu.main": ("Menu", "Menu"),
    "menu.resume": ("Riprendi", "Resume"),
    "menu.load": ("Carica livello", "Load level"),
    "menu.level": ("Opzioni livello", "Level options"),
    "menu.video": ("Opzioni video", "Video options"),
    "menu.general": ("Opzioni generali", "General options"),
    "menu.help": ("Aiuto", "Help"),
    "menu.quit": ("Esci", "Quit"),
    "menu.back": ("Indietro", "Back"),
    "menu.yes": ("Sì", "Yes"),
    "menu.no": ("No", "No"),

    # screen with no levels
    "data.title": ("Mancano i livelli del gioco", "The game's levels are missing"),
    "data.line1": ("Il viewer legge i file .bze del gioco: non li contiene.",
                   "The viewer reads the game's .bze files: it doesn't ship them."),
    "data.line2": ("Copia la cartella Datas\\bze del CD o dell'installazione",
                   "Copy the Datas\\bze folder from the CD or the installation"),
    "data.line3": ("dentro bze_levels, accanto al viewer.", "into bze_levels, next to the viewer."),
    "data.line4": ("Oppure scegli dove stanno già.", "Or choose where they already are."),
    "data.open": ("Apri la cartella bze_levels", "Open the bze_levels folder"),
    "data.choose": ("Scegli la cartella dei livelli…", "Choose the levels folder…"),
    "data.retry": ("Riprova", "Try again"),
    "data.desc_open": ("Crea bze_levels se non c'è e la apre in Esplora file.",
                       "Creates bze_levels if missing and opens it in Explorer."),
    "data.desc_choose": ("Va bene anche la cartella del gioco: il viewer cerca Datas\\bze "
                         "e bze al suo interno. La scelta resta salvata.",
                         "The game folder works too: the viewer looks for Datas\\bze "
                         "and bze inside it. The choice is saved."),
    "data.desc_retry": ("Dopo aver copiato i file.", "After copying the files."),
    "data.no_bze": ("Nessun file .bze in {c}", "No .bze files in {c}"),
    "general.folder": ("Cartella dei livelli", "Levels folder"),
    "general.desc_folder": ("Dove il viewer legge i .bze: {c}", "Where the viewer reads the .bze files: {c}"),
    "load.missing": ("{file}.bze non c'è nella cartella dei livelli.",
                        "{file}.bze is not in the levels folder."),
    "level.no_level": ("Nessun livello caricato", "No level loaded"),

    # load level
    "load.title": ("Carica livello", "Load level"),
    "load.part": ("Parte {n}", "Part {n}"),
    "load.bonus": ("Bonus", "Bonus"),
    "load.desc_level": ("{entry_name} · LevID {id} · {file}.bze",
                            "{entry_name} · LevID {id} · {file}.bze"),
    "load.desc_variant": ("{entry_name} · {file}.bze: sul disco ma non nella tabella dei "
                             "livelli dell'eseguibile, quindi senza LevID.",
                             "{entry_name} · {file}.bze: on the disc but not in the executable's "
                             "level table, so no LevID."),
    "load.desc_era": ("I livelli dell'era, per titolo e parte.",
                        "The era's levels, by title and part."),
    "load.desc_extra": ("L'Era selector (LS01) anche al centro di ogni era, e le "
                          "varianti _8 fuori dalla tabella dei livelli.",
                          "The Era selector (LS01) also at the centre of each era, and "
                          "the _8 variants missing from the level table."),
    "era.nowhere": ("Nowhere", "Nowhere"),
    "era.stone_age": ("Età della pietra", "Stone Age"),
    "era.medieval": ("Medioevo", "Medieval Period"),
    "era.pirates": ("Pirati", "Pirate Years"),
    "era.1930s": ("Anni '30", "The 1930s"),
    "era.dimx": ("Dimensione X", "Dimension X"),
    "extra.title": ("Extra", "Extra"),
    "extra.menu": ("Menu e crediti", "Menu and credits"),
    "extra.hub": ("Era selector", "Era selector"),
    "extra.overview": ("Vista d'insieme", "Overview"),
    "extra.films": ("Filmati", "Cutscenes"),
    "extra.cutscenes": ("Cutscenes", "Cutscenes"),
    "extra.desc_cutscenes": ("Menu, crediti e filmati. Solo nella build Debug.",
                             "Menus, credits and cutscenes. Debug build only."),
    "extra.variants": ("Varianti _8 (senza LevID)", "_8 variants (no LevID)"),

    # level options
    "level.title": ("Opzioni livello — {n}", "Level options — {n}"),
    "level.rendering": ("Resa", "Rendering"),
    "level.texture": ("Texture", "Textures"),
    "level.props": ("Oggetti", "Objects"),
    "level.invisible_walls": ("Muri invisibili", "Invisible walls"),
    "level.no_collision": ("Senza collisione", "No collision"),
    "level.collision_boxes": ("Box di collisione", "Collision boxes"),
    "level.flags": ("Flags", "Flags"),
    "level.death_zones": ("Zone di morte", "Death zones"),
    "level.death_floor": ("Pavimento della morte", "Death floor"),
    "level.ground": ("Terreno di collisione", "Ground"),
    "level.hard_walls": ("Muri duri", "Hard walls"),
    "level.sky": ("Cielo", "Sky"),
    "level.blending": ("Fusioni semitrasparenti", "Semi-transparency"),
    "level.wireframe": ("Wireframe", "Wireframe"),
    "level.entities": ("Entità", "Entities"),
    "level.animations": ("Animazioni", "Animations"),
    "level.anim.playing": ("In movimento", "Playing"),
    "level.anim.paused": ("Ferme", "Paused"),
    "level.anim.pose": ("Posa iniziale", "Starting pose"),
    "level.tps": ("Tick al secondo", "Ticks per second"),
    "level.texanim": ("Texture animate", "Animated textures"),
    "level.clones": ("Template clonati", "Cloned templates"),
    "level.clones.off": ("Spenti", "Off"),
    "level.clones.at_start": ("All'avvio", "At start"),
    "level.clones.all": ("Tutti", "All"),
    "level.no_states": ("Nessuno stato a scelta per questo livello",
                        "No selectable states for this level"),

    # descriptions (bottom line)
    "desc.texture": ("Mostra le texture o solo il colore dei vertici. Tasto T.",
                     "Show textures or vertex colours only. Key T."),
    "desc.props": ("Oggetti piazzati e animati. Tasto O.", "Placed and animated objects. Key O."),
    "desc.invisible_walls": ("Cio' che ti ferma senza niente di disegnato: i muri duri 0x7F della "
                  "heightmap dove non c'e' una parete visibile (terreno o oggetto). In magenta. "
                  "I box degli oggetti sono a parte (Box di collisione).",
                  "What stops you with nothing drawn: the heightmap's 0x7F hard walls where "
                  "there is no visible wall (terrain or object). In magenta. Object boxes are "
                  "separate (Collision boxes)."),
    "level.area_boxes": ("Box delle aree", "Area boxes"),
    "desc.area_boxes": ("Il volume di collisione di ogni mini area (i blocchi della heightmap, "
                    "dalla base alla cima): forse il box che ti chiude. Da verificare nel gioco.",
                    "The collision volume of each mini area (the heightmap blocks, base to "
                    "top): maybe the box that closes you in. To be checked in the game."),
    "level.faces_1000": ("Facce 0x1000", "0x1000 faces"),
    "desc.faces_1000": ("Le facce dei settori 0x1000 del terreno: il gioco non le disegna, ma "
                        "non sono muri (non fermano). Forse trigger o aree di caricamento.",
                        "The faces of the 0x1000 terrain sectors: the game does not draw them, "
                        "but they are not walls (they do not stop you). Maybe triggers or "
                        "loading areas."),
    "desc.no_collision": ("Le facce calpestabili senza collisione: in ciano acceso dove, cadendo, "
                        "si atterra sani e salvi; in ciano scuro dove si finisce in una zona di "
                        "morte, danno o teletrasporto (la lava, i pit).",
                        "Walkable faces with no collision: bright cyan where the fall lands you "
                        "safely; dark cyan where it ends in a death, damage or teleport zone "
                        "(lava, pits)."),
    "desc.collision_boxes": ("Il box di collisione di ogni oggetto, come lo prova il gioco (puo' "
                      "essere molto piu' grande dell'oggetto). In arancione.",
                      "Each object's collision box, as the game tests it (it can be much "
                      "bigger than the object). In orange."),
    "desc.ground": ("Il terreno su cui si sta davvero (la heightmap): verde tenue sotto cio' "
                     "che si vede, verde acceso dove non c'e' niente di disegnato (terreno "
                     "invisibile), bianco coi raggi i punti isolati da 40 unita'.",
                     "The ground you really stand on (the heightmap): faint green under what "
                     "you see, bright green where nothing is drawn (invisible ground), white "
                     "with beams the isolated 40-unit spots."),
    "desc.hard_walls": ("I muri 0x7F della heightmap: fermano a qualunque altezza, anche dove "
                       "non si vede niente. In blu, alti 5 m.",
                       "The heightmap's 0x7F walls: they stop you at any height, even where "
                       "nothing is drawn. In blue, 5 m tall."),
    "desc.flags": ("Sovrapposizioni per il glitch hunting: muri, collisioni, zone di morte.",
                   "Overlays for glitch hunting: walls, collisions, death zones."),
    "desc.death_zones": ("Le zone che ti uccidono e fanno ripartire (rosso) o ti riprendono e "
                        "rimettono in un punto fisso (viola), come il mask pickup del CTR.",
                        "Zones that kill you and respawn you (red) or grab you and put you back "
                        "at a fixed point (violet), like CTR's mask pickup."),
    "desc.death_floor": ("Le zone di morte grandi almeno meta' del livello: il mare, l'abisso "
                         "sotto il livello. Non tutti i livelli ne hanno.",
                         "Death zones at least half the size of the level: the sea, the abyss "
                         "under the level. Not every level has one."),
    "desc.sky": ("La cupola del cielo, che segue la camera. Tasto H.",
                   "The sky dome, which follows the camera. Key H."),
    "desc.blending": ("Le quattro fusioni della PlayStation: ombre, acqua, bagliori. Tasto M.",
                     "The four PlayStation blend modes: shadows, water, glows. Key M."),
    "desc.wireframe": ("Solo gli spigoli dei triangoli. Tasto F.", "Triangle edges only. Key F."),
    "desc.animations": ("Ferme: tutto si blocca dov'è (tasto P). Posa iniziale: il primo "
                        "fotogramma di ogni animazione.",
                        "Paused: everything stops where it is (key P). Starting pose: "
                        "the first frame of every animation."),
    "desc.tps": ("15 misurati sulla PSX. Tasti - e +.", "15, measured on the PSX. Keys - and +."),
    "desc.texanim": ("Occhi, acqua, alone del sole. Tasto N.", "Eyes, water, sun halo. Key N."),
    "desc.clones": ("Template che le regole degli oggetti fanno comparire. Le scelte di "
                   "preferences.py si vedono sempre. Tasto G.",
                   "Templates spawned by object rules. The choices in preferences.py "
                   "are always shown. Key G."),
    "desc.group": ("Solo per questa sessione: al prossimo avvio torna la scelta di "
                    "preferences.py. Il livello si ricostruisce.",
                    "This session only: the next start goes back to the choice in "
                    "preferences.py. The level is rebuilt."),

    # entity groups (preferences.py) and their states
    "group.bridges": ("Ponti levatoi", "Drawbridges"),
    "group.water_barrels": ("Barili in acqua", "Barrels in the water"),
    "group.green_crates": ("Casse verdi", "Green crates"),
    "state.raised": ("Alzati", "Raised"),
    "state.one_third": ("Un terzo", "One third"),
    "state.two_thirds": ("Due terzi", "Two thirds"),
    "state.lowered": ("Abbassati", "Lowered"),
    "state.rising": ("Emergono", "Rising"),
    "state.floating": ("Galleggiano", "Floating"),
    "state.falling": ("Cadono", "Falling"),
    "state.on_ground": ("A terra", "On the ground"),

    # video options
    "video.title": ("Opzioni video", "Video options"),
    "video.fullscreen": ("Schermo intero", "Full screen"),
    "video.vsync": ("VSync", "VSync"),
    "video.filter": ("Filtro texture", "Texture filtering"),
    "video.scale": ("Scala texture", "Texture scale"),
    "video.color": ("Colore", "Colour"),
    "video.color.pc": ("PC", "PC"),
    "video.color.psx": ("PSX (x2)", "PSX (x2)"),
    "video.fov": ("Campo visivo", "Field of view"),
    "desc.fullscreen": ("Anche Alt+Invio.", "Also Alt+Enter."),
    "desc.filter": ("Bilineare come il PC, o i texel netti. Tasto L.",
                    "Bilinear like the PC, or sharp texels. Key L."),
    "desc.scale": ("Ingrandisce le texture con scale2x/scale3x.",
                   "Upscales textures with scale2x/scale3x."),
    "desc.color": ("Il PC usa il colore dei vertici com'è (scoperta 268), la PSX lo raddoppia.",
                    "The PC uses vertex colour as is (finding 268), the PSX doubles it."),

    # general options
    "general.title": ("Opzioni generali", "General options"),
    "general.language": ("Lingua / Language", "Language / Lingua"),
    "general.status_bar": ("Barra di stato", "Status bar"),
    "desc.language": ("Cambia subito, senza ricaricare il livello.",
                    "Changes at once, without reloading the level."),
    "desc.status_bar": ("Livello, coordinate del gioco e in metri, velocità della camera.",
                   "Level, game and metre coordinates, camera speed."),

    # help
    "help.title": ("Aiuto — tasti", "Help — keys"),
    "help.move": ("Muovi la camera", "Move the camera"),
    "help.up_down": ("Camera su / giù", "Camera up / down"),
    "help.look": ("Guarda (tasto destro premuto)", "Look (hold right button)"),
    "help.wheel": ("Velocità della camera", "Camera speed"),
    "help.shift": ("Più veloce / più lento", "Faster / slower"),
    "help.menu": ("Apri / chiudi il menu", "Open / close the menu"),
    "help.menu_nav": ("Nel menu: scegli, cambia, conferma", "In the menu: select, change, confirm"),
    "help.back": ("Nel menu: indietro", "In the menu: back"),
    "help.levels": ("Livello precedente / successivo", "Previous / next level"),
    "help.reset": ("Camera al punto di partenza", "Camera back to the start"),
    "help.tps": ("Tick al secondo", "Ticks per second"),
    "help.pause": ("Ferma / riavvia le animazioni", "Pause / resume animations"),
    "help.fullscreen": ("Schermo intero", "Full screen"),
    "help.k.mouse": ("Mouse destro", "Right mouse"),
    "help.k.wheel": ("Rotella", "Wheel"),
    "help.k.nav": ("↑ ↓ ← → Invio", "↑ ↓ ← → Enter"),
    "help.k.alt": ("Alt+Invio", "Alt+Enter"),

}


def set_language(language: str) -> None:
    global _language
    _language = language if language in LANGUAGES else "en"


def language() -> str:
    return _language


def t(item_key: str, **fields) -> str:
    """The key's text in the current language; the key itself if missing."""
    pair = TEXTS.get(item_key)
    if pair is None:
        return item_key
    label_text = pair[LANGUAGES.index(_language)]
    return label_text.format(**fields) if fields else label_text
