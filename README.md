# TITAN — asistent personal pentru Windows

Asistent personal în Python, cu interfață desktop pentru Windows, wake word local,
transcriere vocală și comenzi pentru laptop. Include integrări configurabile pentru
lumini smart și un server companion pentru telefon/Raspberry Pi. Configurațiile
casei, contactele și modelele descărcate rămân locale.

## Pornire rapidă (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Folosește Python 3.11 sau mai nou. Integrările smart-home și modelele vocale necesită
configurarea descrisă mai jos. Comenzile pentru desktop sunt specifice Windows;
Raspberry Pi este un companion, nu un înlocuitor direct pentru controlul Windows.

## Verificare

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Organizare

- `titan/core`: interpretarea comenzilor și conversațiile.
- `titan/voice`: microfon, wake word, transcriere și răspuns vocal.
- `titan/tools`: control Windows și integrări smart-home.
- `titan/ui`: interfața desktop.
- `titan/mobile`: API local și interfața companion.
- `tests`: teste pentru comenzi și integrări, cu componente simulate.


## Ce poate face acum, fără API key

- deschide Google Chrome sau Spotify;
- deschide YouTube și Google sau caută pe web;
- setează volumul între 0 și 100%;
- oprește/pornește sunetul și face screenshot-uri locale;
- caută melodii în Spotify și controlează play/pause, următoarea sau precedenta;
- deschide Discord, Counter-Strike 2 (prin Steam) și League of Legends, dacă sunt instalate;
- cere confirmare înainte de a închide tabul ori fereastra activă.

TITAN tolerează mici variații de transcriere pentru comenzile sigure, de pildă
`deschidă Spotify` sau `deschide Spotifai`. Acțiunile cu risc nu folosesc
potrivire aproximativă; ele cer formulare clară și confirmare.

## Voce: locală și mai rapidă

Apasă **Testează o comandă vocală acum**, sau activează wake word-ul după ce
este configurat. TITAN ascultă o singură comandă și se oprește imediat după o
pauză scurtă — nu mai captează trei ture de sunet ori muzică din difuzoare.
Transcrierea păstrează modelul Whisper `base` local, mai potrivit pentru
română și titluri de melodii în engleză. Răspunsul este mai rapid fiindcă
ascultarea se încheie la prima pauză și transcrierea folosește o decodare
rapidă. Modelul se descarcă o singură dată în `models/`; ulterior nu are nevoie
de API key și nu trimite audio în cloud.

TITAN răspunde și vocal prin vocea disponibilă în Windows. Dacă nu există o
voce română instalată, va folosi vocea implicită până configurăm una.

## Wake word local: „Titan”

Aplicația pornește acum o fereastră cu butoanele **Start — ascultă „Titan”** și
**Stop**. Când este activă, detectarea wake word-ului rulează local. După
„Titan”, TITAN poate primi o comandă și încă două replici consecutive, apoi
revine în starea de așteptare. Wake word-ul folosește Vosk cu un model local
mic, gratuit, de aproximativ 40 MB. Modelul ascultă doar cuvântul „Titan”, iar
Whisper preia comenzile după activare. Nu necesită cont, cheie sau API.

Până termini configurarea, butonul **Testează o comandă vocală acum** păstrează
modul vocal local fără wake word.

## Comenzi disponibile

- `deschide Chrome`, `deschide Google`, `deschide YouTube`, `deschide Discord`;
- `deschide CS2`, `deschide League of Legends`;
- `caută pe Google vremea`, `pune Creep`, `play`, `next`, `pauză`;
- `volum 40`, `mute`, `pornește sunetul`, `fă screenshot`;
- `pornește laptopul` sau `wake laptop` (după configurarea Wake-on-LAN pe Pi);
- `închide tabul` sau `închide fereastra`, apoi confirmă cu `da`.

TITAN nu poate executa instrucțiuni arbitrare. Fiecare comandă trebuie să se
potrivească unei acțiuni din listă; acesta este intenționat, pentru viteză și
siguranță.

## Lumini smart, local prin Home Assistant

Am pregătit integrarea, dar ea este dezactivată până o configurezi tu. Pentru
control local recomand **Home Assistant** în rețeaua casei. După ce ai un hub
Home Assistant, copiază `smart_home.example.json` în `smart_home.json`, adaugă
URL-ul local, tokenul și identificatorii propriilor lumini. Fișierul real este
ignorat de Git, deci tokenul nu ajunge online.

