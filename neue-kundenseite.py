#!/usr/bin/env python3
"""Baut aus einer Kundendatei (JSON) eine komplette Café-Website.

Aufruf (im Ordner dieser Datei):

  python3 neue-kundenseite.py kunden-beispiel.json --modus demo
      Baut die Demo neu (schreibt index.html, impressum.html, datenschutz.html in diesen Ordner).

  python3 neue-kundenseite.py pfad/zum-cafe.json --modus vorschau
      Baut eine Vorschau für das Café nach vorschau/<name>-<zufall>/ (mit Hinweis-Pille, nicht bei Google).

  python3 neue-kundenseite.py pfad/zum-cafe.json --modus fertig
      Baut die verkaufsfertige Seite nach ausgabe/<name>/ plus <name>.zip (ohne Demo-Teile, bei Google auffindbar).

Fotos: Liegen die Originale neben der Kundendatei im Ordner „fotos“ (oder wie unter bilder.ordner angegeben),
werden sie automatisch zugeschnitten, verkleinert und als WebP gespeichert.
"""
import argparse
import html
import json
import re
import secrets
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import quote, quote_plus

HIER = Path(__file__).resolve().parent
VORLAGE = HIER / "vorlage"
DEMO_URL = "https://voicebooyy.github.io/Website-Business-2/"
STANDARD_FARBEN = {
    "bg": "#f6f1e9", "paper": "#fbf7f1", "soft": "#ede4d6", "text": "#2a1d15",
    "muted": "#6b5c50", "line": "#e2d7c9", "akzent": "#4d6647", "akzent_hell": "#e1e6d8",
}
SEITEN = ["index.html", "impressum.html", "datenschutz.html"]


# ---------------------------------------------------------------- kleine Helfer
def slug(text):
    """„Café & Bistro Größe“ → „cafe-bistro-groesse“ (für Ordnernamen und Reiter-IDs)."""
    text = text.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("é", "e"), ("è", "e"), ("à", "a")):
        text = text.replace(alt, neu)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "cafe"


def tel_link(nummer):
    """„03327 / 123 456“ → „+493327123456“ (für den Anruf-Knopf)."""
    ziffern = re.sub(r"\D", "", nummer)
    return "+49" + ziffern[1:] if ziffern.startswith("0") else "+" + ziffern


def t(s):
    """Text für das HTML (zwischen Tags)."""
    return html.escape(str(s), quote=False)


def a(s):
    """Text für Attribute (zwischen Anführungszeichen)."""
    return html.escape(str(s), quote=True)


