#!/usr/bin/env python3
"""Erstellt aus der Muster-Website eine persönliche Vorschau für ein Café.

Aufruf (im Ordner dieser Datei):   python3 neue-vorschau.py
Das Skript fragt Name, Ort, Adresse usw. ab und legt den Ordner vorschau/<name>/ an.
Öffnungszeiten, Speisekarte und Fotos danach bei Bedarf in vorschau/<name>/index.html anpassen
(die Stellen sind mit „ÄNDERN“ markiert).
"""
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote, quote_plus

HIER = Path(__file__).resolve().parent
SEITEN = ["index.html", "impressum.html", "datenschutz.html"]
LINK = "https://voicebooyy.github.io/Website-Business-2/vorschau/{}/"


def slug(text):
    """„Café & Bistro Größe“ → „cafe-bistro-groesse“ (für Ordnername und Link)."""
    text = text.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("é", "e"), ("è", "e"), ("à", "a")):
        text = text.replace(alt, neu)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def tel_link(nummer):
    """„03327 / 123 456“ → „+493327123456“ (für den Anruf-Knopf)."""
    ziffern = re.sub(r"\D", "", nummer)
    return "+49" + ziffern[1:] if ziffern.startswith("0") else "+" + ziffern


def ersetze(text, paare):
    """Alle Paare in EINEM Durchgang ersetzen, damit ein neuer Wert nicht nochmal ersetzt wird
    (z. B. eine neue Telefonnummer, die zufällig „12345“ enthält). Genauere Muster stehen vorne."""
    tabelle = dict(paare)
    return re.sub("|".join(re.escape(alt) for alt, _ in paare), lambda m: tabelle[m.group(0)], text)


assert slug("Café & Bistro Größe!") == "cafe-bistro-groesse"
assert tel_link("03327 / 123 456") == "+493327123456"
assert ersetze("+4912345678 · 12345", [("+4912345678", "+49331123456"), ("12345", "14542")]) == "+49331123456 · 14542"


def frage(text, vorschlag=""):
    antwort = input(text + (f" [{vorschlag}]" if vorschlag else "") + ": ").strip()
    return antwort or vorschlag


def ersetzungen(d):
    e = html.escape
    # genauere Muster zuerst: die Telefonnummer enthält „12345“, der Karten-Link enthält „Musterstadt“
    liste = [
        ("+4912345678", d["tel_link"]),
        ("0123 / 45678", e(d["tel"])),
        ("Lindenstraße+12+Musterstadt", quote_plus(f'{d["strasse"]} {d["ort"]}')),
        ("hallo@cafe-lindenblatt.de", e(d["email"])),
        ("Lindenstraße 12", e(d["strasse"])),
        ("12345", e(d["plz"])),
        ("Café Lindenblatt GbR", e(d["name"])),  # Rechtsform kennen wir nicht – im Impressum nur den Namen
        ("Café Lindenblatt", e(d["name"])),
        ("Musterstadt", e(d["ort"])),
        ("%3EL%3C/text", "%3E" + quote(d["name"][:1].upper()) + "%3C/text"),  # Buchstabe im Browser-Tab
        ('url("fonts/', 'url("../../fonts/'),  # die Vorschau liegt zwei Ordner tiefer
        ('href="fonts/', 'href="../../fonts/'),
    ]
    if d["inhaber"]:
        liste += [("Anna Muster und Jonas Muster", e(d["inhaber"])), ("Anna & Jonas", e(d["inhaber"]))]
    return liste


def main():
    print("Neue Vorschau. Enter übernimmt den Vorschlag in [eckigen Klammern].\n")
    name = frage("Name des Cafés (z. B. Colonial Café)")
    if not name:
        sys.exit("Ohne Namen geht es nicht.")
    d = {
        "name": name,
        "ort": frage("Ort", "Musterstadt"),
        "plz": frage("PLZ", "12345"),
        "strasse": frage("Straße und Hausnummer", "Lindenstraße 12"),
    }
    tel = frage("Telefon (leer = Beispielnummer)")
    d["tel"], d["tel_link"] = (tel, tel_link(tel)) if tel else ("0123 / 45678", "+4912345678")
    d["email"] = frage("E-Mail", f"info@{slug(name).replace('-', '')}.de")
    d["inhaber"] = frage("Inhaber, z. B. Max Mustermann (leer = Beispielnamen)")

    ziel = HIER / "vorschau" / slug(name)
    ziel.mkdir(parents=True, exist_ok=True)
    for seite in SEITEN:
        text = (HIER / seite).read_text(encoding="utf-8")
        (ziel / seite).write_text(ersetze(text, ersetzungen(d)), encoding="utf-8")

    print(f"\nFertig: vorschau/{slug(name)}/")
    print("Link, sobald hochgeladen: " + LINK.format(slug(name)))


if __name__ == "__main__":
    main()
