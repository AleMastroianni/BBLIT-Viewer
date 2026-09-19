# Note sul formato: scoperte 256-288

English: [FORMAT_NOTES.md](FORMAT_NOTES.md)

Note tecniche sui dati dei livelli di *Bugs Bunny: Lost in Time* (PC, 1999)
e su cio' che il gioco ne fa, trovate costruendo il viewer dei livelli di
questo repository (`tools/viewer.py`), per lo piu' su `L03A` (*Hey... What's
Up, Dock?*, prima sezione) e poi controllate sul resto dei livelli. La
numerazione prosegue quella delle [note di reverse engineering di Ombelll](https://github.com/Ombelll/Bugs-bunny-lost-in-time-reverse-engineered),
che finiscono alla 255: "finding N di Ombelll", "MODELFORMAT di Ombelll" e
"note SPEEDRUN di Ombelll" rimandano a quel repository, come i nomi di
funzione del tipo `FUN_00423eb0` (lavoro affine: [BugsDecomp](https://github.com/quantumdude836/BugsDecomp)).
La regola e' la stessa: **una lettura conta solo dopo un test che poteva
fallire**, e ogni scoperta riporta quel test e i suoi numeri. Le etichette di
prova (`PROVEN_RAW_DATA`, `PROVEN_BINARY`, `REBUILD_VERIFIED`, `STRONG`,
`OPEN`) si usano come in quelle note. Dove una scoperta corregge i documenti
di Ombelll, lo dice.

| # | Scoperta |
|---|---|
| 256 | L'header di un settore di terreno consuma sempre almeno una faccia di delimitazione |
| 257 | Un quad e' a Z, non a ventaglio |
| 258 | I modi `0x4A` e `0x4E` sono texturizzati, con una texture a tinta unita |
| 259 | `FF FF` nella prima UV e' l'angolo (255,255), non un riempimento |
| 260 | SMENTITA dalla 275: "la tabella delle texture e' cumulativa tra i file" |
| 261 | Le parti di un modello si montano con il rig e si concatenano sui genitori |
| 262 | Le UV vanno scalate per (dimensione − 1), non divise per 256 |
| 263 | I `.bmp` in `Datas/bze` non sono anteprime dei livelli |
| 264 | Due build di `Bugs.exe`: gli indirizzi dei dati valgono, quelli del codice no |
| 265 | Gli stream di tipo 4 sono animazioni |
| 266 | RESPINTA: "le facce `0x4A`/`0x4E` semitrasparenti vengono disegnate opache" |
| 267 | La cupola del cielo segue la camera |
| 268 | Il fattore x2 sul colore dei vertici e' sbagliato per il PC |
| 269 | CHIUSA dalla 275: l'alone del sole usa texture che nessun file statico ha |
| 270 | La cupola del cielo, parte per parte |
| 271 | La coordinata v delle texture si conta dal basso |
| 272 | La posa di un oggetto e' quella che il gioco fa partire, non quella con piu' record |
| 273 | Le fusioni semitrasparenti erano spente dal secondo fotogramma (difetto del viewer) |
| 274 | Forzieri blu, casse che cadono e fiamme sono cloni di template |
| 275 | Occhi, alone del sole, acqua e increspature sono texture animate riempite da oggetti |
| 276 | Un vertice col bit `0x8000` e' la copia di un vertice di un'altra parte, e va saldato |
| 277 | Nel triangolo `0x3C` il primo vertice e' quello a +28, non a +14 |
| 278 | Un'animazione ha un blocco per tick, e ogni blocco porta solo cio' che cambia |
| 279 | Sprite, cloni annidati e punti di aggancio: le torce |
| 280 | Le ancore: parti tolte dalla posa (tipo 8, flag 0xB) e la rotazione dell'azione `0x26` |
| 281 | Le varianti `_8` non sono nella tabella dei livelli |
| 282 | I settori `0x1000`: un quad per record, in due ordini dei vertici |
| 283 | Facce che si vedono e su cui non si sta |
| 284 | Un box per oggetto: il muro invisibile sopra il vetro in `L05A3C` |
| 285 | Le regole delle zone: effetti a +16; le zone che uccidono o riportano indietro |
| 286 | Quello che si vede contro quello su cui si sta: terreno invisibile, pixel, muri finti |
| 287 | I blocchi di collisione sono lastre impilate; la loro cima come soffitto e' solo un candidato |
| 288 | Le flag di collisione del viewer, riviste sul gioco |

---

## 256 — L'header di un settore di terreno consuma sempre almeno una faccia di delimitazione

`PROVEN_RAW_DATA`. Un settore con `mode 0x0000` dichiara `n_bound_faces = 0`,
ma il suo blocco dei punti non sta a +8: sta a **`8 + max(n_doos, 1) * 8`**.
Il passo del dispatcher salta comunque una faccia, anche quando non ce n'e'
nessuna, e questo combacia con la tabella dei modi "singoli" (16, 16, 56, 56,
20 byte) che il MODELFORMAT di Ombelll ricava da `FUN_00423eb0`.

**La prova:** con questa lettura la catena dei settori di `L03A` chiude
esatta: 158 settori, somma dei campi `+0` pari a **3058 = `n_prim`**, ogni
catena di poligoni che finisce sull'ultimo byte del proprio record, e l'ultimo
settore che termina su `vert_top`. Col blocco dei punti a +8 il parser si
ferma dopo **3 settori su 158**.

## 257 — Un quad e' a Z, non a ventaglio

`PROVEN_RAW_DATA` + `REBUILD_VERIFIED`. I due triangoli di un quad sono
`(0,1,2)` e `(1,3,2)`. Scrivere `f v0 v1 v2 v3` in un OBJ e lasciare che
l'importer chiuda il poligono da' `(0,1,2)` e `(0,2,3)`: l'altra diagonale.

**La prova:** in `L03A` l'87% delle facce del terreno sono quad, e **516 dei
2378 (il 22%) cambiano area** tra le due letture; disegnati a ventaglio
diventano denti di sega chiari e scuri lungo tutti i moli. Il formato in se'
non e' in discussione (i documenti di Ombelll lo dicono in una riga
sull'esportazione), ma un esportatore che scrive poligoni invece di triangoli
lo perde.

## 258 — I modi `0x4A` e `0x4E` sono texturizzati, con una texture a tinta unita

`PROVEN_RAW_DATA`. Il MODELFORMAT di Ombelll dice "indice di texture a +4,
nessuna UV nel record", e da li' viene facile concludere che siano facce a
colore piatto. Non lo sono: il campo a +4 nomina una texture vera, e il record
non porta UV perche' non servono.

**La prova:** delle 45 texture citate dai modi senza UV in `L03A`, **45 su 45
sono 4×4 e perfettamente uniformi**, un solo colore ripetuto, quindi
campionarle in un punto qualsiasi da' lo stesso risultato. Disegnate col solo
colore dei vertici, quasi neutro, queste facce (quasi la meta' di quelle del
livello) escono bianche o grigie.

**Un test che NON discrimina, tenuto come avvertimento:** "l'id a +4 e'
registrato dal livello" da' 100%, ma un numero a caso nello stesso intervallo
da' **97%**, perche' il livello registra 442 id su 456.

## 259 — `FF FF` nella prima UV e' l'angolo (255,255), non un riempimento

`PROVEN_RAW_DATA`. **Corregge il MODELFORMAT di Ombelll**, che scrive: *"For
untextured primitives, those spots hold `FF FF` as padding"*.

**La prova:** in `L03A`, **1158 facce su 3048** in modo con UV hanno la prima
coppia a `FF FF`. Di queste:

- l'id di texture e' uno slot registrato in **1158 casi su 1158**;
- **0 su 1158** hanno *tutte* le UV a `FF FF`;
- le coppie sono angoli regolari, per esempio `(255,255), (255,0), (0,255),
  (0,0)`.

Trattarle come facce senza texture fa perdere il **38%** delle facce
texturizzate. Il criterio giusto non sta in quei byte: una faccia e' senza
texture quando il suo id **non esiste nella tabella degli slot**.

## 260 — SMENTITA dalla 275: "la tabella delle texture e' cumulativa tra i file"

> **Smentita dalla scoperta 275.** Gli 8 id che `L03A` cita senza
> registrarli sono slot di texture animate, riempiti da oggetti dello stesso
> livello. Che altri file registrino quegli slot non provava nulla: quasi ogni
> file registra 3-7 e 291/293.

L'affermazione era: il gioco registra ogni TIM in uno slot numerato
(`FUN_004229a0`, tabella a `0x52fd60`) e non svuota la tabella al cambio di
livello (al contrario del registro dei suoni, finding 152 di Ombelll), quindi
`L03A` prenderebbe sei degli 8 id mancanti da `L03ACOM` e due (7 e 307) da
`title.bze`. Che la tabella non venga svuotata resta vero nel codice (vedi
275), ma nessuna faccia disegnata ne dipende.

## 261 — Le parti di un modello si montano con il rig e si concatenano sui genitori

`PROVEN_RAW_DATA` + `REBUILD_VERIFIED`. I vertici di ogni parte TMD stanno in
spazio locale; a posizionarle sono il rig (ruolo 4, stream `0x50` tipo 1) e
la posa di apertura di un'animazione (tipo 2). In `L03A`, **58 oggetti
piazzati su 77 hanno un modello a piu' parti, e tutti e 58 hanno un rig**.

I documenti di Ombelll non concordano su come comporre le trasformazioni: il
loro finding 33 dice che una posa da' la trasformazione completa di ogni
parte, mentre una sezione del MODELFORMAT dice che si concatenano. **La
catena e' giusta**, con la misura che i documenti usano per Bugs: montato
senza catena e' alto 150 unita' e sta in un mucchio; con la catena e' alto
**285**, una figura in piedi.

Due dettagli:

- **Il primo blocco di un'animazione non e' sempre una posa.** Per il
  modello 112 contiene solo record "crea parte" e lascia l'oggetto impilato
  sull'origine. Si leggono i blocchi finche' ogni parte con mesh ha ricevuto
  la sua trasformazione.
- **Quale posa** (regola sostituita dalla 272): scegliere per numero di
  ruolo prendeva uno stream degenere; scegliere lo stream con piu' record TRS
  faceva passare il modello 112 da ammasso a **pirata** riconoscibile.

## 262 — Le UV vanno scalate per (dimensione − 1), non divise per 256

`PROVEN_BINARY` nei documenti di Ombelll (`FUN_0041cd50`), qui applicato. La
coordinata in pixel e' `u/255 · (dimensione − 1)`, campionata al **centro del
texel**. Dividere per 256 sfalsa di mezzo texel: invisibile con un filtro
"nearest", visibile con filtro lineare o mipmap (su una texture 16×16 mezzo
texel e' il 3% della superficie). Il verso della v e' corretto dalla 271.

## 263 — I `.bmp` in `Datas/bze` non sono anteprime dei livelli

`PROVEN_RAW_DATA`. Sono tutti di 328.758 byte, e l'header dichiara
**256×1280 a 8 bit**: dump della memoria video, non schermate. Non danno una
verita' di riferimento su come appare un livello.

## 264 — Due build di `Bugs.exe`: gli indirizzi dei dati valgono, quelli del codice no

`PROVEN_BINARY`. Il finding 208 di Ombelll descrive due build commerciali di
`Bugs.exe`, entrambe di 772.096 byte, con dati dei livelli identici: SHA-256
`6E15F920…`, a cui appartengono tutti gli indirizzi di codice dei documenti di
Ombelll, e `74AB71E1…` ("BBLIT release" nel NATIVE_TRACE di Ombelll). Gli
indirizzi di codice di queste note (scoperta 280) vengono da `74AB71E1…`.

Su quella build gli indirizzi `.data` dei documenti di Ombelll si leggono
correttamente (la tabella dei livelli, 111 voci da 24 byte a partire da
`..\BZE\TITLE.BZE;1`), mentre quelli `.text` vanno ritrovati per firma di
byte: lo spostamento non e' costante (+0x1A0 per le chiamate a `CreateFileA`
nel 208 di Ombelll, +0x90 qui per i gestori delle azioni 0x17 e 0x19). I file
dei livelli sono gli stessi: `MERLIN.BZE` ha l'hash documentato.

## 265 — Gli stream di tipo 4 sono animazioni

`PROVEN_RAW_DATA` + `REBUILD_VERIFIED`. L'header di uno stream `0x50` porta
a +2 un tipo: 1 (rig), 2 (animazione) e 4. Il MODELFORMAT di Ombelll cita il
4 una volta sola, con un punto di domanda.

**La prova:** la catena dei blocchi di posa (`u32` col numero di record,
`u32` di tempo, poi i record autodescrittivi) chiude **esattamente
sull'ultimo byte della risorsa in 205 stream di tipo 4 su 205** (`L01A`,
`MERLIN`, `L03A`, `L03ACOM`, `L03A2`), come per i tipi 1 e 2. Contengono
record TRS normali (107, 36, 181 per stream negli esempi) e quasi sempre un
riquadro (tipo 9) per blocco: sono animazioni di oggetti che si muovono.

**Cosa cambia:** il censimento (`tools/census.py`) contava 35 oggetti del
molo (10 + 6 + 19) con modello a piu' parti, rig e **nessuna posa**, quindi
montati con l'identita', parti ammucchiate sull'origine. Accettando il tipo 4
scendono a zero: il modello 161 torna una palma in piedi, il 285 una
passerella inclinata, e la cima d'ormeggio smette di essere un'asse gigante.
Il contatore da solo non mostra che la posa trovata sia quella giusta; lo
mostra la foto prima e dopo.

**Non stabilito:** cosa distingua il 4 dal 2. "Il 4 porta un riquadro per
blocco, il 2 no" e' compatibile coi conteggi ma non misurato.

## 266 — RESPINTA: "le facce `0x4A`/`0x4E` semitrasparenti vengono disegnate opache"

Il lettore prende la modalita' di fusione solo nei modi con UV, perche' nei
modi `0x4A`/`0x4E` la parola a +10 cade dentro i colori; le facce di quei modi
col bit 3 del flag verrebbero disegnate opache. **Misurato:** nelle tre
sezioni del molo **0 facce su 4899** in modo `0x4A`/`0x4E` hanno il bit 3 (i
loro flag sono solo `0x01` e `0x03`). Respinta solo per il molo: il
censimento su tutti i 53 livelli giocabili ne trova **30** (L03C1 6, L04C3 6,
L05A3c 12, L04C1, L04D1, L04D2 2 ciascuno), e cosa ne faccia il gioco non e'
stabilito (colonna `semi0` del censimento).

Nota a margine dallo stesso censimento: i modi `0x34` e `0x38` non compaiono
nelle tre sezioni del molo, e il bit `0x02` del flag (doppia faccia nel TMD
della PlayStation) sta su circa un quinto delle facce di ogni modo. Se qui
voglia dire doppia faccia non e' misurato.

## 267 — La cupola del cielo segue la camera

`REBUILD_VERIFIED`, con una verita' di riferimento. In `L03A` l'oggetto 0
(modello 1, 231 facce) sta in (0,0,0) e misura **367 x 245 x 367 m**,
centrato sull'origine: cielo, sole, nuvole e mare fino all'orizzonte. Il punto
di partenza e' a circa 187 m dall'origine, sul bordo della cupola: disegnata
ferma, se ne vedono solo due punte grigie.

Disegnata per prima, senza profondita' e traslata con la camera, la scena
coincide con le schermate del gioco: **il sole cala dietro la pila di casse
col timone**, cosa impossibile con la cupola ferma.

Aperto: se ruoti anche, in parte, con la visuale. Le schermate escludono la
rotazione completa (il sole non compare in tutte le direzioni), non una
parziale.

## 268 — Il fattore x2 sul colore dei vertici e' sbagliato per il PC

`PROVEN_RAW_DATA` (pixel del gioco PC) + `REBUILD_VERIFIED`. **Corregge il
finding 16 di Ombelll per la versione PC**: texture × colore dei vertici × 2
(128 = neutro, "255 raddoppia") e' la convenzione della PlayStation, non del
port. Col x2 il viewer e' circa **il doppio piu' chiaro su tutto** rispetto
alle schermate del gioco PC nella stessa inquadratura: scafo rosa salmone
invece di marrone, mare blu acceso invece di blu notte. Il mare e' fatto di
facce `0x4A`/`0x4E` (texture 4x4 a tinta unita, 258), quindi passa anche lui
dal fattore. Con fattore 1 scafo, mare e cielo tornano quasi identici al
gioco.

**La misura** (mediana di zone corrispondenti, una schermata PC contro il
viewer nella stessa inquadratura):

| zona | gioco | viewer x2 | viewer x1 |
|---|---|---|---|
| mare (faccia a tinta unita) | (0, 0, 63) | (0, 0, 125) — rapporto 0,50 | **(0, 0, 63)** — rapporto 1,00 |
| cielo alto | (32, 58, 88) | (37, 113, 170) — 0,86 / 0,51 / 0,52 | (18, 57, 85) — 1,78 / 1,02 / 1,04 |
| scafo | (89, 52, 41) | (163, 87, 65) — circa 0,6 | (82, 44, 32) — circa 1,1-1,3 |

Il mare e' il campione pulito: una tinta unita, e coincide esatto. Il rosso
del cielo e lo scafo divergono di piu' perche' le zone non sono le stesse
pixel per pixel e il colore varia lungo la superficie, ma nessuna zona e'
compatibile col x2. Il viewer usa 1 di default; `--albedo 2` resta per
confronto.

## 269 — CHIUSA dalla 275: l'alone del sole usa texture che nessun file statico ha

> **Chiusa dalla 275:** gli slot 3-7 sono riempiti a ogni fotogramma da
> cinque oggetti di tipo 2 con i fotogrammi 361-364, bande gialle sfumate.

Il bagliore attorno al sole sono 10 facce del modello 1 con fusione 3
(B + F/4), colore dei vertici giallo quasi uniforme (circa 255,255,50) e UV
sull'intera texture, quindi la forma sfumata deve venire dalla texture: gli
slot **3-7**, che `L03A` non registra e che nessun file `.bze` riempie con
qualcosa che somigli a un bagliore. La lettura cumulativa della 260 li
disegnava come un ventaglio oliva a righe, in gran parte anche per un difetto
di fusione del viewer (273).

## 270 — La cupola del cielo, parte per parte

`PROVEN_RAW_DATA` per la struttura; l'orientamento, lasciato `OPEN` qui, e'
risolto dalla 271. Il modello 1 di `L03A` ha 7 parti, con un rig (risorsa 3)
e un'animazione (risorsa 4, ruolo 131):

| parte | quota nel mondo | texture | cos'e' |
|---|---|---|---|
| 0 | da -8 a +151 m | 393 (4x4) + 1 e 2 (128x128) | volta del cielo e 14 **cartelloni**: isolotti con palme (1) e navi lontane (2) all'orizzonte |
| 1 | da +18 a +55 m | 394 (4x4) | le nuvole gialle |
| 2 | da -7 a +42 m | 395 (4x4) + slot 3-7 in fusione | il sole e il suo alone (269, 275) |
| 3 | da -94 a -6 m | 396 (4x4) | il mare fino all'orizzonte |
| 4, 5, 6 | da -18 a 0 m | 8 (64x64) | i **riflessi del sole sull'acqua**; l'animazione sposta proprio queste tre parti a ogni fotogramma |

Tutto e' coerente con la conversione `(x, -y, -z)`: cielo sopra, mare sotto,
riflessi sotto l'orizzonte in direzione del sole. I cartelloni non ruotano;
poiche' la cupola viaggia con la camera (267) restano sempre alla stessa
distanza, e lo sfondo dipende da dove guarda la camera, non da dove si trova.

**Orientamento dei cartelloni (risolto dalla 271).** Con la v contata
dall'alto i 14 cartelloni escono capovolti; nel gioco sono diritti. Nei loro
record (`0x40`, flag `0x01`, UV agli angoli, indici `4c 4d 4f 4e`) la riga di
fondo della texture (v = 255) sta sui vertici alti, e anche u corre al
contrario: una rotazione di 180 gradi. La posa della cupola e' l'identita'
per tutte le parti, quindi la posa non lo spiega. Un conteggio sulle facce
verticali (L03A, L01A, MERLIN) dava il terreno mappato "capovolto" circa 3
volte su 4 e i props meta' e meta'; su texture simmetriche come legno e
roccia il verso non si vede, quindi quel conteggio da solo non decideva.

## 271 — La coordinata v delle texture si conta dal basso

`REBUILD_VERIFIED`, con verita' di riferimento. **Corregge la 262** per il
verso (la scala per dimensione − 1 resta). La lettura di `FUN_0041cd50` nei
documenti di Ombelll non dice da che lato parta la v; contarla dall'alto, come
per un'immagine, e' sbagliato.

**Il sintomo** era sparso in quattro difetti che sembravano indipendenti:
"HANDLE WITH CARE" e "ACME" sottosopra sulle casse (righe in ordine inverso,
lettere capovolte, lettura da sinistra a destra: un ribaltamento verticale,
non una specchiatura); i 14 cartelloni della cupola capovolti (270); la
fascia bianca con gli oblo' assente sulla nave; triangoli bianchi e neri a
poppa.

**Le prove:**

* con `v' = 255 - v` tutti e quattro tornano come nelle schermate del gioco;
* una misura che poteva fallire: sulle facce verticali del terreno, con la v
  dall'alto la texture risulta capovolta **696 volte contro 238** in `L03A`
  (MERLIN 748 contro 245, L01A 1065 contro 854); con la v dal basso gli
  stessi numeri diventano "diritta". Pareti, scogli e fiancate dei moli sono
  disegnati per stare diritti, e un verso che li capovolge 3 volte su 4 e'
  quello sbagliato. Il conteggio da solo non basta (su legno e roccia il verso
  non si vede), ma va nella stessa direzione delle scritte.

Le texture esportate come PNG non cambiano: sono gia' diritte (il cartellone
dell'isolotto ha le palme in alto). Cambia solo la mappatura, in
`export_obj.uv_to_texture` (`tools/export_obj.py`), che viewer ed export OBJ
condividono.

## 272 — La posa di un oggetto e' quella che il gioco fa partire, non quella con piu' record

`REBUILD_VERIFIED`, con la catena presa dai finding di Ombelll;
**sostituisce la regola di scelta della posa della 261**.

Scegliere, tra le animazioni di un oggetto, quella con piu' record TRS
prende per la carota normale (modello 55) il ruolo 185, la cui posa iniziale
ha il corpo **schiacciato a scala 0 in verticale** (e' la carota che spunta
da terra): esce corta e piantata sulle assi, mentre nel gioco galleggia
inclinata.

La catena del gioco: per gli oggetti di tipo 14 (`FUN_00440120`, finding 188
di Ombelll) lo stato iniziale e' il **2, e se manca l'1**; lo slot 0 della sua
playlist e' una **chiave** (finding 89 di Ombelll) che si cerca tra i passi
dell'oggetto (`0x30`, e `0x34` per il giocatore); il passo porta a +2 il
**ruolo** dell'animazione (finding 84 di Ombelll). `loadscript.export_level`
esporta stati e passi, e `montage.start_role` segue questa catena.

**Le prove:**

* la catena arriva a un'animazione che l'oggetto possiede davvero per **73
  oggetti con rig su 77** in `L03A` (L03ACOM 28/29, L03A2 100/108, L01A
  135/139, MERLIN 28/39); i restanti non hanno stati, o la loro animazione non
  ha trasformazioni, e ripiegano sul conteggio dei record (colonna `pos~` del
  censimento);
* quattro carote su cinque partono dal ruolo **163**, la cui posa e'
  **inclinata di circa 40 gradi e sollevata di 0,7 m**: la carota galleggia
  intera, come nelle schermate del gioco;
* la quinta (oggetto 114) parte dal ruolo 131, posa neutra, e ha un secondo
  stato (236) che porta al 185, "spunta da terra": e' la carota che il gioco
  fa comparire piu' tardi, e non viene piu' mostrata nella sua forma finale;
* Bugs (il giocatore, i cui passi sono i record `0x34`) parte dal ruolo 35:
  mani sui fianchi, come nelle schermate, invece di tendere una carota.

Semplificazione dichiarata: da fermo si disegna la posa del primo blocco
dell'animazione (l'animazione che scorre e' nella 278).

## 273 — Le fusioni semitrasparenti erano spente dal secondo fotogramma (difetto del viewer)

`REBUILD_VERIFIED`. Un difetto del viewer, annotato perche' nascondeva altri
risultati. Le quattro fusioni della PlayStation erano scritte giuste ma
attive solo nel primo fotogramma: il viewer abilitava `GL_BLEND` una volta
all'avvio, e l'HUD di pyglet la **spegne** dopo aver disegnato il testo
(`pyglet/text/layout/base.py`, riga 780: `glDisable(GL_BLEND)`). Dal secondo
fotogramma in poi ogni faccia semitrasparente usciva opaca, anche in tutte le
catture del viewer (scattate dopo 0,6 s, cioe' dopo decine di fotogrammi).

**Il sintomo e la prova:** quadrati neri sotto le piante dell'isola. La
pianta (modello 192) ha una faccia d'ombra in fusione sottrattiva (tipo 2,
B − F) con una texture 64x64 nera al 77% e una sagoma grigio scuro
(33,33,33): in sottrazione il nero non toglie nulla e la sagoma scurisce
l'erba; disegnata opaca e' un quadrato nero. Con le fusioni "accese" e
"spente" il quadrato era identico, e il terreno sotto la pianta non ha texture
scure: la causa era lo stato di OpenGL, non la lettura dei dati.

**Dopo la correzione** (fusione e test di profondita' riattivati all'inizio
di ogni fotogramma): le ombre delle piante sono sagome morbide, i bordi delle
isole sott'acqua trasparenti, l'alone del sole semitrasparente. **Rivede la
269:** l'alone "a ventaglio oliva" era in gran parte facce additive (B + F/4)
disegnate opache.

## 274 — Forzieri blu, casse che cadono e fiamme sono cloni di template

`PROVEN_RAW_DATA` per chi li chiede e a che condizione, `STRONG` per il posto
dei forzieri, `REBUILD_VERIFIED` a schermo.

Gli oggetti che il gioco mostra (PC e PlayStation) ma che il livello non
piazza sono **template** (blocco 0x08, senza posizione) clonati da una regola
`0x31` di un oggetto vivo con effetto `0x100`/`0x40000`, ruolo al campo +28,
nella posizione e rotazione del genitore (finding 194 di Ombelll).
`loadscript` esporta le regole `0x31` di ogni oggetto. In `L03A`:

| cosa | chi lo chiede | condizione |
|---|---|---|
| **3 forzieri blu** (modello 305, ruoli 764-766) | oggetto 83, modello vuoto con rig | `tabel1[114]` == 1, 2 o 3: tre regole li dispongono in tre ordini; altre regole assegnano 1/2/3 con effetto `0x2` (probabilita', soglie 25000 e 20000). L'ordine e' **estratto a caso** |
| **8 casse verdi** (modello 311) | 8 trigger sui moli | effetto `0x8200100`: bersaglio giocatore, raggio 640; un bit di `tabel1[106/107]` per cassa. Nel gioco cadono quando Bugs si avvicina |
| la "cupoletta" con l'elica (oggetto 138/139, modello 392) | e' un oggetto piazzato | chiede i ruoli 902 (modello 88) e 904 (modello 95) |

**Il posto dei forzieri.** La loro regola porta anche il bit `0x80`, e il
campo +24 vale 1, 2 o 3. Il rig dell'oggetto 83 ha tre parti figlie a
**x = -400, 0, +400**: leggendo "+24 = k-esima parte figlia" i tre forzieri
stanno in fila, come in una schermata della versione PlayStation. Una lettura
coerente, non letta nel codice (affinata nella 279).

**Nel viewer**, flag Template clonati (Cloned templates, `--clones 0/1/2`):
Spenti (predefinito), All'avvio (condizione vera a tabelle vuote, finding 161
di Ombelll, e nessun bersaglio a distanza), Tutti (cio' che puo' comparire).
Le regole non si valutano nel tempo: i forzieri, ordinati a caso a runtime,
compaiono solo con Tutti. Molti cloni sono effetti passeggeri (stelle di
esplosione, buchi di scavo, carote che saltano fuori), per questo sono spenti
di default.

**Aperti a questo punto:** la torcia animata non si trovava ne' tra i cloni
ne' tra gli oggetti (vedi 279); l'oggetto 138 non e' una torcia ma la
cupoletta con l'elica, che nel viewer esce semitrasparente (tutte le 14 facce
in fusione additiva) mentre sulla PlayStation sembra piena; un "!" alto nel
cielo viene da cloni All'avvio.

## 275 — Occhi, alone del sole, acqua e increspature sono texture animate riempite da oggetti

`PROVEN_RAW_DATA` per la regola e i suoi numeri, `REBUILD_VERIFIED` a
schermo. Corregge la **260** e chiude la **269**.

**La regola.** Un oggetto di tipo **2** o **20** (opcode `0x13`) che porta
l'opcode **`0x0B`** non si disegna: a ogni fotogramma scrive nello slot di
texture nominato da `0x0B` (u32) un fotogramma scelto cosi':

* i fotogrammi stanno in una sua risorsa con l'opcode **`0x40`** (u32 offset,
  u32 dimensione nella sezione 4): un modello `0x41` fatto solo di primitive
  **`0x64`** da 16 byte, id della texture a +10, larghezza e altezza a
  +12/+14. Il fotogramma k e' il k-esimo record;
