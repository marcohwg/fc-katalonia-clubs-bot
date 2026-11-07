"""Zeichnet ein Spielfeld mit der Aufstellung als PNG-Bild."""
import io

from PIL import Image, ImageDraw, ImageFont

BREITE, HOEHE = 900, 1150
RAND = 40          # Abstand Spielfeld zum Bildrand (seitlich/unten)
OBEN = 110         # Platz für die Überschrift

RASEN_HELL = (52, 140, 72)
RASEN_DUNKEL = (44, 124, 63)
LINIE = (235, 245, 235)

# Kreisfarbe je Mannschaftsteil (wie auf Taktik-Grafiken üblich)
FARBEN = {
    "tw": (36, 52, 128),
    "abwehr": (240, 190, 20),
    "mittelfeld": (238, 125, 15),
    "sturm": (205, 30, 35),
}


def mannschaftsteil(position: str) -> str:
    if position == "TW":
        return "tw"
    if position in ("IV", "LV", "RV"):
        return "abwehr"
    if position in ("ST", "LF", "RF"):
        return "sturm"
    return "mittelfeld"


def schrift(groesse: int, fett: bool = False):
    """Versucht eine gängige Schrift, sonst die eingebaute von Pillow."""
    kandidaten = (
        ["DejaVuSans-Bold.ttf", "arialbd.ttf"] if fett else ["DejaVuSans.ttf", "arial.ttf"]
    ) + ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for name in kandidaten:
        try:
            return ImageFont.truetype(name, groesse)
        except OSError:
            continue
    return ImageFont.load_default(size=groesse)


def kuerzen(text: str, max_laenge: int = 16) -> str:
    return text if len(text) <= max_laenge else text[: max_laenge - 1] + "…"


def zeichne_spielfeld(draw: ImageDraw.ImageDraw):
    links, rechts = RAND, BREITE - RAND
    oben, unten = OBEN, HOEHE - RAND
    feld_b, feld_h = rechts - links, unten - oben

    # Rasenstreifen
    streifen = 10
    for i in range(streifen):
        y0 = oben + feld_h * i / streifen
        y1 = oben + feld_h * (i + 1) / streifen
        draw.rectangle([links, y0, rechts, y1], fill=RASEN_HELL if i % 2 == 0 else RASEN_DUNKEL)

    w = 4
    mitte_x, mitte_y = (links + rechts) / 2, (oben + unten) / 2
    draw.rectangle([links, oben, rechts, unten], outline=LINIE, width=w)
    draw.line([links, mitte_y, rechts, mitte_y], fill=LINIE, width=w)
    r = feld_b * 0.13
    draw.ellipse([mitte_x - r, mitte_y - r, mitte_x + r, mitte_y + r], outline=LINIE, width=w)
    draw.ellipse([mitte_x - 6, mitte_y - 6, mitte_x + 6, mitte_y + 6], fill=LINIE)

    # Strafräume, Fünfmeterräume und Tore oben + unten
    sr_b, sr_h = feld_b * 0.56, feld_h * 0.15
    fm_b, fm_h = feld_b * 0.26, feld_h * 0.055
    tor_b = feld_b * 0.14
    for y_kante, richtung in ((oben, 1), (unten, -1)):
        y_sr = y_kante + richtung * sr_h
        y_fm = y_kante + richtung * fm_h
        draw.rectangle([mitte_x - sr_b / 2, min(y_kante, y_sr), mitte_x + sr_b / 2, max(y_kante, y_sr)],
                       outline=LINIE, width=w)
        draw.rectangle([mitte_x - fm_b / 2, min(y_kante, y_fm), mitte_x + fm_b / 2, max(y_kante, y_fm)],
                       outline=LINIE, width=w)
        draw.line([mitte_x - tor_b / 2, y_kante, mitte_x + tor_b / 2, y_kante], fill=(255, 255, 255), width=w + 6)

    return links, oben, feld_b, feld_h


def erstelle_bild(titel: str, spieler: list) -> io.BytesIO:
    """spieler: Liste von (position, x, y, name). x/y von 0 bis 1, y=0 ist vorne (Angriff).
    name darf None sein, dann wird die Position als frei angezeigt."""
    bild = Image.new("RGB", (BREITE, HOEHE), (24, 28, 34))
    draw = ImageDraw.Draw(bild)

    draw.text((BREITE / 2, OBEN / 2), titel, font=schrift(46, fett=True), fill="white", anchor="mm")
    links, oben, feld_b, feld_h = zeichne_spielfeld(draw)

    f_pos = schrift(24, fett=True)
    f_name = schrift(26, fett=True)
    radius = 38

    for position, x, y, name in spieler:
        cx = links + x * feld_b
        cy = oben + y * feld_h
        farbe = FARBEN[mannschaftsteil(position)]

        # Schatten + Kreis
        draw.ellipse([cx - radius + 3, cy - radius + 5, cx + radius + 3, cy + radius + 5], fill=(20, 60, 30))
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=farbe, outline="white", width=3)
        draw.text((cx, cy), position, font=f_pos, fill="white", anchor="mm")

        text = kuerzen(name) if name else "frei"
        draw.text((cx, cy + radius + 20), text, font=f_name, fill="white" if name else (200, 200, 200),
                  anchor="mm", stroke_width=4, stroke_fill=(15, 15, 15))

    puffer = io.BytesIO()
    bild.save(puffer, format="PNG")
    puffer.seek(0)
    return puffer
