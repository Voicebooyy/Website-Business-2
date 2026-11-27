# Café-Websites von Polywerk

Eine Vorlage, ein Skript, eine Kundendatei: Aus den Daten eines Cafés entsteht die komplette Website.
Die Demo (`index.html` im Hauptordner) wird mit demselben Skript aus der Vorlage erzeugt. Es gibt also nur **eine** Vorlage, die gepflegt wird.

- Demo: https://voicebooyy.github.io/Website-Business-2/

## Ordner

| Was | Wofür |
|---|---|
| `vorlage/` | Die Vorlage (`index.html`, `impressum.html`, `datenschutz.html`, `uebergabe.txt`). **Nur hier ändern**, nie die erzeugten Seiten. |
| `neue-kundenseite.py` | Das Skript, das aus Vorlage + Kundendatei die Seite baut. |
| `kunden-beispiel.json` | Die Daten des Muster-Cafés (daraus entsteht die Demo). |
| `kunden-vorlage.json` | Leere Kundendatei zum Kopieren. |
| `vorschau/` | Vorschauen für Cafés (öffentlich, mit Zufallsendung im Ordnernamen). |
| `ausgabe/` | Fertige Kunden-Seiten und ZIP-Dateien (wird nicht hochgeladen). |

Kundendaten und Fotos der Cafés gehören **nicht** in dieses öffentliche Repo, sondern in das private (`Website-Business`).

## Eine Seite bauen

```bash
python3 neue-kundenseite.py pfad/zum-cafe.json --modus vorschau   # Vorschau zum Zeigen
python3 neue-kundenseite.py pfad/zum-cafe.json --modus fertig     # verkaufsfertige Seite + ZIP
python3 neue-kundenseite.py kunden-beispiel.json --modus demo     # die Demo neu bauen
```

| Modus | Hinweis-Pille + Kontakt-Fenster | „Hier könnte … stehen“ | Links | Google |
|---|---|---|---|---|
| `demo` | ja | ja | abgefangen | unsichtbar |
| `vorschau` | ja | nein | echt | unsichtbar |
| `fertig` | nein | nein | echt | sichtbar |

Die **fertige** Seite hat kein Formular: nur Telefon- und E-Mail-Links. Dadurch gibt es nichts zu betreiben und keinen Dienst, der später aktiviert werden müsste.

## Fotos

Die Originale (JPG/PNG) liegen neben der Kundendatei im Ordner `fotos/` (oder wie unter `bilder.ordner` angegeben). Das Skript macht automatisch:

- dunkle **Ränder von Screenshots abschneiden** (z. B. bei KI-Bildern), es meldet, was es abgeschnitten hat,
- das Titelbild in drei Größen (800 / 1200 / 1440 px) und als Vorschaubild (1200 × 630) speichern,
- die drei Galerie-Fotos auf 4:5 zuschneiden und verkleinern,
- vor zu kleinen Fotos warnen.

Titelbild: möglichst hell, ab 1600 px Breite, unten links ruhig (dort steht die Schrift). **Auf echten Café-Seiten nur echte Fotos des Cafés**, keine KI-Bilder von Speisen.

## Wichtige Felder der Kundendatei

| Feld | Bedeutung |
|---|---|
| `name`, `strasse`, `plz`, `ort`, `telefon`, `email` | Stammdaten, erscheinen überall (Seite, Impressum, Google-Daten). |
| `hero_woerter` | 2 bis 4 Wörter für die große Überschrift („Frühstück. Kuchen. Kaffee.“). |
| `oeffnungszeiten` | Zeilen mit `tage` (Anzeige), `tage_nr` (0 = So … 6 = Sa) und `zeiten` (Format `8:00 – 18:00` oder `Ruhetag`; mit Mittagspause `8:00 – 12:00, 14:00 – 18:00`; nach Mitternacht `17:00 – 1:00`). Das Türschild „Geöffnet/Geschlossen“ richtet sich automatisch danach und rechnet immer mit deutscher Zeit. |
| `schliesstage`, `hinweis` | Feiertage/Urlaub (`JJJJ-MM-TT`); ein Hinweis verschwindet nach seinem Datum (`bis`) von selbst. |
| `karte.kategorien` | Teile der Speisekarte mit Gerichten (`name`, `preis`, `beschreibung`, optional `schild`). `karte.start` bestimmt optional, welcher Reiter zu welcher Uhrzeit zuerst offen ist. |
| `ueber_uns` | `aussage` (ein Satz) und `text`. |
| `bewertungslink` | Link aus dem Google-Unternehmensprofil, leer lassen = Block entfällt. |
| `bewertungen` | **Optional.** Block „Das sagen unsere Gäste“ mit `durchschnitt`, `anzahl` und 1 bis 3 `eintraege` (`name`, `sterne` 1–5, `text`, optional `wann`). Dazu optional `bewertungslink_profil` für „Alle Bewertungen auf Google“. **Bei echten Cafés nur Bewertungen eintragen, die wörtlich im Google-Profil stehen**, nichts erfinden. Eintrag löschen und neu bauen = Bereich samt Menüpunkt restlos weg. |
| `inhaber`, `rechtsform`, `ust_id`, `hoster` | Für Impressum und Datenschutz (Vorlagen, bitte prüfen lassen). |
| `webadresse` | Endgültige Adresse der Seite, nötig für die Bildvorschau beim Teilen. |
| `farben` | Optional: eigene Farben (`bg`, `paper`, `soft`, `text`, `muted`, `line`, `akzent`, `akzent_hell`). Das Skript prüft die Lesbarkeit. |
| `events` | **Optional.** Termine mit `titel`, `datum` (`JJJJ-MM-TT`) oder `wochentag` (0 = So … 6 = Sa, wiederkehrend), `zeit`, `text`, `schild`. Vergangene Termine verschwinden von selbst, sind alle weg, auch der Bereich samt Menüpunkt. **Eintrag `events` löschen und neu bauen = Bereich restlos weg** (Seite danach identisch zu vorher). |
| `polywerk_hinweis` | `true` = „Website von Polywerk“ im Fußbereich. |

Das Skript bricht bei fehlenden Pflichtfeldern mit einer verständlichen Meldung ab und **warnt**, wenn noch Beispielwerte (`Muster`, `[…]`, `.example` …) in der Datei stehen.

## Übergabe an den Kunden

`--modus fertig` erzeugt `ausgabe/<name>/` und `ausgabe/<name>.zip` (Dateien direkt im Zip-Stamm) mit einer `LIESMICH-UEBERGABE.txt`, die jeder Webspace-Support ohne Rückfrage umsetzen kann. Danach hat der Kunde alles, und es gibt nichts weiter zu betreiben.

## Test

`node tests/tuerschild.test.js` prüft Türschild, Urlaubshinweis und Events (Mittagspause, nach Mitternacht, Feiertage, drei Zeitzonen). Braucht Playwright. Das Skript selbst hat einen eingebauten Selbsttest, der bei jedem Bauen läuft.