* tipo 2: la sequenza sta in una risorsa con l'opcode **`0x3F`** (u32 numero
  di coppie, u32 offset, u32 dimensione): coppie di byte **(fotogramma,
  durata in tick)**;
* tipo 20: nessuna sequenza; `0x42` = **(primo, ultimo, durata)**, un ciclo.

**La prova che poteva fallire.** In tutti i file `.bze` ci sono **520**
oggetti con `0x0B` in 79 file, tutti di tipo 2 (391) o 20 (129). **Nessuno**
dei 520 slot e' registrato dal proprio file, e coprono **518 dei 545** id che
le facce citano senza che il file li registri (7875 facce). I 27 restanti
stanno in modelli che nessun oggetto piazza: su tutti i livelli
(`tools/census.py --all-levels`) le facce disegnate che citano uno slot vuoto
sono **0 su 277.588**.

La testa di Bugs mostra lo schema: in **ogni** file usa 8 id consecutivi, e
il 5° e il 7° non sono mai registrati (L03A 291/293, title 241/243, L02A1
136/138, L03B 184/186, ...). Sono gli occhi.

**Cosa sono in `L03A`** (14 slot, tutti riempiti da oggetti del livello):

| slot | fotogrammi | cosa | usato da |
|---|---|---|---|
| 3-7 | 361-364, 16x32, bande gialle sfumate, avanti e indietro 4 tick l'uno | **alone del sole** | cielo, 10 facce, fusione B + F/4 |
| 202, 203 | 365-372 e 373-380, 32x32, ciclo di 8 da 2 tick (tipo 20) | nuvole e acqua con la schiuma che scorrono | modello 104 |
| 204, 272 | 381-386, righe chiare, poi il 386 vuoto per 15 o 30 tick | riflessi sull'acqua | modelli 104 e 239 |
| 336 | 386 vuoto, poi 381-385 | increspature | **96 facce del terreno**, B + F/4 |
| 353 | 387-391, cerchi che si allargano, poi pausa | cerchi nell'acqua | **146 facce del terreno**, B + F/4 |
| 291, 293 | 392, 64x32 | **occhi di Bugs** (un solo fotogramma, lo stesso per i due occhi) | modello 315 |
| 307 | 311 | **occhio di Merlino** | modello 372 |

