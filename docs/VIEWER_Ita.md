# BBLIT Viewer: il viewer e gli strumenti

English version: [VIEWER.md](VIEWER.md)

BBLIT Viewer è un visualizzatore di livelli a camera libera per il gioco PC
*Bugs Bunny: Lost in Time* (1999). Legge direttamente i file `.bze` dei
livelli e costruisce tutto in memoria, senza formati intermedi. Nella stessa
cartella `tools/` ci sono anche strumenti da riga di comando che estraggono le
texture ed esportano i livelli in OBJ.

- **Solo versione PC.** La versione PlayStation non è supportata.
- **Nessun dato del gioco è incluso.** Serve una propria copia del gioco. I
  file vengono solo letti, mai modificati.

---

## Come si avvia

### La release

Si scompatta la release e si avvia `BBLIT Viewer.exe`. Requisiti: Windows 10
o 11 a 64 bit e un driver grafico con OpenGL 3.3. Python e le sue librerie
sono già dentro `_internal/`: non c'è niente da installare.

### Dai sorgenti

Servono Python 3.10 o successivo e pyglet 2.x (sviluppato con pyglet 2.1).
La finestra di scelta della cartella usa `tkinter`, incluso nell'installer di
python.org.

```bash
pip install pyglet
python tools/viewer.py            # apre il menu principale
python tools/viewer.py L03A       # apre direttamente un livello (nome del file, maiuscole o minuscole)
```

Un nome di livello che non è nella cartella dei livelli apre invece il menu
principale. I comandi si lanciano dalla radice del repository.

Altri pacchetti servono solo per lavori accessori: PyInstaller per costruire
l'eseguibile, Pillow per gli script in `branding/` che disegnano icona e logo.
Gli strumenti in `tools/` usano solo la libreria standard, tranne il viewer
(pyglet).

### Da dove vengono i livelli

Il viewer ha bisogno della cartella `Datas\bze` del gioco (i file `.bze`). La
cerca in quest'ordine e usa la prima cartella che contiene almeno un `.bze`:

1. `--data CARTELLA` da riga di comando, altrimenti la cartella scelta in
   **Opzioni generali -> Cartella dei livelli** (ricordata nelle
   impostazioni). In quella finestra va bene anche la cartella del gioco: ci
   si cerca dentro `Datas\bze` (o `bze`).
2. `bze_levels/` accanto al viewer: ci si copia il contenuto di `Datas\bze`.
3. La variabile d'ambiente `BBLIT_DATA`, se impostata: una cartella del gioco
   o una cartella `Datas\bze`.

`BBLIT_DATA` è anche la cartella dati predefinita degli strumenti da riga di
comando (la loro opzione `--data`).

Senza livelli il viewer parte lo stesso, su uno sfondo blu, con una pagina
che spiega cosa copiare e i pulsanti per aprire `bze_levels`, scegliere la
cartella, riprovare, andare alle Opzioni generali o uscire. In **Carica
livello** le voci il cui file manca sono in grigio.

Il viewer legge solo il `.bze` del livello che apre, e di questo solo le
sezioni 1 (load script), 3 (texture) e 4 (modelli e terreno). I titoli dei
livelli nel menu vengono da `tools/levels.py`, non dai file del gioco.

---

## Comandi

### Nella scena

| tasto / mouse | effetto |
|---|---|
| tasto destro del mouse (tenuto) | guardarsi attorno |
| W A S D | avanti / sinistra / indietro / destra |
| E / Q | su / giù |
| Shift / Ctrl sinistro (tenuti) | 5 volte più veloce / 5 volte più lento |
| rotella | velocità di base della camera (x1,2 per scatto) |
| T | texture sì/no |
| O | oggetti (props) sì/no |
| H | cupola del cielo sì/no |
| M | fusioni semitrasparenti sì/no |
| F | wireframe sì/no |
| N | texture animate sì/no (occhi, sole, acqua: scoperta 275) |
| G | template clonati: spenti / all'avvio / tutti |
| P | ferma / riavvia tutte le animazioni (modelli, texture, oggetti che girano) |
| `-` / `+` | tick al secondo delle animazioni, da 1 a 60 (predefinito 15, misurato sulla PlayStation: scoperta 278) |
| L | filtro bilineare (come il PC, predefinito) / texel netti |
| `[` / `]` | file di livello precedente / successivo nella cartella dei livelli (in ordine alfabetico, schermate di caricamento escluse) |
| R | camera alla vista iniziale |
| Esc | apre / chiude il menu |
| Alt+Invio | schermo intero sì/no |

