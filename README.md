# Café-Demo von Polywerk

Muster-Website für Cafés und ein Werkzeug, das daraus persönliche Vorschauen macht.

## Links (sobald GitHub Pages eingeschaltet ist)

- Demo: https://voicebooyy.github.io/Website-Business-2/
- Mit dem Namen eines Cafés: https://voicebooyy.github.io/Website-Business-2/?cafe=Colonial%20Café&ort=Werder
  (ersetzt Name und Ort im sichtbaren Text, Leerzeichen als `%20`)

## Persönliche Vorschau erstellen

```bash
python3 neue-vorschau.py
```

Das Skript fragt Name, Ort, Adresse, Telefon und E-Mail ab und legt `vorschau/<name>-<zufall>/` an (die Zufallsendung macht die Adresse nicht erratbar; ein erneuter Aufruf für dasselbe Café nutzt den vorhandenen Ordner).
Öffnungszeiten, Speisekarte und Fotos danach in `vorschau/<name>/index.html` anpassen.

## Aus der Demo eine echte Kunden-Website machen

1. Alles anpassen, was mit `ÄNDERN` markiert ist.
2. Die DEMO-Teile löschen: den CSS-Block „DEMO“, `<aside class="demo">`, `<div class="toast">` und das DEMO-Script.
3. Die Zeile `<meta name="robots" content="noindex, nofollow">` löschen, sonst findet Google die Seite nicht.
4. Eigene Fotos in den Ordner legen und verlinken (statt Unsplash).
5. Impressum und Datenschutz mit den echten Angaben füllen (z. B. mit einem Datenschutz-Generator).