Le 242 facce del terreno di 336/353 sono le basi dei pali nell'acqua: senza la
loro texture escono come **quadrati piu' chiari** (colore dei vertici in
fusione additiva), che il gioco non mostra. Con la texture, quasi tutta nera,
in fusione additiva restano solo le righe e i cerchi.

**Cosa corregge.** La 260 spiegava gli stessi slot con una tabella
cumulativa tra i file (`title -> L03ACOM -> L03A`). Quella prova era debole:
quasi ogni file registra gli slot 3-7 e 291/293, quindi qualunque file
"compagno" li avrebbe riempiti; e a schermo dava la cinghia di un barile al
posto degli occhi e un ventaglio oliva al posto dell'alone (269). Dopo la 275
nessun livello ha piu' una faccia disegnata da spiegare con la catena, e
`textures.construct` (`tools/textures.py`) non aggiunge piu' i file compagni
(si possono ancora chiedere con `extra`). Che la tabella del gioco sopravviva
al cambio di livello resta vero nel codice (nessun azzeratore), ma non serve
a disegnare nulla.

**Nel viewer** gli slot animati cambiano fotogramma col tempo (flag Texture
animate, Animated textures; da spenta si vede il primo fotogramma della
sequenza). La durata del tick, prima ipotizzata a 25 al secondo, e' misurata
nella 278: 15 al secondo.