Esc non chiude mai il viewer: si esce con **Esci** nel menu o chiudendo la
finestra. I tasti della scena funzionano solo con un livello aperto e il menu
chiuso.

Gli oggetti che girano avanzano di 2 passaggi delle regole per tick di
animazione; questo rapporto non è misurato (scoperta 280).

### Nel menu

| tasto / mouse | effetto |
|---|---|
| Su / Giù, o W / S | scegli |
| Pag Su / Pag Giù | salta di 10 righe |
| Sinistra / Destra, o A / D, o rotella | cambia il valore (Shift: i numeri cambiano di 10 passi alla volta) |
| Invio, Spazio, clic sinistro | conferma / apri |
| Backspace, M, clic destro | indietro |
| passaggio del mouse | scegli |
| Esc | chiude il menu (si riapre dov'era rimasto) |

A menu aperto la camera sta ferma e i tasti della scena non fanno niente.
Senza un livello aperto il menu resta aperto.

---

## Le pagine del menu

| pagina | contenuto |
|---|---|
| Menu | Riprendi (in grigio senza livello), Carica livello, Opzioni livello, Opzioni video, Opzioni generali, Aiuto, Esci |
| Carica livello | le cinque ere (Età della pietra, Medioevo, Pirati, Anni '30, Dimensione X), poi Nowhere (si apre direttamente), poi **Extra**: l'Era selector (`LS01`), apribile anche al centro di ogni era, e le varianti `_8` che sono sul disco ma non nella tabella dei livelli del gioco. In una pagina d'era i livelli sono elencati per titolo e parte, col nome del file a destra (un pallino segna il livello aperto), nome completo e LevID nella descrizione, e una sezione Bonus dove l'era ne ha uno |
| Opzioni livello | **Flags** (sotto); Resa: Texture, Oggetti, Cielo, Fusioni semitrasparenti, Wireframe; Entità: Animazioni (In movimento / Ferme / Posa iniziale), Tick al secondo, Texture animate, Template clonati, più gli stati dei gruppi del livello, se ne ha |
| Opzioni video | Schermo intero, VSync, Filtro texture, Scala texture (da x1 a x4, scale2x/scale3x), Colore (PC, o PSX x2: scoperta 268), Campo visivo (da 40 a 100 gradi, predefinito 65) |
| Opzioni generali | Lingua (inglese, predefinito, o italiano), Barra di stato, Cartella dei livelli, Apri la cartella bze_levels |
| Aiuto | i tasti |

Ogni riga ha una descrizione in fondo al pannello.

**Stati dei gruppi.** In alcuni livelli lo stato di certi oggetti lo decide
il gioco durante la partita. Per questi `tools/preferences.py` fissa un
valore predefinito e dichiara le alternative (`entity_groups`); per ora li ha
solo `L03A`: ponti levatoi (alzati, un terzo, due terzi, abbassati), barili in
acqua (emergono, galleggiano) e casse verdi (cadono, a terra). Uno stato scelto
dal menu ricostruisce il livello e vale solo per la sessione.

**Barra di stato** (in basso): livello, posizione in unità del gioco e in
metri (sono gli `x,y,z` di `--camera`), velocità della camera, triangoli
disegnati, stato delle animazioni quando non sono in movimento.

La riga "BBLIT Viewer by AleMastroianni" compare in basso a destra sulla
pagina principale del menu, e ogni volta che non c'è un livello aperto.

### Flags

Sovrapposizioni per il glitch hunting. Sono **sempre spente all'avvio**, non
vengono salvate e **non hanno tasti**: si accendono in **Opzioni livello ->
Flags**, o con le opzioni da riga di comando qui sotto. Contesto: scoperte
282-288.

| flag | cosa mostra |
|---|---|
| Muri invisibili | ciò che ti ferma senza niente di disegnato: i muri duri (`0x7F`) della heightmap di collisione dove non c'è una parete visibile. In magenta |
| Senza collisione | facce che sembrano calpestabili ma non hanno collisione: ciano acceso dove, cadendo, si atterra sani e salvi; ciano scuro dove si finisce in una zona di morte, danno o teletrasporto |
| Box di collisione | il box di collisione di ogni oggetto, come lo prova il gioco (può essere molto più grande dell'oggetto). In arancione |
| Zone di morte | le zone che ti uccidono e fanno ripartire (rosso) o ti riprendono e rimettono in un punto fisso (viola) |
| Pavimento della morte | le zone di morte grandi almeno metà del livello: il mare, l'abisso sotto il livello. Non tutti i livelli ne hanno |
| Terreno di collisione | il terreno su cui si sta davvero (la heightmap): verde tenue sotto le facce visibili, verde acceso dove non c'è niente di disegnato, bianco coi raggi i punti isolati da 40 unità |
| Muri duri | i muri `0x7F` della heightmap, che fermano a qualunque altezza. In blu, disegnati alti 5 m |
| Box delle aree | il volume di collisione di ogni mini area (i blocchi della heightmap, dalla base alla cima); ancora da verificare nel gioco |
| Facce 0x1000 | le facce dei settori `0x1000` del terreno: il gioco non le disegna e non fermano; forse trigger o aree di caricamento. In grigio |

---

## Opzioni da riga di comando

`python tools/viewer.py [LIVELLO] [opzioni]`, o le stesse opzioni dopo
`"BBLIT Viewer.exe"`.

| opzione | effetto |
|---|---|
| `LIVELLO` | file di livello da aprire, senza estensione (es. `L03A`, `MERLIN`); senza, il menu principale |
| `--data CARTELLA` | cartella dei file `.bze`, per questa esecuzione (ha la precedenza sulla Cartella dei livelli salvata) |
| `--cache CARTELLA` | cartella della cache (predefinita `extracted/` accanto al viewer) |
| `--screenshot FILE.png` | apre, aspetta 0,6 s, salva la finestra in un PNG ed esce. Mouse e tasti sono ignorati e le impostazioni non si leggono né si scrivono, così l'immagine dipende solo dalle opzioni |
| `--camera x,y,z,yaw,pitch` | camera iniziale: posizione in metri del viewer, yaw e pitch in gradi |
| `--menu PAGINA` | apre una pagina del menu all'avvio: `main`, `load`, `level`, `flags`, `video`, `general`, `help`, `extra` |
| `--language it\|en` | lingua dell'interfaccia |
| `--tick N` | blocca tutte le animazioni sul tick N (foto riproducibili) |
| `--tps N` | tick al secondo delle animazioni (predefinito 15) |
| `--clones 0\|1\|2` | template clonati: spenti / all'avvio / tutti |
| `--albedo F` | fattore sul colore dei vertici delle facce con texture: 1 è il PC (predefinito), 2 la PlayStation |
| `--scale-factor N` | ingrandisce le texture con scale2x/scale3x: 1, 2, 3, 4, 6 o 8 |
| `--sky` | mostra la cupola del cielo |
| `--no-blend` | disegna opache le facce semitrasparenti |
| `--invisible-walls`, `--nocollision`, `--boxes`, `--deathzones`, `--deathfloor`, `--ground`, `--hardwalls`, `--areaboxes`, `--faces1000` | accendono la flag corrispondente |

Esempio, una foto riproducibile (`x,y,z` si prendono dai valori "m" della
barra di stato):

```bash
python tools/viewer.py L03A --camera 10,5,-20,-90,-15 --tick 0 --screenshot l03a.png
```

Tranne le flag, i valori dati da riga di comando (lingua, cielo, cloni, scala
delle texture...) vengono salvati come le scelte del menu quando si chiude il
menu o la finestra, a meno di usare `--screenshot`.

---

## Impostazioni e cache

Le **impostazioni** restano da un avvio all'altro, in
`Documenti\BBLIT Viewer\settings.json`. Se accanto al viewer c'è un file
`portable.flag` (accanto a `BBLIT Viewer.exe`, o nella radice del repository
quando si avvia dai sorgenti), finiscono invece in `userdata\settings.json`
lì. Si salvano quando si chiude il menu con Esc e quando si chiude la
finestra, e comprendono ciò che si è cambiato coi tasti della scena. Non si
salvano: flag, stati dei gruppi, animazioni ferme. Una voce sconosciuta o
malformata viene ignorata.

**Cache**, in `extracted/<LIVELLO>/` accanto al viewer (o `--cache`):

- `<LIVELLO>_id01.bin`, `_id03.bin`, `_id04.bin`: le sezioni decompresse
  (decomprimere in Python costa qualche secondo per livello);
- `pieces.pkl`: il livello già costruito, pezzo per pezzo
  (`tools/level_cache.py`). Porta una firma (dimensione e data del `.bze`, più
  un'impronta dei sorgenti di `tools/`, o di quelli da cui è stato costruito
  l'eseguibile) e si ricostruisce da solo quando cambiano il codice o il file
  del livello. Un livello già visto si riapre in una frazione di secondo.

Le sovrapposizioni per il glitch hunting si costruiscono solo quando si
accende una loro flag (la heightmap richiede qualche secondo nei livelli
grandi); da lì in poi stanno anche loro in cache, e spegnere la flag le
nasconde soltanto.

Le sezioni decompresse si riusano finché esistono. Se si sostituisce un file
di livello con uno diverso con lo stesso nome, si cancella la cartella di quel
livello in `extracted/` (cancellare tutta la cartella è sempre sicuro).

Un errore all'avvio viene aggiunto a `errors.txt` accanto al viewer;
l'eseguibile lo mostra anche in una finestra di messaggio.

---

## Costruire l'eseguibile

```bash
pip install pyinstaller
python tools/build_exe.py
```

Costruisce con PyInstaller un'applicazione a cartella, senza console, e mette
`BBLIT Viewer.exe` e `_internal/` nella radice del repository. `_internal/`
contiene Python, le librerie, `resources/` (l'icona della carota d'oro e lo
sfondo blu) e `code_hash.txt`, l'impronta dei sorgenti, così l'eseguibile e
`python tools/viewer.py` condividono la cache dei pezzi. I file di lavoro di
PyInstaller restano in `build/`. Se il viewer è aperto, lo script si ferma
senza toccare niente. Con Python 3.10.0 esatto, lo script aggira un difetto
di `dis` che blocca PyInstaller.

`python tools/make_release.py` costruisce la cartella della release e il suo
zip: l'eseguibile con `_internal/`, `README`, `README_Ita`, `LICENSE` e
`bze_levels/README.txt`.

---

## Gli strumenti

| file | cosa fa |
|---|---|
| `viewer.py` | il viewer |
| `bze.py` | container `.bze` e decompressore LZ77 (ricostruzione di `FUN_00430ff0` del gioco) |
| `loadscript.py` | legge il load script (sezione 1), con la tabella degli opcode **per tipo di blocco**; scrive un estratto JSON |
| `tim.py` | texture TIM della PlayStation -> PNG |
| `textures.py` | la tabella delle texture: slot registrati e slot animati (scoperta 275) |
| `export_obj.py` | terreno e props -> OBJ + MTL, in metri e Y in alto |
| `render_obj.py` | disegna un OBJ in un PNG senza motore grafico, per controllare i dati |
| `model_sheet.py` | provino a contatto dei modelli di un livello |
| `rig.py` | stream `0x50`: rig, pose, catena dei genitori (scoperta 261) |
| `montage.py` | sceglie rig e posa di un oggetto e produce le trasformazioni delle parti, anche per ogni fotogramma |
| `collision.py` | la heightmap di collisione (blocco `0x36` del load script) |
| `zones.py` | le zone che uccidono (`0x200000`) o riprendono (teletrasporto `0x40000000`) |
| `upscale.py` | scale2x / scale3x per le texture |
| `bmp.py` | i file `.bmp` del gioco -> PNG |
| `census.py` | censimento dei difetti di resa, una riga per livello |
| `levels.py` | i livelli per era, con LevID e titoli, per il menu |
| `preferences.py` | stati predefiniti scelti per alcuni livelli (non sono letture del formato) e gli `entity_groups` che il menu lascia cambiare |
| `level_cache.py` | la cache dei pezzi su disco |
| `menu.py`, `texts.py`, `settings.py`, `paths.py` | motore dei menu, testi dell'interfaccia (inglese e italiano), impostazioni salvate, cartelle dei dati |

Tutti gli strumenti scrivono i PNG a mano con `zlib`: non serve nessuna
libreria per le immagini. Gli strumenti con l'opzione `--data` usano
`BBLIT_DATA` come valore predefinito; la loro cache è `extracted` nella
cartella corrente.

### Esempio: da un `.bze` a un OBJ con le texture

```bash
python tools/bze.py "C:/Games/Lost in Time/Datas/bze/L03A.bze" -o extracted/L03A
python tools/loadscript.py extracted/L03A/L03A_id01.bin --json extracted/L03A/l03a.json
python tools/tim.py extracted/L03A/L03A_id03.bin extracted/L03A/l03a.json -o out/L03A/textures
python tools/export_obj.py extracted/L03A/L03A_id04.bin extracted/L03A/l03a.json --section3 extracted/L03A/L03A_id03.bin -o out/L03A/L03A.obj
python tools/render_obj.py out/L03A/L03A.obj -o out/L03A/check.png --textures out/L03A/textures
python tools/model_sheet.py extracted/L03A -o out/L03A/models.png --assemble
```

(Il primo percorso va adattato a dove stanno i propri `.bze`.) Opzioni utili:
`bze.py --raw` (senza decompressione); `tim.py --scale-factor N [--soft]`;
`export_obj.py --no-props` (solo terreno), `--units` (unità del gioco invece
dei metri), `--textures-dir` (cartella citata nel `.mtl`, predefinita
`textures`); `model_sheet.py --model ID`, `--columns`, `--cell-size`.
`textures.py [DATI] [LIVELLO]` stampa da dove vengono gli slot di texture di
un livello, e `bmp.py IN.bmp OUT.png` converte una bitmap.

`census.py` conta, con la stessa lettura del viewer, tutto ciò che viene
disegnato male o non disegnato, separato per causa (terreno, texture, modi,
props):

```bash
python tools/census.py                       # L03A, L03ACOM, L03A2
python tools/census.py --all-levels --json census.json
```

Le colonne non si sommano: un modello vuoto è il file che dice "non
disegnare", non un errore. Dalla scoperta 265 tutte le colonne di lettura sono
a zero sui tre livelli di `L03A`.

### Come sono collegati

```
.bze  --bze.py-->  sezioni decompresse (cache in extracted/)
                     | id 1  load script  --loadscript.py-->  oggetti, risorse, terreno, texture, zone
                     | id 3  blocco asset  --tim.py--------->  texture TIM
                     | id 4  blocco modelli
                     |         +-- magic 0x41  --export_obj.read_model-->  geometria
                     |         +-- magic 0x50  --rig.py / montage.py--->  montaggio delle parti
                     +- id 5+ banchi audio (non usati)
```

---

## Conversione delle coordinate

- **128 unità del gioco = 1 metro.**
- Il gioco è **mancino** con la Y verso il basso. La conversione è
  `(x, -y, -z)`, che ha determinante +1, **più l'inversione dell'ordine dei
  vertici di ogni faccia**. Negare la sola Y specchia tutto il livello
  (scoperta 180 di Ombelll).
- Rotazioni: 4096 unità = un giro intero, composte come `Rx * Ry * Rz`
  (scoperta 32 di Ombelll).

Il `--camera` del viewer e i valori "m" della barra di stato sono nel sistema
convertito; i valori "gioco" sono le unità originali.

---

## Cosa è verificato, e con quale prova

Le scoperte 256-288 sono in [FORMAT_NOTES.md](FORMAT_NOTES.md). I numeri più
bassi e i documenti sul formato sono di Ombelll:
<https://github.com/Ombelll/Bugs-bunny-lost-in-time-reverse-engineered>.
I dati sono di `L03A` dove non è detto altro.

| affermazione | prova | riferimento |
|---|---|---|
| container e decompressione | rapporto di compressione esattamente 8/9 (0,91x) sui banchi audio, e ogni header `FORM` è un `AIFF` valido | documenti sul formato di Ombelll; `bze.py` stampa il rapporto per sezione |
| load script | consumato al 100%, 1 byte sconosciuto; 282 oggetti, 150 con posizione, come nei documenti di Ombelll | `loadscript.py` stampa entrambi |
| offset delle risorse | 79/79 modelli con magic `0x41`, 274/274 stream con `0x50`, 442/442 texture su un header TIM | |
| terreno | 158 settori, somma dei contatori 3058 = `n_prim`, ogni settore finisce sul byte previsto, catena che termina su `vert_top` | scoperta 256; `export_obj.py` stampa i conteggi |
| primitive | 2773/2773 lette nei modelli, 2742/2742 nel terreno, nessuna respinta | |
| texture a tinta unita | le 45 citate dai modi `0x4A`/`0x4E` sono tutte 4x4 e uniformi | scoperta 258 |
| UV `FF FF` | 1158/1158 hanno un id di texture registrato, 0/1158 hanno tutte le UV a `FF` | scoperta 259 |
| fattore 1 sul colore dei vertici per il PC, non 2 | colore del mare di `L03A` misurato nel gioco | scoperta 268 |
| 15 tick di animazione al secondo | misurati fotogramma per fotogramma sulla versione PlayStation | scoperta 278 |

I controlli dietro questi numeri sono gli script in `tools/diagnostics/`
(`check_*.py`, `diag_*.py`); leggono i livelli da `BBLIT_DATA` e si possono
rieseguire.
