"""All the interface texts, in Italian and in English.

A single place for translations, as in the CTR viewer: menus ask for a key
and get the text in the current language, so changing language rebuilds
nothing. A missing key is shown on screen as is.
"""

from __future__ import annotations

import re

LANGUAGES = ("it", "en")
LANGUAGE_NAMES = {"it": "Italiano", "en": "English"}

_language = "en"

TEXTS: dict[str, tuple[str, str]] = {
    # window and status bar
    "title": ("BBLIT Viewer", "BBLIT Viewer"),
    "status.menu": ("Esc menu", "Esc menu"),
    "status.game": ("gioco", "game"),
    "status.speed": ("velocità {v:.0f} m/s", "speed {v:.0f} m/s"),
    "status.area": ("area {n}", "area {n}"),
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
    "level.area_visibility": ("Visibilita' per area come nel gioco", "Visibility by area as in the game"),
    "desc.area_visibility": ("Disegna solo cio' che il gioco disegnerebbe: il pezzo di terreno e gli "
                             "oggetti tagliati per area dell'area della camera, piu' le aree raggiunte "
                             "dai portali a schermo (scoperte 293-295). In LS01 resta il cielo della "
                             "sola isola dove sei. Spenta a ogni avvio.",
                             "Draws only what the game would draw: the terrain piece and the objects "
                             "cut by area of the camera's area, plus the areas reached through the "
                             "portals on screen (findings 293-295). In LS01 only the sky of the island "
                             "you are on is left. Off at every start."),
    "level.invisible_walls": ("Muri invisibili", "Invisible walls"),
    "level.no_collision": ("Senza collisione", "No collision"),
    "level.collision_boxes": ("Box di collisione", "Collision boxes"),
    "level.flags": ("Flags", "Flags"),
    "level.death_zones": ("Zone di morte e danno", "Death and damage zones"),
    "level.teleport_zones": ("Zone di teletrasporto", "Teleport zones"),
    "level.ground": ("Terreno di collisione", "Ground"),
    "level.hard_walls": ("Muri duri", "Hard walls"),
    "level.sky": ("Cielo", "Sky"),
    "level.blending": ("Fusioni semitrasparenti", "Semi-transparency"),
    "level.wireframe": ("Wireframe", "Wireframe"),
    "level.wire.off": ("Spento", "Off"),
    "level.wire.skeleton": ("Scheletro", "Skeleton"),
    "level.wire.grid": ("Griglia", "Grid"),
    "level.entities": ("Entità", "Entities"),
    "level.animations": ("Animazioni", "Animations"),
    "level.anim.playing": ("In movimento", "Playing"),
    "level.anim.paused": ("Ferme", "Paused"),
    "level.anim.pose": ("Posa iniziale", "Starting pose"),
    "level.tps": ("Tick al secondo", "Ticks per second"),
    "level.texanim": ("Texture animate", "Animated textures"),
    "level.gates": ("Cancelli", "Gates"),
    "level.gates.open": ("Aperti", "Open"),
    "level.gates.shut": ("Chiusi", "Shut"),
    "level.gates.game": ("Come nel gioco", "As the game starts"),
    "level.gates.of": ("Cancelli di #{n}", "Gates of #{n}"),
    "level.movers": ("Personaggi in movimento", "Moving characters"),
    "level.clones": ("Template clonati", "Cloned templates"),
    "level.clones.off": ("Spenti", "Off"),
    "level.clones.at_start": ("All'avvio", "At start"),
    "level.clones.all": ("Tutti", "All"),
    "level.no_states": ("Nessuno stato a scelta per questo livello",
                        "No selectable states for this level"),

    # descriptions (bottom line)
    "desc.texture": ("Mostra le texture o solo il colore dei vertici. Tasto [[textures]].",
                     "Show textures or vertex colours only. Key [[textures]]."),
    "desc.props": ("Oggetti piazzati e animati. Tasto [[props]].", "Placed and animated objects. Key [[props]]."),
    "desc.invisible_walls": ("Cio' che ti ferma senza niente di disegnato, in magenta: i muri duri 0x7F "
                             "della heightmap dove non c'e' una parete visibile (INVISIBLE WALL, sigla "
                             "INV) e i gradini di piu' di 100 unita' (STEP WALL, sigla STP), che fermano "
                             "solo salendo: dal lato alto STEP WALL · OUTSIDE. I box degli oggetti sono "
                             "a parte (Box di collisione).",
                             "What stops you with nothing drawn, in magenta: the heightmap's 0x7F hard "
                             "walls where there is no visible wall (INVISIBLE WALL, short INV) and the "
                             "steps of more than 100 units (STEP WALL, short STP), which stop you only "
                             "going up: from the high side STEP WALL · OUTSIDE. Object boxes are "
                             "separate (Collision boxes)."),
    "level.area_boxes": ("Box delle aree", "Area boxes"),
    "desc.area_boxes": ("Il volume di collisione di ogni mini area (i blocchi della heightmap). "
                        "I lati fermano solo chi e' dentro (AREA WALL; da fuori AREA WALL · OUTSIDE: "
                        "si passa). La cima ferma la testa di un salto (JUMP CEILING, da sotto): "
                        "l'origine di Bugs si ferma circa 410 piu' in basso.",
                        "The collision volume of each mini area (the heightmap blocks). The sides "
                        "stop only who is inside (AREA WALL; from outside AREA WALL · OUTSIDE: you "
                        "pass). The top stops the head of a jump (JUMP CEILING, from below): Bugs's "
                        "origin stops about 410 lower."),
    "level.walls_outside": ("Muri: lato di fuori", "Walls: outside side"),
    "desc.walls_outside": ("Il lato dei muri da cui non si e' fermati (le scritte OUTSIDE): i box delle "
                           "aree da fuori e da sopra, i gradini dal lato alto. Spento, da fuori si "
                           "vedono le aree senza il box davanti.",
                           "The side of the walls that does not stop you (the OUTSIDE names): the area "
                           "boxes from outside and above, the steps from the high side. Off, from "
                           "outside you see the areas without the box in front."),
    "level.hole_steps": ("Muri: bordi sui buchi", "Walls: edges over holes"),
    "desc.hole_steps": ("Con Muri invisibili, anche i gradini visti da un buco 0x7E (il suo suolo e' la "
                        "base della lastra): i bordi delle piattaforme sul vuoto. Nel gioco fermano chi "
                        "cade accanto alla piattaforma, ma di solito sono solo rumore.",
                        "With Invisible walls, also the steps seen from a 0x7E hole (its ground is the "
                        "slab's base): the edges of platforms over the void. In the game they stop "
                        "whoever falls next to the platform, but they are mostly noise."),
    "level.gate_links": ("Chi apre cosa", "Who opens what"),
    "level.gate_links.off": ("No", "No"),
    "level.gate_links.gates": ("Solo cancelli", "Gates only"),
    "level.gate_links.all": ("Tutti i collegamenti", "All the links"),
    "level.faces_1000": ("Portali", "Portals"),
    "desc.gate_links": ("Una linea da ogni interruttore a quello che comanda (scoperte 323, 331). "
                        "\"Solo cancelli\": chi apre davvero qualcosa che sbarra la strada, e il "
                        "box dice GATE <- #78. \"Tutti i collegamenti\": anche gli oggetti che "
                        "reagiscono a un byte senza aprire niente (pedane, raccoglibili), col box "
                        "che dice REACTS <- #78 e il tipo che ha. No a ogni avvio e a ogni livello.",
                        "A line from every switch to what it commands (findings 323, 331). \"Gates "
                        "only\": what really opens something that bars the way, and the box says "
                        "GATE <- #78. \"All the links\": the objects that only react to a byte "
                        "without opening anything too (pads, pick-ups), with REACTS <- #78 on the "
                        "box beside what kind it is. No at every start and at every level."),
    "desc.faces_1000": ("I quad 0x1000 del terreno: sono portali, l'area che si vede attraverso e' "
                        "scritta su ognuno (scoperta 293). Il gioco non li disegna e non fermano. In "
                        "grigio.",
                        "The terrain's 0x1000 quads: they are portals, and the area seen through is "
                        "written on each of them (finding 293). The game does not draw them and they "
                        "do not stop you. Grey."),
    "desc.no_collision": ("Cio' che si attraversa, in bianco con gli spigoli neri: le facce "
                          "calpestabili senza suolo di collisione sotto e le loro pareti che lo sweep "
                          "del gioco lascia passare (NO COLLISION, sigla NOC). Cosa c'e' sotto lo "
                          "dicono le flag delle zone.",
                          "What you go through, in white with black edges: the walkable faces with no "
                          "collision ground under them and their walls the game's sweep lets through "
                          "(NO COLLISION, short NOC). What is under them is told by the zone flags."),
    "desc.collision_boxes": ("Il box di collisione di ogni oggetto, come lo prova il gioco (puo' essere "
                             "molto piu' grande dell'oggetto), per cio' che fa a Bugs (scoperta 300): "
                             "SOLID in arancione ti ferma (SLD), PLATFORM in verde ti ferma e ci si sta "
                             "sopra (PLT), TOUCH in blu si tocca soltanto: raccoglibili, trigger (TCH).",
                             "Each object's collision box, as the game tests it (it can be much bigger "
                             "than the object), by what it does to Bugs (finding 300): SOLID in orange "
                             "stops you (SLD), PLATFORM in green stops you and you can stand on it "
                             "(PLT), TOUCH in blue is only touched: pickups, triggers (TCH)."),
    "desc.ground": ("Il terreno su cui si sta davvero (la heightmap): verde tenue sotto cio' "
                     "che si vede, verde acceso dove non c'e' niente di disegnato (terreno "
                     "invisibile), bianco coi raggi i punti isolati da 40 unita'.",
                     "The ground you really stand on (the heightmap): faint green under what "
                     "you see, bright green where nothing is drawn (invisible ground), white "
                     "with beams the isolated 40-unit spots."),
    "desc.hard_walls": ("I muri 0x7F della heightmap: fermano a qualunque altezza, anche dove "
                        "non si vede niente (HARD WALL, sigla HRD). In blu, alti 5 m, visti dal lato "
                        "da cui si entra; per Bugs fermano da ogni lato.",
                        "The heightmap's 0x7F walls: they stop you at any height, even where "
                        "nothing is drawn (HARD WALL, short HRD). In blue, 5 m tall, seen from the "
                        "side you would enter from; for Bugs they stop from every side."),
    "desc.flags": ("Sovrapposizioni per il glitch hunting: muri, collisioni, zone di morte. Ogni "
                   "cosa ha scritto cio' che fa: un nome intero, o piu' sigle se fa piu' cose o e' "
                   "in piu' flag accese (per esempio DTH + DMG).",
                   "Overlays for glitch hunting: walls, collisions, death zones. Each thing is "
                   "named with what it does: a full name, or short names when it does more or is "
                   "in more flags that are on (for example DTH + DMG)."),
    "desc.death_zones": ("Le zone che ti uccidono (DEATH, sigla DTH; DEATH FLOOR, DFL, quelle grandi "
                         "almeno meta' del livello: il mare, l'abisso), con respawn al checkpoint, e "
                         "quelle che ti feriscono (DAMAGE, DMG, azione 0x48). Tutte in rosso; sulla "
                         "faccia in alto tutto cio' che la zona fa, anche il respawn (RSP).",
                         "Zones that kill you (DEATH, short DTH; DEATH FLOOR, DFL, for those at "
                         "least half the size of the level: the sea, the abyss), with a respawn at "
                         "the checkpoint, and zones that hurt you (DAMAGE, DMG, action 0x48). All "
                         "red; on the top face all the zone does, where it sends you too."),
    "desc.teleport_zones": ("Le zone che mandano qualcuno da qualche parte (scoperta 326), in viola, "
                            "con una freccia fino al punto: ENTRANCE e' l'ingresso da un altro livello "
                            "(e dice da quale), TELEPORT sposta Bugs senza condizioni, RECOVER l'oggetto "
                            "dentro la zona (le reti di recupero), RESTART e' dove Bugs torna dopo una "
                            "morte, LEVEL dice il livello a cui porta. Una zona che anche uccide sta in "
                            "tutte e due le flag, con un nome solo (DTH + RST).",
                            "Zones that send somebody somewhere (finding 326), in violet, with an arrow "
                            "to the point: ENTRANCE is the way in from another level (and says which), "
                            "TELEPORT moves Bugs with no condition at all, RECOVER the object inside the "
                            "zone (the recovery nets), RESTART is where Bugs comes back after a death, "
                            "LEVEL says the level it leads to. A zone that also kills is in both flags, "
                            "with one name (DTH + RST)."),
    "desc.sky": ("La cupola del cielo, che segue la camera. Tasto [[sky]].",
                   "The sky dome, which follows the camera. Key [[sky]]."),
    "desc.blending": ("Le quattro fusioni della PlayStation: ombre, acqua, bagliori. Tasto [[blending]].",
                     "The four PlayStation blend modes: shadows, water, glows. Key [[blending]]."),
    "desc.wireframe": ("Scheletro: solo gli spigoli dei triangoli. Griglia: le texture normali e gli "
                       "spigoli sopra, scuri, come nel CTR viewer. Tasto [[wireframe]].",
                       "Skeleton: triangle edges only. Grid: normal textures with the edges over "
                       "them, dark, as in the CTR viewer. Key [[wireframe]]."),
    "desc.animations": ("Ferme: tutto si blocca dov'è (tasto [[pause]]). Posa iniziale: il primo "
                        "fotogramma di ogni animazione.",
                        "Paused: everything stops where it is (key [[pause]]). Starting pose: "
                        "the first frame of every animation."),
    "desc.tps": ("15 misurati sulla PSX. Tasti [[tps_down]] e [[tps_up]].", "15, measured on the PSX. Keys [[tps_down]] and [[tps_up]]."),
    "desc.texanim": ("Occhi, acqua, alone del sole. Tasto [[texanim]].", "Eyes, water, sun halo. Key [[texanim]]."),
    "desc.gates": ("I box che cambiano con lo stato dell'oggetto (scoperta 323): cancelli, porte, "
                   "massi. Aperti di default, perche' aprire un cancello muove solo geometria; "
                   "\"Come nel gioco\" mostra lo stato di partenza. Il livello si ricostruisce.",
                   "The boxes that change with the object's state (finding 323): gates, doors, "
                   "boulders. Open by default, because opening a gate only moves geometry; "
                   "\"As the game starts\" shows the starting state. The level is rebuilt."),
    "desc.gate_group": ("Solo i cancelli che apre quell'interruttore (i gruppi vengono dai dati, "
                        "non da un elenco scritto a mano). Torna alla voce generale a ogni livello.",
                        "Only the gates that switch opens (the groups come from the data, not from "
                        "a list written by hand). Back to the general entry at every level."),
    "desc.movers": ("I personaggi che il gioco sposta: avanti, verso le loro tappe, "
                    "sul suolo di collisione (scoperta 317). Senza Bugs nella scena chi "
                    "punta lui resta fermo; niente urti fra oggetti ne' vagabondaggio. "
                    "Torna a No a ogni livello; il livello si ricostruisce.",
                    "The characters the game moves: forward, towards their waypoints, on "
                    "the collision ground (finding 317). Without Bugs in the scene those "
                    "who aim at him stand still; no bumping between objects and no "
                    "wandering. Back to No at every level; the level is rebuilt."),
    "desc.clones": ("Template che le regole degli oggetti fanno comparire. Le scelte di "
                   "preferences.py si vedono sempre. Tasto [[clones]].",
                   "Templates spawned by object rules. The choices in preferences.py "
                   "are always shown. Key [[clones]]."),
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
    "video.distant": ("Texture lontane", "Distant textures"),
    "video.distant.pc": ("come il PC", "like the PC"),
    "video.distant.smooth": ("morbide", "smooth"),
    "video.uv": ("Coordinate texture", "Texture coordinates"),
    "video.uv.pc": ("PC, scheda NVIDIA/Intel", "PC, NVIDIA/Intel card"),
    "video.uv.amd": ("PC, scheda AMD", "PC, AMD card"),
    "video.uv.psx": ("PlayStation", "PlayStation"),
    "video.fov": ("Campo visivo", "Field of view"),
    "video.fov.pc": ("(come il PC)", "(like the PC)"),
    "desc.fullscreen": ("Anche Alt+Invio.", "Also Alt+Enter."),
    "desc.filter": ("Bilineare come il PC, o i texel netti. Tasto [[filter]].",
                    "Bilinear like the PC, or sharp texels. Key [[filter]]."),
    "desc.scale": ("Ingrandisce le texture con scale2x/scale3x.",
                   "Upscales textures with scale2x/scale3x."),
    "desc.color": ("Il PC usa il colore dei vertici com'è (scoperta 268), la PSX lo raddoppia.",
                    "The PC uses vertex colour as is (finding 268), the PSX doubles it."),
    "desc.distant": ("Come il PC: niente mipmap, pi\u00f9 nitide da lontano ma sfarfallano mentre ti muovi. Morbide: le mipmap, quiete ma impastate.",
                     "Like the PC: no mipmaps, sharper far away but they shimmer as you move. Smooth: mipmaps, quiet but blurred."),
    "desc.uv": ("Il PC legge i byte come byte/255, li limita fra 0,01 e 0,99 e ripete la texture (scoperta 341): il lato opposto si mescola al bordo solo sulle texture sotto i 50 texel. Col driver AMD il gioco taglia una striscia esterna più larga; PlayStation è la regola (misura − 1).",
                "The PC reads the bytes as byte/255, clamps them between 0.01 and 0.99 and repeats the texture (finding 341): the opposite side mixes in at the edge only on textures under 50 texels. With an AMD driver the game cuts a wider outer strip; PlayStation is the (size − 1) rule."),
    "desc.fov": ("Angolo verticale. 51° è la prospettiva del gioco (scoperta 327): con una finestra 4:3 l'immagine è la sua.",
                 "Vertical angle. 51° is the game's perspective (finding 327): with a 4:3 window the picture is its own."),

    # general options
    "general.title": ("Opzioni generali", "General options"),
    "general.language": ("Lingua / Language", "Language / Lingua"),
    "general.status_bar": ("Barra di stato", "Status bar"),
    "desc.language": ("Cambia subito, senza ricaricare il livello.",
                    "Changes at once, without reloading the level."),
    "desc.status_bar": ("Livello, coordinate del gioco e in metri, velocità della camera.",
                   "Level, game and metre coordinates, camera speed."),

    # help
    "help.title": ("Aiuto", "Help"),
    "help.reset": ("Camera al punto di partenza", "Camera back to the start"),
    "help.pause": ("Ferma / riavvia le animazioni", "Pause / resume animations"),
    "help.hide_ui": ("Copri / scopri l'interfaccia", "Hide / show the interface"),

    # keys and gamepad (Help and General options, as in the CTR viewer)
    "help.keyboard": ("Tastiera", "Keyboard"),
    "help.gamepad": ("Gamepad", "Gamepad"),
    "desc.help_keyboard": ("Tutti i comandi di tastiera e mouse. I tasti con una sola funzione si "
                           "possono cambiare qui.",
                           "All keyboard and mouse controls. Keys with a single function can be "
                           "changed here."),
    "desc.help_gamepad": ("Comandi del gamepad su un controller disegnato (solo informativo).",
                          "Gamepad controls on a drawn controller (information only)."),
    "general.keys": ("Tasti e gamepad", "Keys and gamepad"),
    "desc.general_keys": ("I tasti (quelli con una sola funzione si cambiano) e i comandi del gamepad.",
                          "The keys (those with a single function can be changed) and the gamepad controls."),
    "general.gamepad": ("Gamepad", "Gamepad"),
    "desc.general_gamepad": ("Usa il primo gamepad collegato: camera e menu. No lo ignora.",
                             "Uses the first gamepad connected: camera and menu. No ignores it."),
    "keys.camera_up": ("Camera su", "Camera up"),
    "keys.camera_down": ("Camera giù", "Camera down"),
    "keys.level_prev": ("Livello precedente", "Previous level"),
    "keys.level_next": ("Livello successivo", "Next level"),
    "keys.tps_down": ("Tick al secondo: meno", "Ticks per second: fewer"),
    "keys.tps_up": ("Tick al secondo: più", "Ticks per second: more"),
    "keys.menu_back": ("Menu indietro", "Menu back"),
    "keys.menu_back_alt": ("Menu indietro (secondo tasto)", "Menu back (second key)"),
    "keys.locked.esc": ("Apri / chiudi il menu, annulla la cattura del tasto",
                        "Open / close the menu, cancel the key capture"),
    "keys.locked.enter": ("Conferma; Alt + Invio: schermo intero", "Confirm; Alt + Enter: full screen"),
    "keys.locked.space": ("Nel menu: conferma", "In the menu: confirm"),
    "keys.locked.w": ("Camera avanti, menu su", "Camera forward, menu up"),
    "keys.locked.a": ("Camera a sinistra, menu: valore precedente", "Camera left, menu: previous value"),
    "keys.locked.s": ("Camera indietro, menu giù", "Camera back, menu down"),
    "keys.locked.d": ("Camera a destra, menu: valore successivo", "Camera right, menu: next value"),
    "keys.locked.up": ("Menu su", "Menu up"),
    "keys.locked.down": ("Menu giù", "Menu down"),
    "keys.locked.left": ("Menu: valore precedente", "Menu: previous value"),
    "keys.locked.right": ("Menu: valore successivo", "Menu: next value"),
    "keys.locked.pageup": ("Menu: 10 righe su", "Menu: 10 rows up"),
    "keys.locked.pagedown": ("Menu: 10 righe giù", "Menu: 10 rows down"),
    "keys.locked.shift": ("Camera più veloce, valori del menu x10", "Faster camera, menu values x10"),
    "keys.locked.ctrl": ("Camera più lenta", "Slower camera"),
    "keys.locked.alt": ("Alt + Invio: schermo intero, Alt + F4: esci", "Alt + Enter: full screen, Alt + F4: quit"),
    "keys.locked.f4": ("Alt + F4: esci", "Alt + F4: quit"),
    "keys.locked.num_tps": ("Tick al secondo (fisso, oltre ai tasti qui sopra)",
                            "Ticks per second (fixed, besides the keys above)"),
    "keys.cap.prtsc": ("Stamp", "PrtSc"),
    "keys.cap.space": ("Spazio", "Space"),
    "keys.no_key": ("(nessun tasto)", "(no key)"),
    "keys.press_key": ("Premi un tasto... (Esc = annulla)", "Press a key... (Esc = cancel)"),
    "keys.reset": ("Ripristina tasti predefiniti", "Restore default keys"),
    "keys.row.esc": ("Esc - Apri / chiudi il menu", "Esc - Open / close the menu"),
    "keys.row.nav": ("Frecce o WASD - Naviga nel menu", "Arrows or WASD - Navigate the menu"),
    "keys.row.confirm": ("Invio / Spazio - Conferma", "Enter / Space - Confirm"),
    "keys.row.move": ("WASD - Muovi la camera", "WASD - Move the camera"),
    "keys.row.shift": ("Shift / Ctrl - Camera più veloce / più lenta", "Shift / Ctrl - Faster / slower camera"),
    "keys.row.page": ("PagSu / PagGiù - Menu: 10 righe; Shift + ← → valori x10",
                      "PgUp / PgDn - Menu: 10 rows; Shift + ← → values x10"),
    "keys.row.num_tps": ("Num + / Num - - Tick al secondo", "Num + / Num - - Ticks per second"),
    "keys.row.fullscreen": ("Alt + Invio - Schermo intero", "Alt + Enter - Full screen"),
    "keys.row.quit": ("Alt + F4 - Esci", "Alt + F4 - Quit"),
    "keys.row.mouse_look": ("Mouse destro - Guarda; nel menu indietro", "Right mouse - Look; in the menu back"),
    "keys.row.wheel": ("Rotella - Velocità della camera; nel menu cambia valore",
                       "Wheel - Camera speed; in the menu change value"),
    "keys.reverted": ("Un'azione era rimasta senza tasto: tornano i tasti dell'ultimo salvataggio.",
                      "An action was left without a key: the last saved keys are back."),
    "keys.cancelled": ("Cambio tasto annullato.", "Key change cancelled."),
    "keys.press_new": ("{action}: premi il nuovo tasto (Esc = annulla).",
                       "{action}: press the new key (Esc = cancel)."),
    "keys.defaults_restored": ("Tasti predefiniti ripristinati e salvati.", "Default keys restored and saved."),
    "keys.saved": ("{action}: {key}. Salvato.", "{action}: {key}. Saved."),
    "keys.not_saved_yet": ("{action}: {key}. Non ancora salvato, ancora senza tasto: {missing}.",
                           "{action}: {key}. Not saved yet, still without a key: {missing}."),
    "keys.is_locked": ("{key} è bloccato: ha già più funzioni.", "{key} is locked: it already has several functions."),
    "keys.is_system": ("{key} non si può usare: è riservato a Windows o alla tastiera.",
                       "{key} cannot be used: Windows or the keyboard reserve it."),
    "keys.in_use": ("{key} è già usato da: {owner}. Toglilo prima da lì (clic destro).",
                    "{key} is already used by: {owner}. Remove it there first (right click)."),
    "keys.unsupported": ("{key} non è supportato.", "{key} is not supported."),
    "keys.removed": ("{key} tolto da {action}. Assegna un nuovo tasto prima di uscire, o tornano i tasti "
                     "dell'ultimo salvataggio.",
                     "{key} removed from {action}. Give it a new key before leaving, or the last saved "
                     "keys come back."),
    "keys.legend": ("Arancione = usato  |  Grigio = libero  |  Clic su una riga: nuovo tasto  |  "
                    "Clic destro: togli tasto  |  Lucchetto = bloccato",
                    "Orange = used  |  Grey = free  |  Click a row: new key  |  Right click a row: "
                    "remove key  |  Padlock = locked"),
    "keys.mouse_help": ("Mouse: tasto destro - guarda (nel menu: indietro), rotella - velocità della "
                        "camera (nel menu: cambia valore), tasto sinistro - clic nel menu",
                        "Mouse: right button - look (in the menu: back), wheel - camera speed (in the "
                        "menu: change value), left button - click in the menu"),
    "keys.locked": ("bloccato", "locked"),
    "keys.free": ("libero", "free"),
    "pad.title": ("Comandi gamepad (solo informativo)", "Gamepad controls (information only)"),
    "pad.connected": ("collegato: {name}", "connected: {name}"),
    "pad.none": ("nessun gamepad collegato", "no gamepad connected"),
    "pad.hint": ("{keys} / Cerchio: indietro  |  Esc / Start: chiudi il menu",
                 "{keys} / Circle: back  |  Esc / Start: close the menu"),
    "pad.select": ("Select (Share, Back)", "Select (Share, Back)"),
    "pad.start": ("Start (Options)", "Start (Options)"),
    "pad.l1": ("L1 (LB)", "L1 (LB)"),
    "pad.r1": ("R1 (RB)", "R1 (RB)"),
    "pad.l2": ("L2 (LT)", "L2 (LT)"),
    "pad.r2": ("R2 (RT)", "R2 (RT)"),
    "pad.triangle": ("Triangolo (Y)", "Triangle (Y)"),
    "pad.circle": ("Cerchio (B)", "Circle (B)"),
    "pad.cross": ("Croce (A)", "Cross (A)"),
    "pad.square": ("Quadrato (X)", "Square (X)"),
    "pad.dpad": ("Croce direzionale", "D-pad"),
    "pad.left_stick": ("Levetta sinistra (L3)", "Left stick (L3)"),
    "pad.right_stick": ("Levetta destra (R3)", "Right stick (R3)"),
    "pad.select_does": ("Copri / scopri l'interfaccia (come F1)", "Hide / show the interface (like F1)"),
    "pad.start_does": ("Apri / chiudi il menu (come Esc)", "Open / close the menu (like Esc)"),
    "pad.l1_does": ("Camera giù", "Camera down"),
    "pad.r1_does": ("Camera su", "Camera up"),
    "pad.l2_does": ("Tenuto: velocità della camera giù", "Held: camera speed down"),
    "pad.r2_does": ("Tenuto: velocità della camera su", "Held: camera speed up"),
    "pad.circle_does": ("Menu indietro", "Menu back"),
    "pad.cross_does": ("Conferma. Tenuto: camera più veloce", "Confirm. Held: faster camera"),
    "pad.dpad_does": ("Muovi la camera (come WASD), naviga nel menu", "Move the camera (like WASD), navigate the menu"),
    "pad.left_stick_does": ("Muovi la camera. Pressione: nessuna funzione", "Move the camera. Press: no function"),
    "pad.right_stick_does": ("Guarda. Pressione: nessuna funzione", "Look around. Press: no function"),
    "pad.nothing": ("Nessuna funzione", "No function"),

    # Camera and points (glitch hunting, stage 3)
    "level.camera": ("Camera e punti", "Camera and points"),
    "desc.camera": ("Segnalibri di camera di questo livello e il punto ombra da copiare.",
                    "Camera bookmarks for this level and the shadow point to copy."),
    "camera.title": ("Camera e punti — {level}", "Camera and points — {level}"),
    "camera.now": ("Camera", "Camera"),
    "camera.shadow_point": ("Punto ombra", "Shadow point"),
    "camera.no_ground": ("nessun terreno sotto", "no ground below"),
    "camera.area": ("area {area}", "area {area}"),
    "camera.show_shadow": ("Mostra l'ombra", "Show the shadow"),
    "desc.show_shadow": ("Un cerchio nero dove cadrebbe Bugs dalla camera: il suolo che trova "
                         "la query del gioco (heightmap di collisione, prima lastra sotto; niente "
                         "box degli oggetti). Il bordo si vede anche attraverso il terreno.",
                         "A black circle where Bugs would land from the camera: the ground the "
                         "game's query finds (collision heightmap, first slab below; no object "
                         "boxes). The rim shows through the terrain too."),
    "camera.add": ("Aggiungi segnalibro qui", "Add a bookmark here"),
    "desc.camera_add": ("Salva posizione e direzione della camera nelle impostazioni, per "
                        "questo livello.",
                        "Saves the camera's position and direction in the settings, for this level."),
    "camera.copy_lua": ("Copia il punto per BizHawk (Lua)", "Copy the point for BizHawk (Lua)"),
    "desc.copy_lua": ("Negli appunti una voce di tabella Lua { X = …, Y = …, Z = … }, come i "
                      "waypoint di BBLIT_Tasing.lua.",
                      "Puts a Lua table entry { X = …, Y = …, Z = … } on the clipboard, like the "
                      "waypoints of BBLIT_Tasing.lua."),
    "camera.copy_all_lua": ("Copia tutti i segnalibri per BizHawk", "Copy every bookmark for BizHawk"),
    "desc.copy_all_lua": ("Negli appunti una tabella Lua con il punto ombra di ogni segnalibro "
                          "di questo livello.",
                          "Puts a Lua table with the shadow point of every bookmark of this "
                          "level on the clipboard."),
    "camera.copied": ("copiato ✓", "copied ✓"),
    "camera.bookmarks": ("Segnalibri di questo livello", "Bookmarks of this level"),
    "camera.no_bookmarks": ("Nessun segnalibro", "No bookmarks"),
    "camera.bookmark": ("Segnalibro {n}", "Bookmark {n}"),
    "desc.bookmark": ("Apre il segnalibro: vai qui, sostituisci, copia, elimina.",
                      "Opens the bookmark: go there, replace, copy, delete."),
    "bookmark.title": ("{name} — {level}", "{name} — {level}"),
    "bookmark.go": ("Vai qui", "Go here"),
    "desc.bookmark_go": ("Chiude il menu con la camera nel punto e nella direzione salvati.",
                         "Closes the menu with the camera at the saved point and direction."),
    "bookmark.replace": ("Sostituisci con la camera attuale", "Replace with the current camera"),
    "bookmark.replaced": ("sostituito ✓", "replaced ✓"),
    "bookmark.delete": ("Elimina", "Delete"),
    "bookmark.confirm_delete": ("Conferma: elimina", "Confirm: delete"),
    "desc.bookmark_delete": ("Al primo Invio chiede conferma; al secondo toglie il segnalibro "
                             "dalle impostazioni.",
                             "The first Enter asks for confirmation; the second removes the "
                             "bookmark from the settings."),
    # export: comments in the copied text
    "export.shadow": ("punto ombra", "shadow point"),
    "export.camera_no_ground": ("camera, nessun terreno sotto", "camera, no ground below"),
    "export.table_comment": ("segnalibri del viewer, punto ombra in unità del gioco (Y negativa in alto)",
                             "viewer bookmarks, shadow point in game units (Y negative is up)"),
    "export.table_name": ("punti", "points"),

}


def set_language(language: str) -> None:
    global _language
    _language = language if language in LANGUAGES else "en"


def language() -> str:
    return _language


# "[[action]]" in a text is the key bound to that action now (keybinds):
# the viewer sets the function that names it
key_of_action = None


def t(item_key: str, **fields) -> str:
    """The key's text in the current language; the key itself if missing."""
    pair = TEXTS.get(item_key)
    if pair is None:
        return item_key
    label_text = pair[LANGUAGES.index(_language)]
    label_text = label_text.format(**fields) if fields else label_text
    if "[[" in label_text:
        label_text = re.sub(r"\[\[(\w+)\]\]",
                            lambda m: key_of_action(m.group(1)) if key_of_action else m.group(1), label_text)
    return label_text