**Ancora aperto:** nel gioco l'alone e' un disco giallo pieno e piu' grande;
nel viewer ha la forma giusta ma e' piu' tenue (fotogramma, fusione o colore
dei vertici, da confrontare). Chi sceglie la fase di partenza: i cinque
oggetti 3-7 condividono la sequenza, e il viewer li fa partire insieme.

## 276 — Un vertice col bit `0x8000` e' la copia di un vertice di un'altra parte, e va saldato

`PROVEN_RAW_DATA` per la corrispondenza, `REBUILD_VERIFIED` a schermo.

Nell'elenco dei vertici di una parte (record da 16 byte: x, y, z float, u32
id), alcuni id portano il bit **`0x8000`**. Ogni id di questo tipo ha
**esattamente un** vertice con lo stesso id senza il bit, in un'altra parte:
**2876 copie su 2876** in 8 file (`L03A`, `L03A2`, `L03ACOM`, `L01a`,
`MERLIN`, `L02A1`, `L04A1`, `L05A1`), nessuna orfana, nessuna con due
proprietari. Le facce nominano l'id senza il bit.

**La prova che poteva fallire.** Con la posa di partenza (272) la copia sta
in mediana a **3,7 unita'** dal suo originale, contro 44 in coordinate
locali: e' lo stesso punto espresso nel sistema della propria parte, giusto
nella posa di modellazione e sbagliato appena le parti si muovono (fino a
**620 unita'**). Ipotesi nulla: tra tutti i vertici delle **altre** parti,
l'originale dichiarato e' il piu' vicino alla copia **2197 volte su 2876** (a
caso sarebbe circa 1 su qualche centinaio; i restanti sono in buona parte
vertici quasi coincidenti).