Pentru pornirea laptopului, copiază `laptop.example.json` ca `laptop.json` şi
completează ulterior MAC-ul. Fișierul real este ignorat de Git. Wake-on-LAN va
fi trimis de Raspberry Pi doar din rețeaua locală; telefonul nu comunică direct
cu laptopul.

Exemple după configurare: `aprinde luminile din dormitor`, `stinge luminile`,
`pune luminile albastre în birou`, `lumina din living la 40%`.

## WhatsApp Web: contacte locale și confirmare

TITAN poate deschide WhatsApp Web cu un mesaj pregătit, dar nu îl trimite
automat. Copiază `contacts.example.json` în `contacts.json` și completează
singur numerele în format internațional, numai cu cifre (de exemplu
`407XXXXXXXXX`). Fișierul real este ignorat de Git.

Fluxul vocal recomandat: `deschide WhatsApp`, apoi `trimite mesaj lui mama`,
apoi `textul ajung acasă în zece minute`. TITAN repetă destinatarul și textul;
spune `da` doar dacă sunt corecte. WhatsApp Web se deschide cu textul pus în
conversație. Când conversația este afișată, spune `trimite`; TITAN aduce
fereastra WhatsApp în față și trimite mesajul confirmat. Spune `nu` pentru a
anula înainte de pasul final.

## API: pregătit, dar oprit

TITAN rulează complet local în această etapă și nu trimite voce sau texte către
un API. Fișierul `.env.example` include pentru viitor un plafon inițial de
100 cereri plătite/lună și un buget țintă de 3 EUR/lună. API-ul nu poate fi
activat accidental: trebuie adăugată manual o cheie și setarea explicită
`TITAN_API_ENABLED=true`.

Exemple: `deschide Google`, `caută pe Google vremea`, `deschide Spotify`,
`pune melodia Blinding Lights`, `dă play`, `următoarea melodie`,
`pune volumul la 30`, `închide tabul` urmat de `da`.

> Dacă Google Chrome nu este instalat, comanda pentru Chrome deschide o pagină
> în browserul implicit și explică acest lucru.

## Aplicația de telefon: TITAN Command Center

Aplicația pentru telefon este pregătită ca PWA (aplicație instalabilă din
browser), cu conversație text, comenzi rapide și confirmări separate pe fiecare
sesiune. Înainte de Raspberry Pi, o poți previzualiza local astfel:

```powershell
.\.venv\Scripts\python.exe -m titan.mobile.server
```

Deschide apoi `http://127.0.0.1:8787`. Preview-ul este intenționat disponibil
doar pe laptop. Când mutăm proiectul pe Pi, îl vom păstra pe `127.0.0.1`, vom
seta `TITAN_MOBILE_ACCESS_TOKEN` în `.env` şi îl vom expune privat prin
Tailscale Serve — fără port forwarding sau acces public la rețeaua casei.

## Instalare

Ai nevoie de Python 3.11 sau mai nou. Deschide PowerShell în acest folder și rulează:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Nu este nevoie de o cheie API pentru această etapă.

## VS Code

Deschide folderul proiectului în VS Code. Configurația din `.vscode` selectează
automat mediul `.venv`. Din fila **Run and Debug**, alege `Pornește TITAN
(terminal)` și apasă `F5`. Extensia oficială Python va fi sugerată automat dacă
nu este instalată. Testele pot fi descoperite din fila Testing sau rulate cu
comanda de mai jos.

Pentru a verifica logica fără a controla laptopul, rulează:

```powershell
python -m unittest discover -s tests -v
```

## Structură

- `app.py` — pornește interfața de terminal;
- `titan/core` — înțelegerea comenzilor și fluxul de confirmare;
- `titan/tools/windows` — singurul modul care controlează Windows;
- `titan/voice` — rezervat pentru microfon, Whisper și TTS;
- `titan/security` — rezervat pentru politici și recunoaștere vocală;
- `tests` — verificări automate fără a deschide aplicații;
- `docs` — explicații suplimentare în română.

## Siguranță

TITAN nu execută cod arbitrar dintr-o comandă. Nucleul trimite cereri doar către
acțiuni declarate explicit. Acțiunile care pot închide sau pierde conținut cer
confirmare. În viitor, ștergerea, mutarea fișierelor, mesajele și oprirea
laptopului vor avea reguli mai stricte.

## Următorii pași

1. testăm comenzile text pe acest laptop;
2. adăugăm microfonul și răspunsurile vocale;
3. conectăm un model AI prin API;
4. introducem un agent Raspberry Pi și Home Assistant.