def luminanz(hexfarbe):
    r, g, b = (int(hexfarbe.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def kontrast(f1, f2):
    hell, dunkel = sorted((luminanz(f1), luminanz(f2)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


def filtere(text, behalte):
    """Entfernt die Blöcke <!--[NAME]-->…<!--[/NAME]--> (bzw. /*[NAME]*/…) für Marker, die NICHT in `behalte` sind;
    bei behaltenen Markern werden nur die Markierungszeilen entfernt."""
    for name in ("PILLE", "DEMO", "EVENTS", "BEWERTUNGEN"):
        block = re.compile(
            r"^[ \t]*(?:<!--|/\*)\[%s\](?:-->|\*/)[ \t]*\n(.*?)^[ \t]*(?:<!--|/\*)\[/%s\](?:-->|\*/)[ \t]*\n" % (name, name),
            re.S | re.M)
        text = block.sub((lambda m: m.group(1)) if name in behalte else "", text)
    return text


def fuelle(text, werte):
    """Ersetzt {{schluessel}} durch Werte. Ein unbekannter Schlüssel ist ein Fehler (kein stilles Weglassen)."""
    def ersatz(m):
        if m.group(1) not in werte:
            raise SystemExit(f"Fehler in der Vorlage: Platzhalter {{{{{m.group(1)}}}}} hat keinen Wert.")
        return werte[m.group(1)]
    return re.sub(r"\{\{(\w+)\}\}", ersatz, text)


# ---------------------------------------------------------------- Fotos
def _kante(werte):
    """`werte` = mittlere Helligkeit der Linien von außen nach innen. Sucht in den äußeren 15 % einen harten Sprung von dunkel
    nach hell (Rand eines Screenshots) und gibt zurück, wie viele Linien Rand abzuschneiden sind (0 = kein Rand)."""
    for i in range(1, max(2, int(len(werte) * 0.15))):
        if werte[i] - werte[i - 1] >= 45 and max(werte[:i]) < 80:
            return i + 3  # 3 Pixel Sicherheitsabstand nach innen
    return 0


def rand_entfernen(im):
    """Schneidet dunkle Ränder ab, wie sie bei Screenshots von KI-Bildern entstehen. Gibt (Bild, Hinweis oder None) zurück."""
    from PIL import Image
    grau = im.convert("L")
    w, h = im.size
    zeilen = list(grau.resize((1, h), Image.BOX).tobytes())
    spalten = list(grau.resize((w, 1), Image.BOX).tobytes())
    oben, unten = _kante(zeilen), _kante(zeilen[::-1])
    links, rechts = _kante(spalten), _kante(spalten[::-1])
    if not (oben or unten or links or rechts):
        return im, None
    return (im.crop((links, oben, w - rechts, h - unten)),
            f"Dunkler Rand erkannt und abgeschnitten (oben {oben}, unten {unten}, links {links}, rechts {rechts} px).")


def lade_foto(pfad, rand=True):
    """Öffnet ein Foto (richtig gedreht) und schneidet auf Wunsch dunkle Screenshot-Ränder ab. Gibt (Bild, Hinweis) zurück."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(pfad)).convert("RGB")
    return rand_entfernen(im) if rand else (im, None)


def mittig_zuschneiden(im, verhaeltnis):
    """Schneidet mittig auf Breite:Höhe = verhaeltnis zu."""
    w, h = im.size
    if w / h > verhaeltnis:
        neu = round(h * verhaeltnis); links = (w - neu) // 2
        return im.crop((links, 0, links + neu, h))
    neu = round(w / verhaeltnis); oben = (h - neu) // 2
    return im.crop((0, oben, w, oben + neu))


def verarbeite_fotos(c, json_ordner, ziel, meldungen):
    """Gibt zurück: {'hero': [(breite, höhe), ...], 'galerie': [(breite, höhe), ...], 'vorschau': bool}"""
    from PIL import Image
    b = c.get("bilder", {})
    info = {"hero": [], "galerie": [], "vorschau": False}
    ziel.mkdir(parents=True, exist_ok=True)

    if b.get("verarbeitet"):  # Bilder liegen schon fertig im Ordner „bilder“ (so ist die Demo aufgebaut)
        quelle = HIER / "bilder"
        for datei in sorted(quelle.glob("titelbild-*.webp"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1))):
            info["hero"].append(Image.open(datei).size)
            if quelle != ziel:
                shutil.copy2(datei, ziel / datei.name)
        for i in range(1, 4):
            d = quelle / f"galerie-{i}.webp"
            if d.exists():
                info["galerie"].append(Image.open(d).size)
                if quelle != ziel:
                    shutil.copy2(d, ziel / d.name)
        v = quelle / "vorschau.jpg"
        info["vorschau"] = v.exists()
        if v.exists() and quelle != ziel:
            shutil.copy2(v, ziel / v.name)
        return info

    ordner = json_ordner / b.get("ordner", "fotos")
    titel = b.get("titelbild", {})
    if not titel.get("datei"):
        meldungen.append("Kein Titelbild angegeben (bilder.titelbild.datei) – die Seite hat dann kein großes Foto.")
    else:
        quelle = ordner / titel["datei"]
        if not quelle.exists():
            raise SystemExit(f"Titelbild nicht gefunden: {quelle}")
        im, hinweis = lade_foto(quelle, b.get("rand_entfernen", True))
        if hinweis:
            meldungen.append(f"{titel['datei']}: {hinweis}")
        if im.width < 1200:
            meldungen.append(f"Titelbild ist nur {im.width} px breit (besser ab 1600 px) – es kann unscharf wirken.")
        breiten = sorted({w for w in (800, 1200, 1440) if w < im.width} | {min(im.width, 1440)})
        for w in breiten:
            h = round(im.height * w / im.width)
            im.resize((w, h), Image.LANCZOS).save(ziel / f"titelbild-{w}.webp", quality=82, method=6)
            info["hero"].append((w, h))
        if im.width >= 1200:  # Vorschaubild für WhatsApp/E-Mail, 1200×630
            r = mittig_zuschneiden(im, 1200 / 630).resize((1200, 630), Image.LANCZOS)
            r.save(ziel / "vorschau.jpg", quality=85, optimize=True, progressive=True)
            info["vorschau"] = True
    for i, g in enumerate(b.get("galerie", [])[:3], start=1):
        quelle = ordner / g["datei"]
        if not quelle.exists():
            raise SystemExit(f"Galerie-Foto nicht gefunden: {quelle}")
        im, hinweis = lade_foto(quelle, b.get("rand_entfernen", True))
        if hinweis:
            meldungen.append(f"{g['datei']}: {hinweis}")
        im = mittig_zuschneiden(im, 4 / 5)
        if im.width < 600:
            meldungen.append(f"Galerie-Foto {i} ist nur {im.width} px breit (besser ab 800 px) – es kann unscharf wirken.")
        w = min(im.width, 640)
        h = round(im.height * w / im.width)
        im.resize((w, h), Image.LANCZOS).save(ziel / f"galerie-{i}.webp", quality=86, method=6)
        info["galerie"].append((w, h))
    return info


# ---------------------------------------------------------------- Bausteine der Seite
def baue_hero_bild(c, info):
    hero = info["hero"]
    if not hero:
        return ""
    alt = a(c["bilder"].get("titelbild", {}).get("alt", f"Innenraum des {c['name']}"))
    src_w = max([w for w, _ in hero if w <= 1200] or [hero[0][0]])
    srcset = ", ".join(f"bilder/titelbild-{w}.webp {w}w" for w, _ in hero)
    w, h = hero[-1]
    return (f'<img class="hero-img" src="bilder/titelbild-{src_w}.webp"\n'
            f'    srcset="{srcset}"\n'
            f'    sizes="(min-width: 1000px) calc(100vw - 240px), 100vw" width="{w}" height="{h}"\n'
            f'    alt="{alt}" fetchpriority="high">')


def baue_galerie(c, info):
    bilder = c.get("bilder", {}).get("galerie", [])
    figuren = ""
    for i, ((w, h), g) in enumerate(zip(info["galerie"], bilder), start=1):
        figuren += (f'  <figure><div class="frame"><img src="bilder/galerie-{i}.webp" width="{w}" height="{h}" '
                    f'alt="{a(g.get("alt", ""))}" loading="lazy"></div><figcaption>{t(g.get("unterschrift", ""))}</figcaption></figure>\n')
    if not figuren:
        return ""
    return ('<section class="gallery-sec"><div class="wrap gallery" role="region" aria-label="Bilder aus dem Café" tabindex="0">\n'
            + figuren + '</div></section>\n')


def baue_karte(c):
    kats = c["karte"]["kategorien"]
    ids = [slug(k["titel"]) for k in kats]
    if len(set(ids)) != len(ids):
        raise SystemExit("Zwei Teile der Speisekarte haben (fast) denselben Namen – bitte unterschiedlich benennen.")
    tabs = '  <div class="tabs" role="tablist" aria-label="Teile der Speisekarte">\n'
    panels = ""
    for k, i in zip(kats, ids):
        tabs += f'    <button type="button" role="tab" id="t-{i}" aria-controls="p-{i}">{t(k["titel"])}</button>\n'
        zus = f' <small>{t(k["zusatz"])}</small>' if k.get("zusatz") else ""
        panels += (f'  <div class="panel" id="p-{i}" role="tabpanel" aria-labelledby="t-{i}">\n'
                   f'    <h3 class="panel-title">{t(k["titel"])}{zus}</h3>\n    <ul class="dishes">\n')
        for g in k["gerichte"]:
            schild = f'<i class="tag">{t(g["schild"])}</i>' if g.get("schild") else ""
            beschr = f'<small>{t(g["beschreibung"])}</small>' if g.get("beschreibung") else ""
            panels += f'      <li><span>{t(g["name"])}{schild}</span><b>{t(g["preis"])}</b>{beschr}</li>\n'
        panels += "    </ul>\n  </div>\n"
    tabs += "  </div>\n"
    start = c["karte"].get("start")
    if start:
        for wer in ("vorher", "danach"):
            if slug(start[wer]) not in ids:
                raise SystemExit(f"karte.start.{wer}: „{start[wer]}“ ist kein Teil der Speisekarte.")
        js = f"now.getHours() < {int(start['bis_uhr'])} ? 't-{slug(start['vorher'])}' : 't-{slug(start['danach'])}'"
    else:
        js = f"'t-{ids[0]}'"
    return tabs + '  <div class="panels">\n' + panels + "  </div>\n", js


def baue_oeffnungszeiten(c):
    zeilen = ""
    for z in c["oeffnungszeiten"]:
        zeilen += f'        <tr data-days="{" ".join(str(n) for n in z["tage_nr"])}"><td>{t(z["tage"])}</td><td>{t(z["zeiten"])}</td></tr>\n'
    return zeilen


WOCHENTAGE = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]  # 0 = So … 6 = Sa
MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def baue_events(c):
    """Optionaler Events-Bereich. Ohne Eintrag `events` in der Kundendatei gibt es ihn (samt Menüpunkt, Gestaltung, Skript) nicht."""
    ev = c.get("events")
    if not ev:
        return ""
    liste = ""
    for e in ev["eintraege"]:
        zeit = f", {t(e['zeit'])} Uhr" if e.get("zeit") else ""
        schild = f'\n      <i class="tag">{t(e["schild"])}</i>' if e.get("schild") else ""
        text = f'<p class="ev-text">{t(e["text"])}</p>' if e.get("text") else ""
        if e.get("datum"):
            d = date.fromisoformat(e["datum"])
            wochentag = WOCHENTAGE[(d.weekday() + 1) % 7]
            kopf = f'    <li data-date="{e["datum"]}">\n      <time class="ev-date" datetime="{e["datum"]}"><b>{d.day:02d}</b><span>{MONATE[d.month - 1]}</span></time>'
            wann = f"{wochentag}{zeit}"
        else:
            wochentag = WOCHENTAGE[e["wochentag"]]
            kopf = f'    <li>\n      <span class="ev-date"><b>{wochentag[:2]}</b><span>jeden</span></span>'
            wann = f"Jeden {wochentag}{zeit}"
        liste += f'{kopf}\n      <div><h3>{t(e["titel"])}</h3><p class="ev-when">{wann}</p>{text}</div>{schild}\n    </li>\n'
    return (f'<section id="events"><div class="wrap">\n  <h2 class="head">{t(ev.get("titel", "Das ist bei uns los"))}</h2>\n'
            f'  <ul class="events">\n{liste}  </ul>\n</div></section>\n')


def baue_bewertungen(c):
    """Optionaler Bewertungs-Bereich (Durchschnitt + bis zu 3 Karten). Ohne Eintrag `bewertungen` entfällt er samt Menüpunkt.
    Bei echten Cafés nur Bewertungen eintragen, die wörtlich im Google-Profil stehen."""
    b = c.get("bewertungen")
    if not b:
        return ""
    def sterne(n):
        n = int(round(float(n)))
        return f'<div class="stars" role="img" aria-label="{n} von 5 Sternen">' + "★" * n + '<span class="off">' + "★" * (5 - n) + "</span></div>"
    karten = ""
    for e in b["eintraege"]:
        wann = f"<span>{t(e['wann'])}</span>" if e.get("wann") else ""
        karten += (f'    <figure>\n      {sterne(e["sterne"])}\n      <blockquote>„{t(e["text"])}“</blockquote>\n'
                   f'      <figcaption>{t(e["name"])} {wann}</figcaption>\n    </figure>\n')
    note = str(b["durchschnitt"]).replace(".", ",")
    link = (f'  <a class="reviews-more" href="{a(c["bewertungslink_profil"])}" target="_blank" rel="noopener">Alle Bewertungen auf Google →</a>\n'
            if c.get("bewertungslink_profil") else "")
    return (f'<section id="bewertungen"><div class="wrap">\n  <h2 class="head">{t(b.get("titel", "Das sagen unsere Gäste"))}</h2>\n'
            f'  <div class="rating"><span class="rating-num">{t(note)}</span><div>{sterne(float(b["durchschnitt"]))}'
            f'<p>{t(str(b["anzahl"]))} Bewertungen auf Google</p></div></div>\n'
            f'  <div class="reviews">\n{karten}  </div>\n{link}</div></section>\n')


def baue_jsonld(c, telefon_link):
    d = {"@context": "https://schema.org", "@type": "CafeOrCoffeeShop", "name": c["name"], "telephone": telefon_link, "email": c["email"],
         "address": {"@type": "PostalAddress", "streetAddress": c["strasse"], "postalCode": c["plz"], "addressLocality": c["ort"], "addressCountry": "DE"},
         "servesCuisine": ", ".join(c.get("schlagworte", c.get("hero_woerter", []))), "openingHoursSpecification": []}
    return json.dumps(d, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------- Prüfungen
PFLICHT = ["name", "strasse", "plz", "ort", "telefon", "email", "oeffnungszeiten", "karte", "ueber_uns", "hero_woerter"]


def pruefe_daten(c, modus):
    fehlt = [k for k in PFLICHT if not c.get(k)]
    if fehlt:
        raise SystemExit("In der Kundendatei fehlt: " + ", ".join(fehlt))
    for z in c["oeffnungszeiten"]:
        if not re.search(r"\d{1,2}:\d{2}\D+\d{1,2}:\d{2}", z["zeiten"]) and not z["zeiten"].strip():
            raise SystemExit(f"Öffnungszeit „{z['tage']}“ ist leer.")
        if not all(isinstance(n, int) and 0 <= n <= 6 for n in z["tage_nr"]):
            raise SystemExit(f"tage_nr bei „{z['tage']}“ muss aus Zahlen 0 (So) bis 6 (Sa) bestehen.")
    for e in (c.get("events") or {}).get("eintraege", []):
        if not e.get("titel"):
            raise SystemExit("Ein Event hat keinen Titel.")
        if bool(e.get("datum")) == (e.get("wochentag") is not None):
            raise SystemExit(f"Event „{e['titel']}“: entweder `datum` (JJJJ-MM-TT) ODER `wochentag` (0 = So … 6 = Sa) angeben.")
        try:
            if e.get("datum"):
                date.fromisoformat(e["datum"])
            elif not 0 <= e["wochentag"] <= 6:
                raise ValueError
        except ValueError:
            raise SystemExit(f"Event „{e['titel']}“: ungültiges Datum oder ungültiger Wochentag.")
    b = c.get("bewertungen")
    if b:
        if not b.get("eintraege") or len(b["eintraege"]) > 3:
            raise SystemExit("bewertungen.eintraege: 1 bis 3 Bewertungen angeben.")
        for e in b["eintraege"]:
            if not all(e.get(k) for k in ("name", "text", "sterne")) or not 1 <= float(e["sterne"]) <= 5:
                raise SystemExit("Jede Bewertung braucht name, text und sterne (1 bis 5).")
        if not b.get("durchschnitt") or not b.get("anzahl"):
            raise SystemExit("bewertungen: durchschnitt und anzahl fehlen.")
    if len(c["hero_woerter"]) > 4:
        raise SystemExit("hero_woerter: höchstens 4 Wörter – der erste Eindruck soll kurz bleiben.")


def sammle_warnungen(c, modus):
    w = []
    if modus != "demo":
        verdacht = re.compile(r"Muster|DEIN-CODE|\.example|\[.*\]|\b12345\b|0123 ?/ ?45678|Lorem", re.I)
        for pfad, wert in durchlaufe(c):
            if verdacht.search(str(wert)) and pfad not in ("_hinweis",):
                w.append(f"Sieht nach Beispielwert aus: {pfad} = „{wert}“")
    if modus != "demo" and c.get("bewertungen"):
        w.append("Bewertungen: nur echte Texte aus dem Google-Profil des Cafés, wörtlich übernommen. Nichts erfinden oder umschreiben.")
    if modus == "fertig":
        if not c.get("inhaber"):
            w.append("Für das Impressum fehlt „inhaber“ (z. B. „Inhaber: Max Mustermann“).")
        if not c.get("hoster"):
            w.append("„hoster“ fehlt – in der Datenschutzerklärung steht dann ein Platzhalter.")
        if not c.get("webadresse"):
            w.append("„webadresse“ fehlt – ohne sie gibt es keine Bildvorschau beim Teilen (WhatsApp, E-Mail).")
        w.append("Impressum und Datenschutz sind Vorlagen aus den Kundendaten: bitte prüfen lassen (z. B. mit einem Generator).")
    f = {**STANDARD_FARBEN, **c.get("farben", {})}
    for name, vordergrund, grund, minimum in [
        ("Text auf Hintergrund", f["text"], f["bg"], 7), ("Grauer Text auf Hintergrund", f["muted"], f["bg"], 4.5),
        ("Grauer Text auf Abschnitt", f["muted"], f["soft"], 4.5), ("Akzent auf Hintergrund", f["akzent"], f["bg"], 4.5),
        ("Akzent auf Abschnitt", f["akzent"], f["soft"], 4.5), ("Akzent auf Schild", f["akzent"], f["akzent_hell"], 4.5),
        ("Knopf (Hintergrund auf Text)", f["bg"], f["text"], 4.5)]:
        if kontrast(vordergrund, grund) < minimum:
            w.append(f"Farbkontrast zu schwach: {name} {kontrast(vordergrund, grund):.1f}:1 (nötig {minimum}:1)")
    return w


def durchlaufe(obj, pfad=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from durchlaufe(v, f"{pfad}.{k}" if pfad else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from durchlaufe(v, f"{pfad}[{i}]")
    elif isinstance(obj, str):
        yield pfad, obj


# ---------------------------------------------------------------- Bauen
def baue(c, modus, json_ordner, ausgabe):
    behalte = {"demo": {"PILLE", "DEMO"}, "vorschau": {"PILLE"}, "fertig": set()}[modus] | ({"EVENTS"} if c.get("events") else set()) | ({"BEWERTUNGEN"} if c.get("bewertungen") else set())
    meldungen = []
    info = verarbeite_fotos(c, json_ordner, ausgabe / "bilder" if modus != "demo" else HIER / "bilder", meldungen)

    farben = {**STANDARD_FARBEN, **c.get("farben", {})}
    karte_html, karte_js = baue_karte(c)
    name = c["name"]
    tl = tel_link(c["telefon"])
    maps = "https://maps.google.com/?q=" + quote_plus(f'{c["strasse"]} {c["ort"]}')
    web = c.get("webadresse", "")
    if modus == "vorschau":
        web = DEMO_URL + f"vorschau/{ausgabe.name}/"
    if web and not web.endswith("/"):
        web += "/"
    zusatz = c.get("titel_zusatz") or " & ".join(c["hero_woerter"][:2])
    beschr = c.get("beschreibung") or f"{name} in {c['ort']}: {', '.join(c['hero_woerter'])}."
    hinweis = c.get("hinweis")
    hinweis_html = ""
    if hinweis:
        bis = f' data-until="{a(hinweis["bis"])}"' if hinweis.get("bis") else ""
        hinweis_html = (f'      <!-- Kurzer Hinweis (Urlaub, Aktion): verschwindet nach dem Datum in data-until von selbst -->\n'
                        f'      <p class="notice"{bis}>{t(hinweis["text"])}</p>\n')
    bewertung = c.get("bewertungslink", "")
    bewertung_html = (f'      <p><a href="{a(bewertung)}" target="_blank" rel="noopener">Hat’s geschmeckt? Bewerte uns bei Google</a></p>\n'
                      if bewertung else "")
    og_bild = f'<meta property="og:image" content="{a(web)}bilder/vorschau.jpg">\n' if web and info["vorschau"] else ""
    noindex = modus in ("demo", "vorschau")
    hoster = c.get("hoster")
    if modus == "fertig":
        hoster_satz = f"Diese Website wird bei {t(hoster)} gehostet." if hoster else "Hosting-Anbieter: [bitte eintragen]"
    else:
        hoster_satz = "Diese Musterseite liegt bei GitHub Pages (GitHub Inc., USA)."
    rechtsform = f" {c['rechtsform']}" if c.get("rechtsform") else ""
    ust = (f'\n  <h2>Umsatzsteuer-ID</h2>\n  <p>Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: {t(c["ust_id"])}</p>\n'
           if c.get("ust_id") else "")
    buchstabe = quote(name[0].upper(), safe="")

    werte = {
        "seitentitel": t(f"{name} – {zusatz} in {c['ort']}"), "beschreibung": a(beschr), "og_beschreibung": a(c.get("og_beschreibung", beschr)),
        "farbe_bg": farben["bg"], "farbe_paper": farben["paper"], "farbe_soft": farben["soft"], "farbe_text": farben["text"],
        "farbe_muted": farben["muted"], "farbe_line": farben["line"], "farbe_akzent": farben["akzent"], "farbe_akzent_hell": farben["akzent_hell"],
        "robots_meta": ('<!-- Demo/Vorschau nicht bei Google zeigen -->\n<meta name="robots" content="noindex, nofollow">\n' if noindex else ""),
        "robots_meta_einfach": ('<meta name="robots" content="noindex">' if noindex else ""),
        "og_bild_meta": og_bild, "favicon_buchstabe": buchstabe,
        "favicon_dunkel": "%23" + farben["text"].lstrip("#"), "favicon_hell": "%23" + farben["bg"].lstrip("#"), "favicon_hell_roh": "%23" + farben["bg"].lstrip("#"),
        "fonts": "../../fonts/" if modus == "vorschau" else "fonts/", "jsonld": baue_jsonld(c, tl),
        "name": t(name), "name_rechtsform": t(name + rechtsform), "inhaber": t(c.get("inhaber", "[Inhaber eintragen]")),
        "strasse": t(c["strasse"]), "plz": t(c["plz"]), "ort": t(c["ort"]), "telefon": t(c["telefon"]), "telefon_link": tl, "email": t(c["email"]),
        "maps_url": maps, "hero_bild": baue_hero_bild(c, info), "hero_h1": "<br>".join(t(w) + "." for w in c["hero_woerter"]),
        "karte_titel": t(c["karte"].get("titel", "Unsere Lieblinge")), "menu_html": karte_html, "karte_start_js": karte_js,
        "galerie_sektion": baue_galerie(c, info), "events_sektion": baue_events(c), "bewertungen_sektion": baue_bewertungen(c), "ueber_aussage": t(c["ueber_uns"]["aussage"]), "ueber_text": t(c["ueber_uns"]["text"]),
        "oeffnungszeilen": baue_oeffnungszeiten(c), "schliesstage": " ".join(c.get("schliesstage", [])),
        "hinweis_block": hinweis_html, "bewertung_block": bewertung_html,
        "kontakt_text": t(c.get("kontakt_text", "Fragen, Feiern oder Kuchen vorbestellen? Ruf kurz an oder schreib uns.")),
        "polywerk_link": ('<a href="mailto:polywerk.business@gmail.com">Website von Polywerk</a>' if c.get("polywerk_hinweis", True) else ""),
        "ust_block": ust, "hoster_satz": hoster_satz,
    }
    ausgabe.mkdir(parents=True, exist_ok=True)
    for seite in SEITEN:
        quelle = (VORLAGE / seite).read_text(encoding="utf-8")
        (ausgabe / seite).write_text(fuelle(filtere(quelle, behalte), werte), encoding="utf-8")
    if modus != "demo" and not (ausgabe / "fonts").exists() and modus == "fertig":
        shutil.copytree(HIER / "fonts", ausgabe / "fonts")
    return meldungen


def schreibe_uebergabe(c, ausgabe):
    text = (VORLAGE / "uebergabe.txt").read_text(encoding="utf-8")
    (ausgabe / "LIESMICH-UEBERGABE.txt").write_text(text.replace("{{name}}", c["name"]), encoding="utf-8")
    zip_pfad = ausgabe.parent / f"{ausgabe.name}.zip"
    with zipfile.ZipFile(zip_pfad, "w", zipfile.ZIP_DEFLATED) as z:  # Dateien liegen direkt im Zip-Stamm (kein Extra-Ordner)
        for datei in sorted(ausgabe.rglob("*")):
            if datei.is_file():
                z.write(datei, datei.relative_to(ausgabe))
    return zip_pfad


def selbsttest():
    assert slug("Café & Bistro Größe!") == "cafe-bistro-groesse"
    assert tel_link("03327 / 123 456") == "+493327123456"
    assert kontrast("#000000", "#ffffff") > 20 and kontrast("#777777", "#777777") == 1
    gefiltert = filtere("a\n<!--[DEMO]-->\nb\n<!--[/DEMO]-->\n/*[PILLE]*/\nc\n/*[/PILLE]*/\nd\n", {"PILLE"})
    assert gefiltert == "a\nc\nd\n", repr(gefiltert)
    assert fuelle("x {{a}} y", {"a": "1"}) == "x 1 y"
    assert filtere("a\n<!--[EVENTS]-->\nb\n<!--[/EVENTS]-->\nc\n", set()) == "a\nc\n"
    ev = baue_events({"events": {"eintraege": [{"datum": "2026-12-06", "zeit": "10:00 – 14:00", "titel": "X"}, {"wochentag": 4, "titel": "Y"}]}})
    rv = baue_bewertungen({"bewertungen": {"durchschnitt": 4.8, "anzahl": 214, "eintraege": [{"name": "A. B.", "sterne": 4, "text": "Gut"}]}})
    assert "4,8" in rv and "214 Bewertungen" in rv and "„Gut“" in rv and 'aria-label="4 von 5 Sternen"' in rv
    assert filtere("a\n<!--[BEWERTUNGEN]-->\nb\n<!--[/BEWERTUNGEN]-->\nc\n", set()) == "a\nc\n"
    assert "Sonntag, 10:00 – 14:00 Uhr" in ev and "Jeden Donnerstag" in ev and "<b>06</b><span>Dez</span>" in ev and "<b>Do</b>" in ev


def main():
    selbsttest()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("datei", help="Kundendatei (JSON)")
    p.add_argument("--modus", choices=["demo", "vorschau", "fertig"], required=True)
    args = p.parse_args()
    pfad = Path(args.datei).resolve()
    c = json.loads(pfad.read_text(encoding="utf-8"))
    pruefe_daten(c, args.modus)
    if args.modus == "demo":
        ausgabe = HIER
    elif args.modus == "vorschau":
        vorhanden = [x.name for x in (HIER / "vorschau").iterdir()] if (HIER / "vorschau").is_dir() else []
        passend = [x for x in vorhanden if re.fullmatch(re.escape(slug(c["name"])) + "-[0-9a-f]{6}", x)]
        ausgabe = HIER / "vorschau" / (passend[0] if passend else f"{slug(c['name'])}-{secrets.token_hex(3)}")
    else:
        ausgabe = HIER / "ausgabe" / slug(c["name"])
        if ausgabe.exists():
            shutil.rmtree(ausgabe)
    meldungen = baue(c, args.modus, pfad.parent, ausgabe) + sammle_warnungen(c, args.modus)
    print(f"Fertig ({args.modus}): {ausgabe.relative_to(HIER) if ausgabe != HIER else '.'}")
    if args.modus == "vorschau":
        print("Link, sobald hochgeladen: " + DEMO_URL + f"vorschau/{ausgabe.name}/")
    if args.modus == "fertig":
        print("ZIP: " + str(schreibe_uebergabe(c, ausgabe).relative_to(HIER)))
    for m in meldungen:
        print("  ACHTUNG: " + m)


if __name__ == "__main__":
    main()