**La regola**, in `export_obj.read_model`: la copia prende la posizione
dell'originale gia' trasformata con la sua parte. E' la pelle che tiene unite
le giunture: senza, le spalle e le braccia di Bugs e la veste e il viso di
Merlino restano aperti. `read_model(..., weld=False)` rida' la lettura
vecchia.

## 277 — Nel triangolo `0x3C` il primo vertice e' quello a +28, non a +14

`PROVEN_RAW_DATA`, `REBUILD_VERIFIED` a schermo.

Il triangolo Gouraud texturizzato (`0x3C`, 32 byte) porta tre UV (+4, +8,
+12), tre colori (+16, +20, +24) e tre indici di vertice (+14, +28, +30). UV
e colore k vanno con gli indici nell'ordine **+28, +30, +14**, non +14, +28,
+30.

**La prova che poteva fallire.** Due triangoli che condividono uno spigolo
devono dare ai vertici comuni la stessa UV e lo stesso colore. Provate le 6
permutazioni, scartate le coppie dove combaciano tutte o nessuna:

| test | lettura vecchia | +28, +30, +14 | altre (max) |
|---|---|---|---|
| colori, triangoli dei modelli, 7 file | 6 | **1195** | 64 |
| UV, triangoli dei modelli, 7 file | 27 | **418** | 67 |
| UV, terreno `L03A`, increspature (336/353) | **0** | **48** | 0 |
| UV, terreno `L01a` | 35 | **151** | 25 |

Lo stesso test sui quad `0x40` (24 permutazioni) conferma la loro lettura
attuale (4706 contro 2492 della seconda): il difetto e' solo nei triangoli.
Il nuovo ordine e' una rotazione, quindi il verso delle facce non cambia.

**A schermo:** le increspature attorno ai pali, prima spezzate in due mezzi
cerchi sfalsati, sono anelli interi centrati sul palo; si sistemano anche la
decorazione a spirale sul bordo dei moli e il teschio della bandiera pirata
(in alto a sinistra dalla camera in (202, 18, -117)).

**Non provato:** il triangolo piatto `0x34` ha la stessa forma (primo indice
a +14, subito dopo la terza UV) ma solo 50 primitive in tutti i dati e
nessuna coppia adiacente nei file provati: resta con la lettura vecchia.

## 278 — Un'animazione ha un blocco per tick, e ogni blocco porta solo cio' che cambia

`PROVEN_RAW_DATA` per la struttura, `REBUILD_VERIFIED` a schermo.

Negli stream di animazione (tipi 2 e 4) i tempi dei blocchi valgono 0, 1, 2,
... senza buchi: un blocco e' un tick. Il primo blocco porta la posa
completa, i successivi solo i record TRS delle parti che si muovono (la
carota 111: 17 blocchi, dal secondo in poi solo la rotazione della parte 2).
Lo stato quindi si **accumula** blocco per blocco, senza interpolazione.
`rig.animation` restituisce le trasformazioni di ogni fotogramma a partire
dalla posa che `rig.construct` usa da fermo (stesso blocco).

In `L03A` 29 oggetti piazzati hanno un'animazione di partenza che cambia
davvero qualcosa (carote e carote d'oro che girano, salvagenti con l'elica,
pirati, ...). La carota ai tick 0, 4, 8 e' inclinata a sinistra, di fronte,
inclinata a destra.

**Tick al secondo: 15, misurato** in BizHawk sulla versione PlayStation
(NTSC-U), fotogramma per fotogramma, davanti a una carota normale: un giro in
68, 68 e 67 fotogrammi (203 in 3 giri). L'animazione della carota ha **17
blocchi** e la PlayStation li mostra tutti prima di ricominciare: 17 tick
ogni 67,7 fotogrammi a 60 Hz = **15,07 tick al secondo**, un blocco ogni 4
fotogrammi esatti (la logica gira a 30 al secondo, 0x76010).

**L'ultimo blocco e' un segnaposto di fine giro**: non cambia nessuna parte,
quindi ripete il penultimo fotogramma. Vale per **135 animazioni su 135** in
L03A, L03A2, L03ACOM, L01a e MERLIN. Nel gioco PC la carota gira senza
fermarsi, mentre tenendo quel blocco si ferma per un tick a ogni giro;
`rig.animation` lo toglie. Misurato sulla PlayStation; il PC dovrebbe avere
la stessa logica, non misurato. Il viewer ripete ogni animazione in ciclo,
quindi quelle di un solo giro (una carota che spunta) si vedono ripetersi.

**Il barile in acqua** (modello 239, template 89 e 211) ha due passi: 199, la
salita, con cui il gioco lo fa partire (la cima va da 0 a 1,85 m sull'acqua
in 30 fotogrammi), e 202, galleggia in ciclo (31 fotogrammi, cima a circa
1,96 m). Anche i cloni sono animati.

**Il ponte levatoio** (oggetti 85 e 127-130, modello 217) ha quattro stadi
fermi da 3 blocchi: 118 alzato, 119, 120, 121 abbassato (profondita' 2,6 /
6,2 / 9,4 / 12,0 m), e le transizioni 140, 141, 142 tra uno stadio e il
successivo, 198 tutto giu', 199 tutto su. Il gioco parte da 118.

## 279 — Sprite, cloni annidati e punti di aggancio: le torce

`PROVEN_RAW_DATA` per la catena e per la fusione degli sprite, `STRONG` per
l'aggancio (lettura coerente con i dati, non letta nel codice).

**Gli sprite.** Un template con una risorsa `0x40` (fotogrammi, 275) e senza
`0x0B` e' uno sprite del mondo: `L03A` ne ha 20. Il record `0x64` porta
larghezza e altezza a +12/+14 in unita' del mondo, e la fusione con la
**stessa codifica delle facce**: bit 3 del flag a +2 = semitrasparente, modo
nei bit 5-6 della parola a +6. Il bagliore della torcia (texture 250, fondo
nero) ha flag 0x09 e parola 0x20: additivo. La fiamma (218-222, 32x64, 5
fotogrammi da 3 tick) ha flag 0x01: opaca, con i pixel trasparenti.

**La catena della torcia.** Due trigger (0x0A, a (23310, -1400, 9125) e
(10100, -1420, 8125)) clonano il template della torcia (ruoli 671 e 861,
modello 165, alta 1,4 m). La torcia, nel suo passo di partenza (chiave 3),
clona a sua volta la fiamma (657/866) e il bagliore sulla propria parte 3, la
cima. La regola che clona la fiamma una seconda volta ha la chiave 157, un
altro passo (la torcia che si spegne?), e non vale all'avvio.

