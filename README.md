# TypeStream

**Sprich — und der Text erscheint dort, wo dein Cursor blinkt.**

TypeStream ist ein Diktier-Tool für Windows. Du hältst eine Taste, sprichst, lässt los — der gesprochene Text wird transkribiert und automatisch in das gerade aktive Fenster getippt (E-Mail, Chat, Word, Browser, egal wo). Im Hintergrund läuft TypeStream als kleines Symbol unten rechts neben der Uhr (im "Tray").

---

## Inhalt

1. [Erste Schritte](#1-erste-schritte)
2. [So funktioniert die tägliche Bedienung](#2-so-funktioniert-die-tägliche-bedienung)
3. [Das Hauptfenster (Verlauf)](#3-das-hauptfenster-verlauf)
4. [Das Tray-Symbol](#4-das-tray-symbol)
5. [Die Einstellungen — alle Optionen erklärt](#5-die-einstellungen--alle-optionen-erklärt)
6. [Was tun, wenn etwas nicht klappt?](#6-was-tun-wenn-etwas-nicht-klappt)

---

## 1. Erste Schritte

Beim ersten Start öffnen sich automatisch die **Einstellungen**, weil TypeStream wissen muss, wie es deinen Text in Schrift umwandeln soll. Es gibt zwei Wege:

- **OpenAI (Cloud)** — empfohlen für die meisten. Schnell, sehr gute Qualität, kostet ca. 0,2–0,4 Cent pro Minute Audio. Du brauchst einen API-Key von OpenAI (siehe unten).
- **Faster-Whisper (Lokal)** — läuft komplett auf deinem Rechner, ohne Internet, ohne Kosten. Beim ersten Mal lädt TypeStream das Sprachmodell einmalig herunter (ca. 75–470 MB).

### Wenn du OpenAI nutzen willst

1. Geh auf [platform.openai.com](https://platform.openai.com), erstelle ein Konto und lade ein paar Euro Guthaben auf.
2. Erstelle dort unter "API Keys" einen neuen Schlüssel (beginnt mit `sk-...`).
3. In TypeStream → Einstellungen → **Transkription** → Feld **API-Key** den Schlüssel einfügen.
4. Fertig — du kannst loslegen.

### Wenn du lokal arbeiten willst (ohne Cloud)

1. In den Einstellungen → **Transkription** → Quelle auf **Faster-Whisper (Lokal)** stellen.
2. Klick auf **Faster-Whisper installieren**. Das Modell wird im Hintergrund geladen — das dauert beim ersten Mal etwas.
3. Fertig — keine Internet-Verbindung mehr nötig, keine Kosten.

---

## 2. So funktioniert die tägliche Bedienung

TypeStream hat **keinen großen Aufnahme-Knopf zum Klicken** — der Sinn ist ja, dass du nicht das Fenster wechseln musst. Stattdessen benutzt du eine **Aufnahme-Taste** (Standard: **F9**), die überall in Windows funktioniert, egal welches Programm gerade offen ist.

### Push-to-Talk (Standard)

Wie bei einem Walkie-Talkie:

1. Cursor in das Feld setzen, in das der Text soll (z. B. E-Mail-Fenster).
2. **F9 gedrückt halten** und sprechen.
3. **F9 loslassen** — nach ein, zwei Sekunden erscheint der Text dort, wo dein Cursor war.

Während der Aufnahme erscheint unten in der Bildschirmmitte ein kleiner schwebender Hinweis ("Overlay") — daran erkennst du, dass das Mikrofon zuhört. Zusätzlich hörst du beim Start- und Stop-Drücken einen leisen Ton.

### Toggle-Modus (Alternative)

Wenn du nicht ständig die Taste halten willst:

1. **F9 drücken** → Aufnahme startet, du kannst die Taste loslassen.
2. Sprechen, so lange du willst.
3. **F9 erneut drücken** → Aufnahme stoppt, Text wird eingefügt.

Diesen Modus stellst du in Einstellungen → **Hotkeys** → **Modus** um.

### Letzten Text nochmal einfügen

Klappt das Auto-Einfügen mal nicht (kommt z. B. bei manchen Spielen oder Admin-Fenstern vor), kannst du den letzten Text mit **Strg + Alt + V** noch einmal einfügen.

---

## 3. Das Hauptfenster (Verlauf)

Doppelklick auf das Tray-Symbol (oder Rechtsklick → "Verlauf öffnen") öffnet das Hauptfenster. Es zeigt deine letzten Aufnahmen.

### Was ist oben zu sehen?

- **"TypeStream"** als Titel, darunter wie viele Wörter du heute und insgesamt diktiert hast.
- **STIL** (rechts oben) — ein Dropdown, mit dem du blitzschnell den Schreibstil wechseln kannst (Original / Professionell / Locker / Eigener Stil). Mehr dazu unter "Stil" weiter unten.
- **Einstellungen** — öffnet das Konfigurationsfenster.

### Die Verlaufsliste

Jede Zeile ist eine Aufnahme. Links steht der erkannte Text, darunter Datum/Uhrzeit. Falls Benchmark-Modus an ist, stehen zusätzlich die Laufzeiten der beiden Engines daneben.

### Die Buttons unten

- **Kopieren** — legt den ausgewählten Text in die Zwischenablage (du kannst ihn dann mit Strg+V woanders einfügen).
- **Einfügen** — versteckt das Fenster und tippt den Text in das Fenster, das danach den Fokus bekommt. (Tipp: ein **Doppelklick auf einen Eintrag** macht dasselbe wie "Kopieren".)
- **Löschen** — entfernt den ausgewählten Eintrag aus dem Verlauf.
- **Alle löschen** — leert den kompletten Verlauf.

---

## 4. Das Tray-Symbol

Unten rechts neben der Uhr findest du das TypeStream-Symbol. Es wechselt die Farbe:

- **normal** → bereit.
- **rot** → Aufnahme läuft gerade.
- **gelb** → Transkription läuft (Audio wird in Text umgewandelt).

**Rechtsklick** auf das Symbol öffnet ein Menü:

- **Verlauf öffnen** — wie Doppelklick.
- **Einstellungen** — alle Optionen.
- **Stil** — Stil schnell wechseln, ohne Hauptfenster.
- **Letzte Aufnahme kopieren** — den letzten Text in die Zwischenablage legen.
- **Update auf v… laden** — erscheint nur, wenn eine neue Version verfügbar ist.
- **Beenden** — schließt TypeStream wirklich (nur das Hauptfenster zu klicken beendet die App nicht).

---

## 5. Die Einstellungen — alle Optionen erklärt

Die Einstellungen sind in sechs Bereiche aufgeteilt, links in der Seitenleiste.

### 5.1 Transkription

Hier legst du fest, **wer** dein Audio in Text umwandelt.

- **Quelle** — *OpenAI API (Cloud)* oder *Faster-Whisper (Lokal)*. Cloud ist schneller, Lokal ist privat und kostenlos.
- **API-Key** *(nur OpenAI)* — dein Schlüssel von OpenAI (siehe Erste Schritte).
- **Modell** *(nur OpenAI)* — drei Stufen:
  - `gpt-4o-mini-transcribe` (~0,003 $/Min, sehr gutes Preis-Leistungs-Verhältnis — Voreinstellung)
  - `whisper-1` (~0,006 $/Min, klassisches Whisper)
  - `gpt-4o-transcribe` (~0,006 $/Min, beste Qualität)
- **Modell-Größe** *(nur Lokal)* — wie groß das lokale Modell sein soll:
  - `tiny` (~75 MB) — am schnellsten, aber Qualität nur okay.
  - `base` (~150 MB) — guter Kompromiss, voreingestellt.
  - `small` (~470 MB) — beste lokale Qualität, braucht mehr RAM.
- **Sprache** — meistens *Auto-Erkennung*. Wenn du immer in einer Sprache diktierst, hilft eine feste Wahl (z. B. Deutsch) der Erkennung etwas auf die Sprünge.
- **Benchmark-Modus (beide Engines vergleichen)** — Spielerei für Neugierige: jede Aufnahme wird parallel an OpenAI **und** lokal geschickt. Beide Laufzeiten landen unter "Statistik". Eingefügt wird der Text aus der oben gewählten Quelle. Kostet etwas mehr (OpenAI-Aufruf läuft trotzdem) und erfordert, dass beide Engines konfiguriert sind.

### 5.2 Hotkeys

Hier definierst du, **welche Taste** was auslöst.

- **Aufnahme** — die Taste, mit der du das Mikro aktivierst (Standard: **F9**). Klick auf den Button, dann drücke die gewünschte Taste oder eine Maus-Sondertaste. Für Push-to-Talk muss es eine **einzelne** Taste sein (keine Kombination), sonst behandelt TypeStream sie automatisch als Toggle.
- **Modus** — *Push-to-Talk* (Taste halten) oder *Toggle* (drücken: Start, nochmal: Stop). Siehe oben.
- **Letzten Text einfügen** — Taste, die den zuletzt transkribierten Text noch einmal einfügt (Standard: **Strg+Alt+V**). Hier *darf* es eine Kombination sein.

### 5.3 Aufnahme

Alles rund ums Mikrofon und den Aufnahme-Vorgang.

- **Mikrofon** — welches Eingabegerät benutzt wird. *Systemstandard* nimmt das, was Windows als Standard-Mikro eingestellt hat. Ein USB-Headset oder externes Mikro kannst du hier explizit auswählen.
- **Min. Aufnahme-Dauer** — Aufnahmen, die kürzer sind als dieser Wert (Standard: 0,4 s), werden verworfen. So vermeidest du, dass versehentliches Antippen der Taste eine leere Datei zur Transkription schickt.
- **Verlauf-Limit** — wie viele Aufnahmen im Verlauf bleiben (Standard: 50). Ältere fallen automatisch raus.
- **Akustisches Feedback (Start- / Stop-Ton)** — der dezente Piep beim Start und Stop einer Aufnahme. An, wenn du die Bestätigung willst; aus, wenn dich das stört.
- **Aufnahme-Ton** — Lautstärke der Start/Stop-Töne (Schieberegler, 0–100 %).
- **Warnton** — Lautstärke der **wichtigen** Warntöne (z. B. wenn die Transkription fehlschlägt). Separat regelbar, damit die freundlichen Start/Stop-Töne leise sein können, kritische Hinweise aber laut.
- **Visuelles Overlay während Aufnahme** — der schwebende Hinweis am unteren Bildschirmrand. An lassen, wenn du wissen willst, wann das Mikro tatsächlich zuhört.
- **Bei Windows-Start automatisch starten** — TypeStream startet mit Windows. Empfohlen, sonst musst du das Programm jeden Tag manuell öffnen.

### 5.4 Stil

Diktieren ergibt rohe Sätze ("ähm, also, ich denke, dass…"). TypeStream kann das automatisch in einen Schreibstil umformen.

- **Aktiver Stil** — *Original* (keine Änderung), *Professionell* (formell, "Sehr geehrte Damen und Herren…"), *Locker* (Umgangssprache), oder *Eigener Stil* (siehe unten). Den aktiven Stil kannst du auch oben im Hauptfenster und im Tray-Menü wechseln.
- **Stil-Modus** — wie der Stil angewendet wird:
  - **Whisper-Hint** *(Standard)* — der Stil-Beispieltext wird Whisper als Vorlage mitgegeben. Schnell, kostenlos, aber der Effekt ist subtil.
  - **LLM-Refine** — nach der Transkription geht der Text noch einmal an GPT zum Umformulieren. Klarere Stil-Änderung, kostet aber einen zusätzlichen API-Aufruf pro Aufnahme.
- **Refine-Modell** *(nur bei LLM-Refine sichtbar)* — *gpt-4o-mini* (günstig, schnell) oder *gpt-4o* (beste Qualität).
- **Eigener Stil** — ein Beispieltext im Wunsch-Stil. Schreib hier z. B. einen Absatz so, wie deine Ausgabe klingen soll. Sobald das Feld nicht leer ist, taucht "Eigener Stil" als zusätzliche Option im Stil-Dropdown auf.

### 5.5 Erscheinungsbild

- **Theme** — *System* (folgt dem Windows-Hell/Dunkel-Modus), *Dunkel*, oder *Hell*.

### 5.6 Statistik

- **Engine A / Engine B** — wähle zwei Engines (OpenAI Cloud und Faster-Whisper Lokal), die verglichen werden sollen.
- Darunter zwei **Kacheln** mit der Ø-Latenz der letzten 10 Aufnahmen für jede Engine, plus die Anzahl der Messungen (n = …).
- Ein **Fazit-Satz** unten sagt dir z. B. "OpenAI ist im Mittel 2,3× schneller als Whisper".

Sinnvoll nur, wenn du in 5.1 den **Benchmark-Modus** aktiviert hast — sonst sammelt TypeStream Daten nur für eine der beiden Engines.

---

## 6. Was tun, wenn etwas nicht klappt?

- **Es passiert gar nichts, wenn ich F9 drücke** → Tray-Symbol nicht da? Dann läuft TypeStream nicht. Programm neu starten. Wenn das Symbol da ist, aber F9 keine Reaktion auslöst, vielleicht hat ein anderes Programm (z. B. ein Spiel) die Taste gekapert — versuche in Einstellungen → Hotkeys eine andere Aufnahme-Taste.
- **"Kein API-Key gesetzt"** → Einstellungen → Transkription → API-Key ausfüllen oder auf "Faster-Whisper (Lokal)" wechseln.
- **"Aufnahme zu kurz"** → Du hast die Taste zu schnell losgelassen. Halte sie mindestens so lange wie der "Min. Aufnahme-Dauer"-Wert (Standard 0,4 s).
- **"Auto-Einfügen fehlgeschlagen — Text in Zwischenablage"** → Manche Fenster (Admin-Programme, ältere Spiele) lassen Auto-Tippen nicht zu. Der Text liegt aber in der Zwischenablage — einfach Strg+V drücken, oder den Einfügen-Hotkey (Strg+Alt+V) verwenden.
- **TypeStream lässt sich nicht beenden, wenn ich das Fenster schließe** → Das ist gewollt. Beim Schließen verschwindet nur das Fenster, das Programm läuft im Tray weiter. Zum vollständigen Beenden Rechtsklick auf das Tray-Symbol → "Beenden".

---

## Datenschutz, kurz

- **OpenAI-Modus**: dein Audio geht an OpenAI zur Transkription. Keine permanente Speicherung deinerseits, aber siehe OpenAI-Datenschutzerklärung.
- **Lokal-Modus**: nichts verlässt deinen Rechner. Modell und Verlauf liegen unter `AppData/Roaming/TypeStream`.
- Der **Verlauf** ist nur lokal — keine Cloud-Synchronisation, keine Telemetrie.
