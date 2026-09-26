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
    # the frame drawn before a level is built: loading blocks the window, and
    # without it the last frame of the level that is leaving stays on screen
    "status.loading": ("Caricamento {name}...", "Loading {name}..."),
    "status.pick": ("Alt+clic: cosa c'e' qui", "Alt+click: what is here"),

    # the selector (Alt+click, window/picking.py)
    "pick.title": ("Seleziona / Cosa c'e' qui", "Select / What is here"),
    "pick.desc": ("Alt+clic su un pixel dice cosa c'e' li'. Alt+clic di nuovo sullo stesso punto "
                  "scorre la pila, dal piu' vicino al piu' lontano, e dopo l'ultimo passa da "
                  "\"niente selezionato\". Il tasto destro, cliccato senza girare la camera, "
                  "deseleziona. Si seleziona solo cio' che e' "
                  "disegnato: un tratto senza faccia disegnata si prende lo stesso, perche' il suo "
                  "pannello c'e'.",
                  "Alt+click on a pixel says what is there. Alt+click the same spot again steps down "
                  "the stack, nearest to farthest, and after the last one comes \"nothing "
                  "selected\". A right click that does not turn the camera clears the selection. "
                  "Only what is drawn can be picked: a run with "
                  "nothing drawn on it is still picked, because its panel is there."),
    "pick.enabled": ("Seleziona con Alt+clic", "Select with Alt+click"),
    "pick.copy": ("Copia la scheda", "Copy the card"),
    "pick.desc_copy": ("Mette tutta la scheda negli appunti.",
                       "Puts the whole card on the clipboard."),
    "pick.clear": ("Deseleziona", "Clear the selection"),
    "pick.none": ("Niente selezionato: Alt+clic su un pixel.",
                  "Nothing selected: Alt+click on a pixel."),
    "pick.of": ("Selezione {n} di {total} su questo pixel", "Selected {n} of {total} on this pixel"),
    "pick.group": ("Gruppo: {name}", "Group: {name}"),
    "pick.kind.terrain": ("Terreno", "Terrain"),
    "pick.kind.props": ("Oggetti", "Objects"),
    "pick.kind.sky": ("Cielo", "Sky"),
    "pick.kind.clones": ("Template clonati", "Cloned templates"),
    "pick.kind.flag": ("Flag", "Flag"),
    "pick.part.label": ("scritta", "words"),
    "pick.part.lines": ("contorno", "outline"),
    "pick.point": ("Punto di gioco {x:.0f}, {y:.0f}, {z:.0f} - {m:.1f} m dalla camera",
                   "Game point {x:.0f}, {y:.0f}, {z:.0f} - {m:.1f} m from the camera"),
    "pick.run": ("Tratto: {ends}", "Run: {ends}"),
    "pick.height": ("Alto {top:.0f}, basso {base:.0f} - dislivello {drop:.0f} unita' ({metres:.2f} m)",
                    "Top {top:.0f}, base {base:.0f} - drop {drop:.0f} units ({metres:.2f} m)"),
    "pick.block": ("Blocco: pavimento {floor:.0f}, soffitto {ceiling:.0f}",
                   "Block: floor {floor:.0f}, ceiling {ceiling:.0f}"),
    "pick.stops_wall": ("FERMA fino al soffitto del blocco ({m:.1f} m)",
                        "STOPS you up to the block's ceiling ({m:.1f} m)"),
    "pick.edge": ("EDGE, bordo del pavimento sul vuoto: sul lato libero la heightmap non ha "
                  "suolo (0x7E). Spessore disegnato {m:.2f} m, preso dalla faccia che il gioco "
                  "disegna qui; dove non ne disegna nessuna, una sotto-cella",
                  "EDGE, the rim of a floor over the void: the heightmap has no ground on the "
                  "free side (0x7E). Drawn thickness {m:.2f} m, taken from the face the game "
                  "draws here; one sub-cell where it draws none"),
    "pick.step_real": ("Gradino vero: sotto c'e' suolo", "A real step: below is ground"),
    "pick.drop_wall": ("MURO da dislivello: {m:.2f} m, oltre il salto di Bugs ({jump} unita'). "
                       "Disegnato e chiamato come muro",
                       "WALL by drop: {m:.2f} m, more than Bugs's jump ({jump} units). "
                       "Drawn and named as a wall"),
    "pick.climbable": ("Si supera: {m:.2f} m, sotto il salto di Bugs ({jump} unita')",
                       "You can get up: {m:.2f} m, under Bugs's jump ({jump} units)"),
    "pick.free": ("Lato libero ({dx}, {dz})", "Free side ({dx}, {dz})"),
    "pick.seen": ("Il gioco ci disegna qualcosa sopra", "The game draws something on it"),
    "pick.unseen": ("INVISIBILE: il gioco non ci disegna niente",
                    "UNSEEN: the game draws nothing on it"),
    "pick.face": ("Faccia del gioco: {d:+.1f} dal piano, {tilt:.1f} gradi dalla verticale, "
                  "{off:.1f} gradi fuori dal piano",
                  "Game face: {d:+.1f} from the plane, {tilt:.1f} degrees off vertical, "
                  "{off:.1f} degrees off the plane"),

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
    "data.no_bze": ("Nessun file .bze in {c}: la cartella non è cambiata.",
                    "No .bze files in {c}: the folder has not changed."),
    "data.no_bze_short": ("nessun .bze", "no .bze"),
    "menu.load_error": ("{n} non si costruisce (errors.txt)", "{n} does not build (errors.txt)"),
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
    "load.eras": ("Ere", "Eras"),
    "load.desc_eras": ("L'Era selector (LS01): la vista d'insieme e il centro di ogni era.",
                       "The Era selector (LS01): the overview and the centre of each era."),
    "load.desc_era": ("I livelli dell'era, per titolo e parte.",
                        "The era's levels, by title and part."),
    "load.desc_extra": ("Le varianti _8 fuori dalla tabella dei livelli.",
                          "The _8 variants missing from the level table."),
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
    "extra.cutscenes": ("Filmati", "Cutscenes"),
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
    "level.walls": ("Muri", "Walls"),
    "desc.walls": ("I muri della heightmap di collisione: muri duri, gradini, box delle aree, "
                   "e da quale lato vederli.",
                   "The walls of the collision heightmap: hard walls, steps, area boxes, and "
                   "which side to see them from."),
    "level.walls.off": ("No", "No"),
    "level.walls.all": ("Tutti", "All"),
    "level.walls.unseen": ("Solo invisibili", "Only invisible"),
    "level.steps": ("Gradini", "Steps"),
    "desc.steps": ("I gradini di piu' di 100 unita' della heightmap, in rosa: fermano solo "
                   "salendo, dal lato basso (STEP WALL, sigla STP); dal lato alto STEP WALL · "
                   "OUTSIDE. \"Tutti\" anche quelli coperti da una faccia opaca del livello (un "
                   "gradino ferma comunque), \"Solo invisibili\" quelli senza niente davanti. "
                   "Dove il gioco ha una faccia sul gradino si colora quella, coi suoi spigoli.",
                   "The heightmap's steps of more than 100 units, in pink: they stop you only "
                   "going up, from the low side (STEP WALL, short STP); from the high side STEP "
                   "WALL · OUTSIDE. \"All\" also those an opaque face of the level covers (a "
                   "step stops you anyway), \"Only invisible\" those with nothing drawn over "
                   "them. Where the game has a face on the step, that face is coloured, with "
                   "its edges."),
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
    "level.gates.every": ("Tutti i cancelli", "All gates"),
    "level.gates.by_switch": ("Per interruttore", "By switch"),

    # Level options -> Animations (window/animations_page.py, game/catalog.py)
    "menu.anim": ("Animazioni", "Animations"),
    "desc.anim_page": ("Ogni oggetto del livello, per categoria, famiglia ed esemplare, costruito dai "
                       "dati; accanto a un selettore, in grigio, quante posizioni ha.",
                       "Every object of the level, by category, family and exemplar, built from the "
                       "data; beside a selector, in grey, how many positions it has."),
    "anim.all": ("Tutte le animazioni", "All animations"),
    "anim.category": ("Categoria", "Category"),
    "anim.cat.characters": ("Entità", "Characters"),
    "anim.cat.staged": ("Oggetti a stadi", "Things with stages"),
    "anim.cat.carried": ("Da prendere e spingere", "Carried and pushed"),
    "anim.cat.collectables": ("Collezionabili", "Collectables"),
    "anim.cat.effects": ("Effetti e segnali", "Effects and signs"),
    "anim.cat.opening": ("Cose che si aprono", "Things that open"),
    "anim.cat.rest": ("Il resto", "The rest"),
    "anim.family": ("Famiglia", "Family"),
    "anim.fam.model": ("Modello {n}", "Model {n}"),
    "anim.fam.sprite": ("Sprite {n}", "Sprite {n}"),
    "anim.fam.type": ("Tipo {n}", "Type {n}"),
    "anim.fam.scenery": ("Scenografia", "Scenery"),
    "anim.fam.logic": ("Logica invisibile", "Invisible logic"),
    "anim.parts": ("{n} parti", "{n} parts"),
    "anim.which": ("Esemplare", "Which one"),
    "anim.which_of": ("{k} di {n}", "{k} of {n}"),
    "anim.provenance": ("Provenienza", "Provenance"),
    "anim.prov.placed": ("posato dal file", "placed by the file"),
    "anim.prov.parked": ("parcheggiato all'origine", "parked at the origin"),
    "anim.prov.cloned": ("clonato da #{n}", "cloned by #{n}"),
    "anim.prov.held": ("agganciato a un osso di #{n}", "held at a bone of #{n}"),
    "anim.prov.never_made": ("nessuna regola lo crea", "made by no rule"),
    "anim.prov.pause_page": ("pagina del menu di pausa", "a page of the pause menu"),
    "anim.prov.script": ("copione senza modello", "a script without a model"),
    "anim.prov.sky": ("cielo, segue la camera", "sky, follows the camera"),
    "anim.prov.on_bugs": ("agganciato a Bugs dal primo tick", "on Bugs from the first tick"),
    "anim.prov.texture": ("anima una texture del livello", "animates a texture of the level"),
    "anim.spawn": ("Spawn", "Spawn"),
    "anim.spawn.ask": ("da chiedere", "to be asked"),
    "anim.spawn.merlin_helpers": ("alla prova, uno alla volta", "at the trial, one at a time"),
    "anim.when": ("Quando c'è", "When it is there"),
    "anim.when.start": ("all'inizio", "at the start"),
    "anim.when.later": ("più tardi", "later"),
    "anim.when.moment": ("un attimo", "for a moment"),
    "anim.when.never": ("mai", "never"),
    "anim.when.by_itself": ("dopo, da solo", "later, by itself"),
    "anim.when.gone": ("sparisce al primo tick", "gone at the first tick"),
    "anim.follow": ("Segui con la camera", "Follow with the camera"),
    "desc.anim_follow": ("La riga selezionata inquadra la sua cosa, coi tasti, col pad o col mouse.",
                         "The selected row frames its thing, with the keys, the pad or the mouse."),
    "anim.none": ("Niente da mostrare.", "Nothing to show."),
    "anim.none_here": ("nessuna", "none"),
    "anim.object": ("Oggetto #{n}.", "Object #{n}."),
    "anim.n_exemplar": ("{n} esemplare", "{n} exemplar"),
    "anim.n_exemplars": ("{n} esemplari", "{n} exemplars"),
    "anim.n_at_start": ("{n} all'inizio", "{n} at the start"),
    "anim.cat_rule.characters": ("Entità: chi ha una testa, cioè uno scheletro di almeno {parts} parti con "
                                 "almeno due stati o due animazioni, più Bugs.",
                                 "Characters: whoever has a head, that is a skeleton of at least {parts} "
                                 "parts with at least two states or two animations, and Bugs."),
    "anim.cat_rule.collectables": ("Collezionabili: un tocco di Bugs li porta via, o li aggiunge a un "
                                   "contatore del salvataggio (carote, orologi, carote d'oro).",
                                   "Collectables: a touch by Bugs takes them away, or adds them to a "
                                   "counter of the save (carrots, clocks, golden carrots)."),
    "anim.cat_rule.carried": ("Da prendere e spingere: la cassa da spingere, quello che Bugs può prendere "
                              "in mano e quello che ha regole per quando è preso, lasciato o posato.",
                              "Carried and pushed: the pushable crate, what Bugs can pick up and what "
                              "has rules for being held, let go or put down."),
    "anim.cat_rule.opening": ("Cose che si aprono: il box cambia con lo stato (cancelli, porte, massi).",
                              "Things that open: the box changes with the state (gates, doors, "
                              "boulders)."),
    "anim.cat_rule.effects": ("Effetti e segnali: sprite che girano, proiettili, scritte, fiamme e aloni, "
                              "e i checkpoint.",
                              "Effects and signs: looping sprites, bullets, texts, flames and glows, and "
                              "the checkpoints."),
    "anim.cat_rule.staged": ("Oggetti a stadi: più di uno stato e nessuna delle categorie prima (ponti, "
                             "barili, chi cammina senza scheletro), e le piattaforme (trampolini, "
                             "ascensori, altalene, nastri).",
                             "Things with stages: more than one state and none of the categories "
                             "before (bridges, barrels, what walks without a skeleton), and the "
                             "platforms (trampolines, lifts, see-saws, conveyors)."),
    "anim.cat_rule.rest": ("Il resto: la scenografia (un modello e niente da scegliere, come le rotaie "
                           "delle miniere) e la logica invisibile (trigger, regia della camera, animatori "
                           "di texture).",
                           "The rest: the scenery (a model and nothing to choose, like the rails of the "
                           "mines) and the invisible logic (triggers, the camera director, texture "
                           "animators)."),
    "names.bugs": ("Bugs", "Bugs"),
    "names.merlin": ("Merlino", "Merlin"),
    "names.merlin_trial": ("Merlino-Prova({n})", "Merlin-Trial({n})"),
    "names.merlin_helper": ("Aiutante mago", "Magician helper"),
    "names.pirate": ("Pirata", "Pirate"),
    "names.crab": ("Granchio", "Crab"),
    "names.time_machine": ("Macchina del tempo", "Time machine"),
    "anim.n_by_itself": ("{n} nascono dopo da soli", "{n} come later by themselves"),
    "anim.n_by_bugs": ("{n} nascono quando Bugs fa qualcosa", "{n} come when Bugs does something"),
    "anim.new_game": ("«All'inizio» vale per una partita nuova: con un salvataggio le carote d'oro e "
                      "gli orologi già presi spariscono al primo tick.",
                      "\"At the start\" is a new game: with a save, the golden carrots and clocks "
                      "already taken are gone at the first tick."),
    "anim.n_never": ("{n} che nessuna regola crea", "{n} made by no rule"),
    "anim.why.there": ("C'è all'inizio (dopo il primo tick di una partita nuova).",
                       "It is there at the start (after the first tick of a new game)."),
    "anim.why.clones_off": ("C'è all'inizio, ma Template clonati è su Spenti.",
                            "It is there at the start, but Cloned templates is Off."),
    "anim.why.all_on": ("Con Template clonati su Tutti lo vedi lo stesso.",
                        "With Cloned templates on All it is shown anyway."),
    "anim.why.invisible": ("Non ha un modello: nel gioco non si vede.",
                           "It has no model: in the game it is not seen."),
    "anim.why.never_made": ("Nessuna regola del livello lo crea: in partita non esiste.",
                            "No rule of the level makes it: it never exists while playing."),
    "anim.why.passing": ("C'è solo un attimo: lo fa #{parent} e sparisce da solo.",
                         "It is there only for a moment: #{parent} makes it and it goes by itself."),
    "anim.why.touch": ("Nasce quando Bugs tocca #{parent}.", "It is born when Bugs touches #{parent}."),
    "anim.why.held": ("Nasce quando Bugs prende o lascia #{parent}.",
                      "It is born when Bugs picks up or lets go of #{parent}."),
    "anim.why.state_of": ("Nasce quando #{parent} si trova in una certa situazione (atterrato, urtato...).",
                          "It is born when #{parent} is in a given situation (landed, bumped...)."),
    "anim.why.hit": ("Nasce quando #{parent} viene colpito.", "It is born when #{parent} is hit."),
    "anim.why.near": ("Nasce quando Bugs arriva a {metres:.1f} m da #{parent}.",
                      "It is born when Bugs comes within {metres:.1f} m of #{parent}."),
    "anim.why.far": ("Nasce quando Bugs è a più di {metres:.1f} m da #{parent}.",
                     "It is born when Bugs is more than {metres:.1f} m from #{parent}."),
    "anim.why.button": ("Nasce quando si preme un tasto (regola di #{parent}).",
                        "It is born when a button is pressed (a rule of #{parent})."),
    "anim.why.byte_level": ("Nasce quando cambia il byte {index} del livello (lo scrivono: {writers}).",
                            "It is born when level byte {index} changes (written by: {writers})."),
    "anim.why.byte_save": ("Nasce quando cambia il byte {index} del salvataggio (lo scrivono: {writers}).",
                           "It is born when save byte {index} changes (written by: {writers})."),
    "anim.why.nobody": ("nessuna regola del livello", "no rule of the level"),
    "anim.why.chain": ("Nasce così: {steps} → #{parent} lo clona.",
                       "It is born this way: {steps} → #{parent} clones it."),
    "anim.step.button": ("usi #{parent} col tasto Azione", "you use #{parent} with the Action button"),
    "anim.step.touch": ("Bugs tocca #{parent}", "Bugs touches #{parent}"),
    "anim.step.near": ("Bugs arriva a {metres:.1f} m da #{parent}", "Bugs comes within {metres:.1f} m of #{parent}"),
    "anim.step.zone": ("Bugs è nella zona {zone}", "Bugs is in zone {zone}"),
    "anim.step.object": ("#{parent} cambia un byte", "#{parent} changes a byte"),
    "anim.anim": ("Animazione", "Animation"),
    "anim.desc_anim": ("Il ruolo di animazione {r} dell'oggetto (i numeri sono del livello).",
                       "The object's animation role {r} (the numbers are the level's)."),
    "anim.cannot": ("nessuna regola lo crea", "made by no rule"),
    "anim.flow": ("Come scorre", "How it runs"),
    "anim.flow.loop": ("ciclo", "loop"),
    "anim.flow.still": ("ferma", "still"),
    "desc.anim_flow": ("Ciclo: l'animazione gira. Ferma: resta sul fotogramma qui sotto.",
                       "Loop: the animation runs. Still: it stays on the frame below."),
    "anim.frame": ("Fotogramma", "Frame"),
    "desc.anim_frame": ("Scegliere un fotogramma ferma l'animazione lì. Maiusc + freccia salta di dieci.",
                        "Choosing a frame holds the animation there. Shift + arrow jumps ten."),
    "anim.why.other": ("Nasce più tardi, per una regola di #{parent} che il viewer non sa ancora dire a parole.",
                       "It is born later, by a rule of #{parent} the viewer cannot yet put in words."),
    "anim.why.by_itself": ("Nasce da solo dopo il primo tick, senza che Bugs faccia niente.",
                           "It comes by itself after the first tick, with Bugs doing nothing."),
    "anim.why.gone_first_tick": ("Il file lo posa, ma il suo primo tick lo cancella.",
                                 "The file places it, but its first tick deletes it."),
    "anim.why.later": ("Nasce più tardi: chi lo crea non c'è all'inizio.",
                       "It is born later: what makes it is not there at the start."),
    "anim.because.player": ("È Bugs.", "It is Bugs."),
    "anim.because.skeleton": ("Ha uno scheletro di {n} parti.", "It has a skeleton of {n} parts."),
    "anim.because.touch_gone": ("Un tocco di Bugs lo porta via.", "A touch by Bugs takes it away."),
    "anim.because.touch_counts": ("Un tocco di Bugs lo conta.", "A touch by Bugs counts it."),
    "anim.because.crate": ("La cassa da spingere.", "The pushable crate."),
    "anim.because.pick_up": ("Bugs lo può prendere.", "Bugs can pick it up."),
    "anim.because.held": ("Ha regole per quando è preso, lasciato o posato.",
                          "It has rules for being held, let go or put down."),
    "anim.because.box": ("Il suo box cambia con lo stato.", "Its box changes with its state."),
    "anim.because.sprite_loop": ("Uno sprite che gira.", "A looping sprite."),
    "anim.because.bullet": ("Un proiettile.", "A bullet."),
    "anim.because.text": ("Una scritta.", "A text."),
    "anim.because.sprite": ("Uno sprite.", "A sprite."),
    "anim.because.checkpoint": ("Un checkpoint.", "A checkpoint."),
    "anim.because.states": ("Ha più di uno stato.", "It has more than one state."),
    "anim.because.platform": ("Una piattaforma (tipo {n}).", "A platform (type {n})."),
    "anim.because.scenery": ("Scenografia: ha un modello e nient'altro da scegliere.",
                             "Scenery: it has a model and nothing else to choose."),
    "anim.because.logic": ("Logica invisibile: trigger, regia della camera, animatori di texture.",
                           "Invisible logic: triggers, the camera director, texture animators."),
    "level.movers": ("Personaggi in movimento", "Moving characters"),
    "level.clones": ("Template clonati", "Cloned templates"),
    "level.clones.off": ("Spenti", "Off"),
    "level.clones.in_level": ("Nel livello", "In the level"),
    "level.clones.all": ("Tutti", "All"),

    # descriptions (bottom line)
    "desc.texture": ("Mostra le texture o solo il colore dei vertici. Tasto [[textures]].",
                     "Show textures or vertex colours only. Key [[textures]]."),
    "desc.props": ("Oggetti piazzati e animati. Tasto [[props]].", "Placed and animated objects. Key [[props]]."),
    "level.area_boxes": ("Box delle aree", "Area boxes"),
    "desc.area_boxes": ("Il volume di collisione di ogni mini area (i blocchi della heightmap). "
                        "I lati fermano solo chi e' dentro (AREA WALL; da fuori AREA WALL · OUTSIDE: "
                        "si passa). La cima ferma la testa di un salto (JUMP CEILING, da sotto): "
                        "l'origine di Bugs si ferma circa 410 piu' in basso.",
                        "The collision volume of each mini area (the heightmap blocks). The sides "
                        "stop only who is inside (AREA WALL; from outside AREA WALL · OUTSIDE: you "
                        "pass). The top stops the head of a jump (JUMP CEILING, from below): Bugs's "
                        "origin stops about 410 lower."),
    "level.walls_outside": ("Lato di fuori", "Outside side"),
    "desc.walls_outside": ("Il lato dei muri da cui non si e' fermati (le scritte OUTSIDE): i muri duri "
                           "dal lato 0x7F, i gradini dal lato alto, i box delle aree da fuori e da "
                           "sopra. Spento, da fuori si vedono le aree senza il box davanti.",
                           "The side of the walls that does not stop you (the OUTSIDE names): the hard "
                           "walls from the 0x7F side, the steps from the high side, the area boxes from "
                           "outside and above. Off, from outside you see the areas without the box in "
                           "front."),
    "level.hole_steps": ("Gradini: bordi sui buchi", "Steps: edges over holes"),
    "level.needs_steps": ("Non fa niente finché Gradini è su No.", "Does nothing while Steps is No."),
    "level.needs_walls": ("Non fa niente finché Muri duri, Gradini e Box delle aree sono spenti.",
                          "Does nothing while Hard walls, Steps and Area boxes are off."),
    "desc.hole_steps": ("Con Gradini, anche quelli visti da un buco 0x7E (il suo suolo e' la base della "
                        "lastra): i bordi delle piattaforme sul vuoto. Nel gioco fermano chi cade "
                        "accanto alla piattaforma, ma di solito sono solo rumore.",
                        "With Steps, also those seen from a 0x7E hole (its ground is the slab's base): "
                        "the edges of platforms over the void. In the game they stop whoever falls "
                        "next to the platform, but they are mostly noise."),
    "level.gate_links": ("Chi apre cosa", "Who opens what"),
    "level.gate_links.off": ("No", "No"),
    "level.gate_links.gates": ("Solo cancelli", "Gates only"),
    "level.gate_links.all": ("Tutti i collegamenti", "All the links"),
    "level.faces_1000": ("Portali", "Portals"),
    "level.flag_labels": ("Etichette flag", "Flag labels"),
    "level.flags_off": ("Spegni tutte le flag", "All flags off"),
    "load.previous": ("Livello precedente", "Previous level"),
    "load.next": ("Livello successivo", "Next level"),
    "desc.load_previous": ("Il livello prima di questo, nell'ordine di questa pagina (come il tasto [[level_prev]]).",
                           "The level before this one, in this page's order (as the key [[level_prev]])."),
    "desc.load_next": ("Il livello dopo questo, nell'ordine di questa pagina (come il tasto [[level_next]]).",
                       "The level after this one, in this page's order (as the key [[level_next]])."),
    "camera.reset": ("Torna al punto di partenza", "Back to the starting point"),
    "camera.paste": ("Vai al punto negli appunti", "Go to the point in the clipboard"),
    "desc.camera_paste": ("La camera 1,6 m sopra un punto copiato dal viewer o dagli script Lua "
                          "(una riga con X = … Y = … Z = …, in unità del gioco), guardando dove guarda adesso.",
                          "The camera 1.6 m above a point copied by the viewer or by the Lua scripts "
                          "(a line with X = … Y = … Z = …, in game units), looking where it looks now."),
    "camera.paste.none": ("niente punto negli appunti", "no point in the clipboard"),
    "camera.paste.other": ("il punto è di {n}", "the point is of {n}"),
    "camera.paste.done": ("{x}, {y}, {z}", "{x}, {y}, {z}"),
    "bookmark.name": ("Nome", "Name"),
    "desc.bookmark_name": ("Invio per scrivere il nome, Invio per salvarlo, Esc per lasciare com'era. "
                           "Vuoto torna \"Segnalibro N\".",
                           "Enter to write the name, Enter to save it, Esc to leave it as it was. "
                           "Empty goes back to \"Bookmark N\"."),
    "desc.camera_reset": ("La camera di partenza del livello (come il tasto [[reset_camera]]).",
                          "The level's opening camera (as the key [[reset_camera]])."),
    "desc.flags_off": ("Tutte le flag di questa pagina e di Muri tornano come all'avvio. Le "
                       "Etichette flag e le Opzioni livello restano come sono.",
                       "Every flag of this page and of Walls goes back to how it starts. Flag "
                       "labels and the Level options stay as they are."),
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
    "desc.flag_labels": ("Le scritte dentro le flag e sopra i box di collisione. Spente restano i "
                         "colori e i contorni, spariscono solo le parole. Sì a ogni avvio.",
                         "The words inside the flags and over the collision boxes. Off, the colours "
                         "and the outlines stay, only the words go. Yes at every start."),
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
    "desc.hard_walls": ("I muri 0x7F della heightmap, in blu: fermano a qualunque altezza dentro il "
                        "loro blocco, dal pavimento alla cima esatta (provato nel gioco), anche dove "
                        "non si vede niente (HARD WALL, sigla HRD); visti dal lato da cui si entra. "
                        "\"Solo invisibili\": quelli senza una parete disegnata. Dove il gioco ha una "
                        "faccia sul muro si colora quella, coi suoi spigoli; pannelli dove non c'e' "
                        "niente.",
                        "The heightmap's 0x7F walls, in blue: they stop you at any height inside "
                        "their block, from the floor to its exact top (tested in the game), even "
                        "where nothing is drawn (HARD WALL, short HRD); seen from the side you would "
                        "enter from. \"Only invisible\": those with no wall drawn. Where the game has "
                        "a face on the wall, that face is coloured, with its edges; panels where "
                        "there is nothing."),
    "desc.flags": ("Sovrapposizioni: muri, collisioni, zone di morte. Ogni "
                   "cosa ha scritto cio' che fa: un nome intero, o piu' sigle se fa piu' cose o e' "
                   "in piu' flag accese (per esempio DTH + DMG).",
                   "Overlays: walls, collisions, death zones. Each thing is "
                   "named with what it does: a full name, or short names when it does more or is "
                   "in more flags that are on (for example DTH + DMG)."),
    "desc.death_zones": ("Le zone che ti uccidono (DEATH, sigla DTH; DEATH FLOOR, DFL, quelle grandi "
                         "almeno meta' del livello: il mare, l'abisso), con respawn al checkpoint, e "
                         "quelle che ti feriscono (DAMAGE, DMG, azione 0x48). Tutte in rosso; sulla "
                         "faccia in alto tutto cio' che la zona fa, anche il respawn.",
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
                       "spigoli sopra, scuri. Tasto [[wireframe]].",
                       "Skeleton: triangle edges only. Grid: normal textures with the edges over "
                       "them, dark. Key [[wireframe]]."),
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
    "desc.clones": ("Template che le regole degli oggetti fanno comparire. Nel livello: "
                   "quelli che il gioco ha da solo, senza che Bugs faccia niente, e che "
                   "restano (le rotaie delle miniere). Tutti: anche quelli che arrivano "
                   "dopo un'azione di Bugs o che passano e spariscono. Le scelte di "
                   "preferences.py si vedono sempre. Tasto [[clones]].",
                   "Templates spawned by object rules. In the level: those the game has "
                   "by itself, with Bugs doing nothing, and that stay (the rails of the "
                   "mines). All: also those that come after something Bugs does, or come "
                   "and go. The choices in preferences.py are always shown. Key [[clones]]."),
    "desc.group": ("Solo per questa sessione: al prossimo avvio torna la scelta di "
                    "preferences.py. Il livello si ricostruisce.",
                    "This session only: the next start goes back to the choice in "
                    "preferences.py. The level is rebuilt."),

    # entity groups (preferences.py) and their states
    "group.bridges": ("Ponti levatoi", "Drawbridges"),
    "group.water_barrels": ("Barili in acqua", "Barrels in the water"),
    "group.green_crates": ("Casse verdi", "Green crates"),
    "group.anchors": ("Ancore", "Anchors"),
    "level.sky_choice": ("Cielo", "Sky"),
    "level.sky_choice.start": ("Oggetto {n} (di partenza)", "Object {n} (at the start)"),
    "level.sky_choice.default": ("Oggetto {n} (il primo)", "Object {n} (the first)"),
    "level.sky_choice.other": ("Oggetto {n} (l'altro)", "Object {n} (the other)"),
    "desc.sky_choice": ("Nel gioco i due cieli non stanno mai insieme: una regola toglie uno e "
                        "clona l'altro. Di default quello con cui il livello parte.",
                        "In the game the two skies never stand together: a rule deletes one "
                        "and clones the other. By default the one the level starts with."),
    "state.raised": ("Alzati", "Raised"),
    "state.one_third": ("Un terzo", "One third"),
    "state.two_thirds": ("Due terzi", "Two thirds"),
    "state.lowered": ("Abbassati", "Lowered"),
    "state.rising": ("Emergono", "Rising"),
    "state.floating": ("Galleggiano", "Floating"),
    "state.falling": ("Cadono", "Falling"),
    "state.on_ground": ("A terra", "On the ground"),
    "state.turning_in_air": ("Girano in aria", "Turning in the air"),
    "state.fall": ("Cadono e restano a terra", "Fall and stay on the ground"),

    # video options
    "video.title": ("Opzioni video", "Video options"),
    "video.fullscreen": ("Schermo intero", "Full screen"),
    "video.vsync": ("VSync", "VSync"),
    "video.section.screen": ("Schermo", "Screen"),
    "video.section.textures": ("Texture", "Textures"),
    "video.section.game": ("Come il gioco", "Like the game"),
    "desc.vsync": ("Aspetta lo schermo prima di mostrare il fotogramma: niente righe spezzate, al "
                   "massimo tanti fotogrammi quanti ne fa lo schermo.",
                   "Waits for the screen before showing the frame: no torn lines, at most as many "
                   "frames as the screen shows."),
    "video.defaults": ("Ripristina i predefiniti", "Restore defaults"),
    "desc.video_defaults": ("Tutte le voci di questa pagina come in un'installazione nuova.",
                            "Every entry of this page as in a new installation."),
    "general.defaults": ("Ripristina i predefiniti", "Restore defaults"),
    "general.clean_cache": ("Pulisci la cache", "Clean the cache"),
    "general.clean_cache.none": ("niente da pulire", "nothing to clean"),
    "general.clean_cache.size": ("{n} file, {mb:.0f} MB", "{n} files, {mb:.0f} MB"),
    "desc.clean_cache": ("Manda nel Cestino i pezzi salvati da un codice vecchio o per un file che non c'è "
                         "più, e le texture ingrandite (Scala texture) di tutti i livelli tranne quello "
                         "aperto: si rifanno da sole quando servono.",
                         "Sends to the Recycle Bin the pieces saved by older code or for a file that "
                         "is gone, and the enlarged textures (Texture scale) of every level but the "
                         "open one: they are made again when needed."),
    "desc.general_defaults": ("Barra di stato e gamepad come in un'installazione nuova. La lingua e "
                              "la cartella dei livelli restano come sono.",
                              "Status bar and gamepad as in a new installation. The language and the "
                              "levels folder stay as they are."),
    "general.open_folder": ("Apri la cartella dei livelli", "Open the levels folder"),
    "general.gamepad_page": ("Comandi del gamepad", "Gamepad controls"),
    "general.desc_open_folder": ("Apre in Esplora file la cartella da cui si leggono i livelli adesso: {c}",
                                 "Opens in Explorer the folder the levels are read from now: {c}"),
    "video.filter": ("Filtro texture", "Texture filtering"),
    "video.scale": ("Scala texture", "Texture scale"),
    "video.color": ("Colore", "Colour"),
    "video.color.pc": ("PC", "PC"),
    "video.color.psx": ("PSX (x2)", "PSX (x2)"),
    "video.distant": ("Texture lontane", "Distant textures"),
    "video.distant.pc": ("come il PC", "like the PC"),
    "video.distant.smooth": ("morbide", "smooth"),
    "video.uv": ("Coordinate texture", "Texture coordinates"),
    "video.uv.pc": ("Scheda NVIDIA/Intel", "NVIDIA/Intel card"),
    "video.uv.amd": ("Scheda AMD", "AMD card"),
    "video.uv.psx": ("PlayStation", "PlayStation"),
    "video.fov": ("Campo visivo", "Field of view"),
    "video.backface": ("Backface culling", "Backface culling"),
    "desc.backface": ("Come il gioco: le facce a un lato solo non si disegnano dal retro (scoperta "
                      "307), quelle a due lati restano. Spento, il viewer mostra ogni faccia: da "
                      "sopra un livello si vede il tetto, acceso si vede dentro. Spento di default.",
                      "As the game: the one-sided faces are not drawn from behind (finding 307), the "
                      "two-sided ones stay. Off, the viewer shows every face: from above a level you "
                      "see its roof, on you see inside. Off by default."),
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
    "help.about": ("Informazioni", "About"),
    "desc.help_about": ("Versione del viewer, autore e tipo di copia.",
                        "Viewer version, author and kind of copy."),
    "about.author": ("Autore", "Author"),
    "about.build": ("Copia", "Build"),
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
    "keys.row.wheel": ("Rotella - Scorre la lista del menu (velocità della camera: menu Camera)",
                       "Wheel - Scrolls the menu's list (camera speed: Camera menu)"),
    "keys.row.pick": ("Alt + clic - Cosa c'è qui (selettore); di nuovo, la cosa sotto",
                      "Alt + click - What is here (selector); again, the thing below"),
    "keys.row.unpick": ("Clic destro - Deseleziona (col selettore acceso)",
                        "Right click - Clear the selection (with the selector on)"),
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
    "keys.mouse_help": ("Mouse: tasto destro - guarda (nel menu: indietro), rotella - scorre la lista "
                        "del menu, tasto sinistro - clic nel menu",
                        "Mouse: right button - look (in the menu: back), wheel - scrolls the menu's "
                        "list, left button - click in the menu"),
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
    "camera.speed": ("Velocità camera", "Camera speed"),
    "desc.camera_speed": ("La velocità di base della camera, in metri al secondo (nella barra di "
                          "stato). Maiusc tenuto x5, Ctrl tenuto x0,2; col pad L2 / R2. All'apertura "
                          "di un livello torna a un dodicesimo della sua misura.",
                          "The camera's base speed, in metres per second (in the status bar). Shift "
                          "held x5, Ctrl held x0.2; L2 / R2 on the pad. Opening a level sets it back "
                          "to a twelfth of the level's size."),
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