**L'aggancio.** Col bit `0x80` dell'effetto il campo +24 sceglie una parte
del genitore. I record di **tipo 0xA** delle animazioni marcano una parte per
tick: la cima della torcia (parte 3), la mano del pirata che lancia (parte 23
dell'oggetto 108), i tre posti dei forzieri (parti 4, 3, 2). Lettura
adottata: la k-esima parte marcata `0xA`, e senza marcature la k-esima figlia
della radice (274). Mette la fiamma in cima alla torcia; con la lettura
vecchia sarebbe finita alla base.

**Nel viewer** i cloni sono ricorsivi fino a tre livelli; nei template valgono
le regole del passo di partenza vere all'avvio. Gli sprite sono quadrati
rivolti alla camera sul punto di aggancio.

**Origine dello sprite:** il record `0x64` non porta un'origine. Nel gioco la
fiamma **poggia** sulla cima della torcia (anche in una schermata PlayStation
con la torcia accesa sull'isoletta), quindi il viewer disegna ogni sprite col
lato inferiore sul punto di aggancio. Per gli altri sprite e' un'estensione,
non una misura.

**Aperti:** i due modelli clonati insieme alla fiamma (670, 659).

## 280 — Le ancore: parti tolte dalla posa (tipo 8, flag 0xB) e la rotazione dell'azione `0x26`

`PROVEN_RAW_DATA` per le parti tolte, `PROVEN_BINARY` per l'asse della
rotazione, `REBUILD_VERIFIED` a schermo. **La velocita' non e' misurata.**

**Chi sono.** Le ancore sono il template di ruolo **533** (modello 168),
clonato da **4 trigger** (tipo 16, oggetti 145-148) con la condizione `0x27`
"bit spento" su `tabel1[124]`, vera all'avvio. Il rig ha tre parti con mesh:
la 2 e' l'ancora, la 3 l'ombra, la 4 un terzo pezzo. Nel passo di partenza
(chiave 267, ruolo 248) l'ancora sta **2000 unita' (15,6 m) sopra** il
trigger e l'ombra resta a terra a scala 0,4.

**1. Il record di tipo 8 con flag 0xB toglie una parte.** Nel rig il tipo 8
(flag 0) crea una parte (finding 25 di Ombelll); nelle animazioni il tipo 8
ha **sempre** il flag 0xB (3914 record su 3914 in sette livelli), e non era
letto. La parte 4 dell'ancora lo riceve nella posa 248 e nessuna
trasformazione, quindi veniva disegnata all'origine dell'oggetto, una sagoma
scura a terra.

*La prova che poteva fallire:* se il record toglie la parte, quella che torna
deve essere rimessa da capo. Dopo un `t8 fB` il primo TRS della parte e'
**completo (flag 0xE) in 638 casi su 638**, contro 2443 su 249k (circa 1%)
per un TRS qualunque, che di solito porta solo la rotazione (flag 2).

*La regola:* `rig._apply_records` segna la parte come tolta finche' un TRS non
la rimette; `rig.transforms` le da' una matrice nulla (facce degeneri, non si
disegnano; l'export OBJ le salta). Per la posa ferma una parte tolta conta
come decisa, ma un blocco che toglie **tutto** non e' una posa: molti stream
aprono cosi' (pirata, Merlino) e la posa vera arriva al blocco dopo.

*Cosa cambia* (161 oggetti su 1104 in L03A, L03A2, L03ACOM, L01a, MERLIN; il
censimento resta a zero): i pirati hanno un randello invece di due; la tana
di coniglio (modello 108, 3 in L03A) mostra il buco, prima coperto da una
seconda mesh; sparisce un anello d'acqua ai piedi di Bugs; la carota 114 si
vede solo nella parte alta; diversi oggetti la cui posa non risultava mai
completa ora si animano. Restano invisibili 10 oggetti di L01a e MERLIN la
cui posa di partenza toglie tutte le mesh: nel gioco partono invisibili
(effetti, emettitori).

**2. L'azione `0x26` ruota attorno alla verticale.** Gli indirizzi qui sono
quelli della build `74AB71E1…` (scoperta 264), il cui codice e' spostato
rispetto agli indirizzi dei documenti di Ombelll (verificato sulla tabella
delle azioni: i gestori 0x17 e 0x19 cadono 0x90 dopo): sull'altra build vanno
ritrovati per firma di byte. Il gestore, a `0x0042D070` (tabella delle azioni a `0x004AC6E0`), fa
`[obj+0xC0]+0x12 += valore*16 + indice` (s16 a +4 e +6 del record
dell'azione, cioe' `p[16]` e `p[18]` della regola). `obj+0xC0` punta a
`obj+0xCC` (`lea edx,[eax+0xCC]; mov [eax+0xC0],edx`, anche nel caricatore a
`0x0042FEFB`), quindi il campo e' `obj+0xDE`, e il caricatore (`0x00430250`)
vi copia la **seconda** s16 della rotazione del load script: la Y.
`loadscript` esporta la parola intera come quarto elemento di `action`
(finding 138 di Ombelll).

La prima regola dell'ancora nel passo 267 e' `[0x26, 0, 136]`, senza
condizione e con `0x8000`: il gestore del tipo 14 percorre il passo a ogni
tick (finding 188 di Ombelll), quindi l'ancora gira di **136/4096 di giro a
ogni tick della logica**. Le altre regole del passo descrivono la caduta: la 2
azzera l'orologio dell'oggetto (azione 25) col giocatore entro 300, la 5
cerca un ruolo 725 (i pirati) entro 160, la 4 cambia stato quando l'orologio
(`0x16`, `obj+0x22`) passa 30. Stato 501: 153 (l'ombra cresce), 348 (cade),
198 (a terra).

**Nel viewer** i gruppi di un oggetto che gira hanno la loro matrice:
rotazione attorno alla verticale per il punto dell'oggetto (esatta quando la
rotazione di base ha X e Z nulle, come per tutte e 4 le ancore). Di default le
ancore si vedono sempre (`tools/preferences.py`, ruolo 533): in aria, che
girano, con l'ombra a terra. La caduta non e' simulata.

**Non misurato: la velocita'.** Con 2 passaggi delle regole per tick
d'animazione (logica a 30 al secondo, 278) un giro sono 4096/136 = 30,1
passaggi, **1,0 s** (60 fotogrammi PlayStation). Se le regole girassero una
volta per tick d'animazione sarebbero 2,0 s (120 fotogrammi). Decide una
misura fotogramma per fotogramma in BizHawk (`RULE_PASSES_PER_TICK` in
`tools/viewer.py`).

**Escluso di proposito:** il pirata 110 ruota di 60×16 = 960 (84°) in ognuno
dei suoi quattro stati, e ogni stato finisce quando arriva vicino a un punto
di passaggio (ruoli 58, 139, 140; effetto `0x10000000` senza `0x8000`): e' un
giro di ronda, non una rotazione continua. `_spin_speed` non fa girare gli
oggetti con un passo cosi'; e' materia dei nemici in movimento.

**Le parti tolte, oggetto per oggetto:**

* *Il "vortice" ai piedi di Bugs* nel gioco non c'e' in quel punto. E' la
  parte 36 (mesh 34, disco di 1,56 m, additivo, texture 303: una girandola),
  figlia della radice. La posa 35 la toglie; tra le animazioni di Bugs in
  L03A solo la **28** (stato 30, passo 37) la mette, **3 m sopra la radice**
  e ruotante per 14 tick: le orecchie a elica con cui Bugs rallenta la
  caduta. Senza una posa che la posizionasse, veniva disegnata all'origine
  della parte, dentro le assi. Lo stesso per le parti 37 e 38 (due quadrati
  additivi da 2,5 m, texture 304 e 305, anelli di scia): la 38 compare solo
  nella 365 (stati 21 e 90, 4 tick), la 37 mai in L03A. Il modello di Bugs
  porta le mesh di tutti i suoi effetti; e' l'animazione a decidere quali si
  vedono.
* *Il secondo randello dei pirati* (mesh 10, identica alla mesh 15 di quello
  in mano) e' tolto **esplicitamente in tutte e 19** le animazioni del pirata
  di L03A e in nessuna riceve una posizione; idem nelle 27 del pirata di
  L03A2 (modello 256). L03ACOM non ha questo pirata. Pirati con due randelli
  in altri livelli non sono esclusi; non controllato. Non tolto, stava
  all'origine della parte 11, figlia della 9: nell'altra mano, per questo
  sembrava naturale.
* *La tana di coniglio* (modello 108) ha due mesh della stessa forma con
  texture diverse: la 1 col buco (207/208), la 2 senza (208/209). L'oggetto
  ha una sola animazione (149), usata da entrambi i suoi stati, che toglie
  sempre la 2: coi soli dati dell'oggetto la tana si vede sempre aperta. In
  L03A sono tre. La **100** (221,1; -116,0 m) sta sotto una cassa che Bugs
  sposta; la **99** (236,3; -155,9) e' sull'isola: ruoli 210 e 209, una
  coppia. Nel gioco, entrando nella tana sotto la cassa si attiva il buco
  dell'altra. Nei dati entrambe fanno entrare sempre (azione 47, entro 200);
  cio' che cambia l'aspetto della 99 non e' nella sua animazione e non e'
  stato trovato. La **62** (22,9; -32,5, vicino alla partenza) fa entrare
  (entro 400) solo col bit 0x80 di `tabel1[102]`, che l'oggetto 97 accende nel
  passo 199. L'oggetto 97 e' il **barile esplosivo** (modello 157) che sta
  sopra la tana; nel gioco la tana si apre dopo l'esplosione del barile,
  acceso con la torcia. Nel passo 199 il barile clona l'esplosione (ruoli 548
  e 669, la stella bianca) e i suoi pezzi (662), accende il bit e si spegne
  (effetto 0x10000). Il legame con la torcia NON e' provato: lo stato 3 del
  barile ha la condizione `0x0C` (`player+0x17c`) sul valore 69, forse "Bugs
  tiene la torcia". Il viewer mostra tutte le tane aperte.

**Aperti:** l'ancora e' inclinata di circa 40° nel proprio piano (di taglio
lo stelo e' verticale): cosi' e' il modello, da confrontare col gioco. Il
terzo pezzo (parte 4) compare nello stato 404 (ruoli 371 e 211) a +398 in z:
forse l'ancora piantata.

## 281 — Le varianti `_8` non sono nella tabella dei livelli

`PROVEN_BINARY` per la tabella, `PROVEN_RAW_DATA` per i file.

La tabella dei livelli di `bugs.exe` (111 voci da 24 byte a partire da
`..\BZE\TITLE.BZE;1`; l'indice e' il LevID) nomina 111 file. I dati del gioco
contengono nove file `_8` che non vi compaiono: `L01D1_8`, `L01D2_8`,
`L03A_8`, `L03A2_8`, `L03ACOM_8`, `L03B_8`, `L03C_8`, `L04B3_8`, `LB04_8`.
Hanno lo stesso numero di oggetti con modello dei livelli omonimi (per
esempio 77 per `L03A` e `L03a_8`), quindi sono copie o varianti. Senza una
voce nella tabella il gioco non li carica per LevID; il viewer li elenca in
Extra.

**Cosa cambia** (sei coppie: `L03A`, `L03A2`, `L03ACOM`, `L01D1`, `LB04`,
`L04B3`): i due file hanno 10 sezioni; le sezioni 2 e 5-10 sono identiche
byte per byte, cambiano solo la 1 (load script), la 3 (texture) e la 4
(modelli e terreno), di pochi KB. `L03a_8` ha 281 oggetti contro 282 e 439
texture contro 442; `L04b3_8` ha texture identiche. **Non** sono versioni con
texture a 8 bit: la quota di TIM a 4 e a 8 bit e' la stessa (`L03A` 413/29,
`L03a_8` 407/32). Non sono nemmeno il suffisso di lingua (`_0`, `_1`, `_3`),
che riguarda solo le schermate di caricamento `L_*`. Probabilmente un'altra
revisione degli stessi livelli; quali oggetti e texture cambino non e' stato
elencato.

**Controllo incrociato.** La tabella combacia con un foglio LevID
indipendente (riga r = LevID r + 1) per tutte le 70 voci che il viewer usa:
titolo e nota sono confrontati parola per parola da
`tools/diagnostics/check_levels.py`, che trova un file scambiato o una nota
sbagliata introdotti apposta. La tabella nomina anche file che non sono nei
dati del gioco: `LANGUAGE`, `LB05`, i cinque `DEMO*`, `SCREEN4`, `SCREEN5`.

## 282 — I settori `0x1000`: un quad per record, in due ordini dei vertici

`PROVEN_RAW_DATA`.

Il finding 15 di Ombelll e il MODELFORMAT ("Modus 0x10") descrivono i settori
del terreno con modus `0x1000` come facce invisibili di confine e di
collisione: un record da 20 byte con un quad negli indici globali dei vertici
del blocco. Misurato sui 79 livelli del menu del viewer
(`tools/diagnostics/check_walls.py`):

- **1527** record in **26** livelli (nessuno in `L03A`); tutti lunghi 20
  byte, `n_bound_faces` 0, conteggio 1. Un record di `CCEND` risulta lungo
  16384 byte: quel livello comunque non si costruisce.
- I quattro `u16` a `+8` stanno **tutti** dentro il numero di vertici del
  blocco (1527 su 1527), e **tutti** i 1527 quad sono verticali (normale
  entro 0,2 dal piano orizzontale): le "tende".
- **L'ordine dei vertici non e' fisso.** Preso a ventaglio (0,1,2,3) il quad
  e' convesso in 1434 casi (11 dei quali in entrambi gli ordini), preso a Z
  come la PlayStation (0,1,3,2) in 104; 93 quad sono convessi **solo** a Z.
  Il viewer prende l'ordine che da' un quad convesso.
- Gli ultimi 4 byte (`+16`, un `u32`) contengono piccoli numeri (i piu'
  frequenti 5, 9, 6, 4, 2): **non letti**. Un tipo di superficie o di
  collisione e' un'ipotesi.

Il viewer li disegna solo a richiesta (flag Facce 0x1000, 0x1000 faces,
spenta di default). Tutti gli altri gruppi, i limiti del terreno (la camera
iniziale) e il conteggio dei triangoli sono identici byte per byte con e
senza, in 78 livelli su 78. Se nel gioco facciano da muri: vedi 288.

## 283 — Facce che si vedono e su cui non si sta

`PROVEN_RAW_DATA` per la lettura, una regola dichiarata per la
classificazione.

Il gioco non si scontra col terreno che disegna ma con la heightmap di
collisione (blocco `0x36`, finding 110-116 di Ombelll). `tools/collision.py`
la legge come quei finding la descrivono: record da 68 byte, un `u16` per
cella da 320 unita', tessere 8×8 di byte d'altezza con segno, `0x7E`/`0x7F` =
niente terreno, offset relativi al numero di record. Prove
(`tools/diagnostics/check_collision.py`, 79 livelli del menu):

- **479 su 479** record hanno celle × 320 == estensione su entrambi gli assi;
- al centro delle facce calpestabili visibili il terreno della heightmap sta
  a una mediana di **7 unita'** (circa 5 cm) dalla faccia, contro **147** per
  una cella a caso dello stesso blocco: coordinate del gioco = vertice +
  spostamento del blocco, Y verso il basso, come per il resto del terreno.

**Dov'e' l'alto.** Tra le facce con terreno combaciante sotto, 8384 hanno la
normale Y positiva (nello spazio del gioco con la Y in basso, con l'ordine
dei vertici del file) e 59 negativa: positivo e' l'alto. Le facce con normale
negativa sono il sotto di pontili e piattaforme, e restano fuori.

**La regola** (flag Senza collisione, No collision): una faccia con la
normale in alto entro circa 45° dalla verticale e' senza collisione se, al
suo centro, nessun blocco ha terreno entro **100 unita'** da lei, la soglia
di scalino del gioco (finding 116 di Ombelll). Sui livelli del menu sono
**20 967** facce. Su un campione di una su cinque i motivi sono: sotto-cella
marcata `0x7E`/`0x7F` 2693; terreno piu' in basso di 100 unita' (si cade)
646; piu' in alto (la faccia sta sotto il pavimento vero) 455; fuori da ogni
blocco 298. In `L03A` segna i bordi d'acqua bassa delle isole e sotto i
margini dei pontili, non le assi su cui si cammina.

Non coperti: muri e soffitti (si scontrano con lo sweep, non con la query),
gli oggetti (i loro box, 284), le facce solo in parte sopra il terreno (si
prova solo il centro).

## 284 — Un box per oggetto: il muro invisibile sopra il vetro in `L05A3C`

`PROVEN_RAW_DATA` per i box; che questo box sia il muro invisibile che si
incontra nel gioco e' una spiegazione, non ancora misurata nel gioco.

Sopra la ringhiera di vetro in `L05A3C` (la stanza di Mastermind) c'e' un
muro invisibile che non e' un settore `0x1000` (282), e nemmeno la heightmap
di collisione ha un muro duro li'. E' il box di un oggetto. Gli oggetti
collidono col box del record di tipo 9 della loro animazione (finding 123 di
Ombelll: sei angoli `s16` nello spazio dell'oggetto, provati ruotati con
l'oggetto da `FUN_004313a0`). Il viewer lo disegna (flag Box di collisione,
Collision boxes; `montage.collision_box`: il primo record di tipo 9 dello
stream della posa di partenza).

- L'oggetto **24** (modello 81) e' la ringhiera di vetro coi due piloni, di
  traverso sulla griglia 4×4 di piastrelle del pavimento (oggetti 25-40, un
  box da 320 unita' ciascuno). Il suo box e' una lastra larga **2648** unita',
  profonda **102** e alta **748** (circa 20,7 × 0,8 × 5,8 m): tutta l'altezza
  dei piloni per tutta la larghezza. Il vetro e' piu' basso; sopra, il box
  continua, e ne viene un muro che non si vede.
- L'oggetto **84** (modello 292), la colonna di stelle al centro della
  stanza, ha un box **1300 × 19 332 × 1300**: circa 150 m di altezza.
- In entrambi i casi il box e' esattamente l'estensione dei vertici del
  modello: un box solo attorno a tutto il modello, quindi ogni vuoto sotto di
  lui collide.

3892 box sui livelli del menu (quelli grandi in pianta quanto il livello,
cupole del cielo e mare, restano fuori: coprirebbero tutto). Con e senza,
ogni altro gruppo e' identico byte per byte (`check_walls.py`).

## 285 — Le regole delle zone: effetti a +16; le zone che uccidono o riportano indietro

`PROVEN_RAW_DATA`.

Nel record `0x33` da 32 byte di una zona la parola degli effetti sta a
**+16**, non a +20 come nelle regole degli oggetti (`0x31`): condizione a +8,
azione a +11, effetti a +16, i tre parametri a +20/+24/+28 (il finding 100 di
Ombelll conta tre parole di parametri). Prova: le sei zone della rete di
recupero di `L04A2` portano l'effetto `0x40000000` e i parametri
**(7900, −15520, 5000)** a +20..+28, il punto d'arrivo che danno le note
SPEEDRUN di Ombelll, nelle zone 33, 35, 36 e 37. Leggendo gli effetti a +20
nessuna regola del corpus ha nessuno dei due bit. Il box della zona e'
origine + (estensione X, estensione Z), e in Y dal suo piano in su del
"limite" negativo dell'opcode `0x1C`; la quarta parola e' il raggio in pianta
come `u16` (40 481 per i 32 569 × 24 041 di `L03A`, √ = 40 480).

Sui livelli del menu: **165** zone con l'effetto `0x200000` (morte: serie di
animazioni e contatore delle vite azzerato, finding 169 di Ombelll) in 46
livelli, 15 zone di teletrasporto in 4, 9 zone di danno (azione `0x48`) in 3,
70 checkpoint in 57. Le zone di morte piu' grandi coprono tutto il livello:
il mare di `L03A` a Y −300, l'abisso di `L05A5`. Il viewer chiama **pavimento
della morte** una zona che copre almeno meta' della pianta del terreno (flag
Pavimento della morte, Death floor, 23 zone); le altre 153 sono zone di morte
(flag Zone di morte, Death zones). Le condizioni delle regole non si
valutano.

## 286 — Quello che si vede contro quello su cui si sta: terreno invisibile, pixel, muri finti

`PROVEN_RAW_DATA` per la lettura della heightmap (283); le classificazioni
sono regole dichiarate, confrontate con casi noti dal gioco.

- **Terreno invisibile** (parte della flag Terreno di collisione, Ground):
  terreno della heightmap senza una faccia visibile in alto entro 100 unita'
  al centro della sua sotto-cella da 40. In `L01A` disegna, sospesa nel pit,
  la piattaforma ottagonale che solo la variante notturna `L01D1` mostra.
- **Pixel di atterraggio**: una sotto-cella con terreno i cui 4 vicini nello
  stesso blocco non ne hanno: 40 × 40 unita', circa 30 cm. `L01B` ne ha 18
  (nel gioco ci si puo' atterrare in caduta libera nel pit); 601 sui livelli
  del menu.
- **Muri duri**: i bordi delle sotto-celle `0x7F`, muri a qualunque altezza
  (finding 116 di Ombelll). In `L03D1` fiancheggiano la porta rotonda e il
  cancello; sopra il cancello il box dell'oggetto (284) e' il muro invisibile
  che si incontra nel gioco.
- **Muri finti** (ritirati nella 288): le facce verticali del terreno che si
  attraversano. Il lato aperto e' quello opposto alla normale del file (sulle
  facce verticali col terreno da entrambi i lati e' il lato piu' basso 2094
  volte su 2528, la stessa convenzione delle facce in alto); stando li'
  all'altezza del proprio terreno, dietro la faccia non c'e' ne' una
  sotto-cella `0x7F` ne' terreno piu' di 100 unita' sopra. 20 936 facce sui
  livelli del menu; in `L01B` sono le pareti interne dell'anello di canyon,
  che nel gioco non hanno collisione.

Ogni altro gruppo e' identico byte per byte con e senza queste
sovrapposizioni in 78 livelli su 78 (`check_walls.py`). Non coperti: facce e
piattaforme degli oggetti.

## 287 — I blocchi di collisione sono lastre impilate; la loro cima come soffitto e' solo un candidato

`PROVEN_RAW_DATA` per l'impilamento; il soffitto e' un'ipotesi con un
conteggio di controesempi.

Il campo +24 di un record di collisione si chiama "bottom Y" nel finding 110
di Ombelll; con la Y del gioco verso il basso sta sempre **sopra** il piano
+20, cioe' e' la cima del blocco. Il blocco e' una lastra da +20 in su fino a
+24, e i blocchi di un'area si impilano esatti, base su cima (`L01B` area 9:
960 → −1920 → −2448 → −2880 → −9280). Il box a +36 lo ripete (origine, poi
dimensioni con altezza +24 − +20). `L03D1` ha un solo strato ovunque,
0 → −6400, circa 22 m sopra il suo terreno piu' alto.

La cima della lastra piu' alta di ogni pila e' il candidato naturale per un
soffitto che chiude un livello. Non e' un soffitto ovunque: in **37 pile su
297** sui livelli del menu il terreno di collisione della pila sale sopra
quella cima, e sopra un soffitto vero non si puo' stare. Distanza mediana fra
il terreno di collisione piu' alto e la cima nelle altre 260: 4440 unita'. Da
decidere nel gioco. Il viewer disegna le pile come Box delle aree (Area
boxes, 288).

## 288 — Le flag di collisione del viewer, riviste sul gioco

Regole dichiarate; ogni cambiamento segue qualcosa osservato nel gioco.

- **Le facce 0x1000 del terreno non sono muri.** In `L03D1` una sta dove il
  muro invisibile vero e' il box di un oggetto (284) e l'altra non ferma
  niente. Quindi, almeno li', non fanno da muri invisibili di confine come
  dicono il finding 15 di Ombelll e il MODELFORMAT "Modus 0x10". La 282 resta
  come lettura del formato; a cosa servano e' aperto (trigger, piani di
  caricamento?). Hanno una flag loro, Facce 0x1000 (0x1000 faces).
- **Muri invisibili (Invisible walls) = muri duri senza niente di
  disegnato.** I bordi `0x7F` della heightmap (finding 116 di Ombelll) senza
  una faccia visibile quasi verticale, del terreno o di un oggetto piazzato
  nella posa di partenza, che passi entro ±2 sotto-celle (80 unita') dal bordo
  all'altezza del pannello. `L03D1`: 706 pannelli di muro duro su 2942;
  `L03A`: 56 su 114.
- **Senza collisione (No collision), sicuro o trappola.** Dal centro di una
  faccia senza collisione la caduta incontra o il terreno (sicuro, ciano
  acceso) o prima una zona che uccide, ferisce (azione 0x48) o teletrasporta
  (trappola, ciano scuro tenue). La lava di `L03D1` e' una trappola sopra la
  sua lastra della morte, tranne una striscia a z 195–290 appena fuori dalla
  lastra: un candidato per il punto sicuro sulla lava noto dal gioco.
  `L03D1`: 45 sicure, 451 trappole.
- **Muri finti ritirati**: schermate del gioco mostravano la flag segnare
  pareti che chiaramente fermano.
- **Box delle aree (Area boxes) al posto del soffitto**: ogni pila della
  heightmap disegnata come un box intero, solo spigoli (287: la cima e' un
  soffitto al massimo in alcuni punti). Non verificati.
- I Muri duri (Hard walls) si disegnano in pannelli continui (base 16 unita'
  sotto il terreno piu' basso del tratto, cima 5 m sopra il piu' alto); il
  Terreno di collisione (Ground) 16 unita' sopra la heightmap, sopra le
  texture con cui combacia.
- Un difetto del viewer trovato strada facendo (stampo delle facce per
  modello in cache per `id()` di un elenco di facce il cui id poteva essere
  riusato dopo la liberazione: IndexError) e' corretto; `check_walls.py` e
  `check_level_cache.py` rilanciati.
