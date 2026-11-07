"""Zeichnet die Aufstellung im FC-Katalonia-Look."""
import io
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ORDNER = os.path.dirname(os.path.abspath(__file__))
WAPPEN = os.path.join(ORDNER, "wappen.png")

S = 2                      # intern doppelt so groß zeichnen -> glatte Kanten
B, H = 1000 * S, 1400 * S  # Endgröße 1000 x 1400

NAVY = (12, 19, 42)
NAVY_HELL = (20, 31, 64)
ROT = (150, 22, 38)
BLAU = (28, 44, 120)
GOLD = (214, 172, 88)
GOLD_HELL = (247, 214, 138)
GOLD_DUNKEL = (130, 92, 34)

# Freie Schriften (Google Fonts, SIL Open Font License) im Ordner "schriften"
SCHRIFT_TITEL = ("Cinzel.ttf", "Black")
SCHRIFT_NAME = ("Oswald.ttf", "Bold")

_schriften = {}


def schrift(art, groesse):
    datei, stil = art
    schluessel = (datei, groesse)
    if schluessel not in _schriften:
        try:
            f = ImageFont.truetype(os.path.join(ORDNER, "schriften", datei), groesse)
            try:
                f.set_variation_by_name(stil)
            except Exception:
                pass
        except OSError:
            f = ImageFont.load_default(size=groesse)
        _schriften[schluessel] = f
    return _schriften[schluessel]


def gold_text(bild, pos, text, font, schatten=True):
    """Zentrierter Text mit Gold-Verlauf, dunklem Rand und optional Schatten."""
    rand = 12 * S
    mess = ImageDraw.Draw(bild).textbbox((0, 0), text, font=font, anchor="mm", stroke_width=2 * S)
    w = int(mess[2] - mess[0]) + 2 * rand
    h = int(mess[3] - mess[1]) + 2 * rand
    mitte = (w / 2, h / 2)
    ebene = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if schatten:
        s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(s).text((mitte[0] + 2 * S, mitte[1] + 3 * S), text, font=font, anchor="mm",
                               fill=(0, 0, 0, 190), stroke_width=2 * S, stroke_fill=(0, 0, 0, 190))
        ebene.alpha_composite(s.filter(ImageFilter.GaussianBlur(3 * S)))

    ImageDraw.Draw(ebene).text(mitte, text, font=font, anchor="mm", fill=GOLD_DUNKEL,
                               stroke_width=2 * S, stroke_fill=(35, 22, 6))
    verlauf = Image.new("RGBA", (w, h))
    vd = ImageDraw.Draw(verlauf)
    oben, unten = rand, h - rand
    for y in range(h):
        t = min(1, max(0, (y - oben) / max(1, unten - oben)))
        if t < 0.5:
            f = tuple(int(GOLD_HELL[i] + (GOLD[i] - GOLD_HELL[i]) * t * 2) for i in range(3))
        else:
            f = tuple(int(GOLD[i] + (GOLD_DUNKEL[i] - GOLD[i]) * (t - 0.5) * 2) for i in range(3))
        vd.line([(0, y), (w, y)], fill=f + (255,))
    maske = Image.new("L", (w, h), 0)
    ImageDraw.Draw(maske).text(mitte, text, font=font, anchor="mm", fill=255)
    ebene.paste(verlauf, (0, 0), maske)
    bild.alpha_composite(ebene, (int(pos[0] - w / 2), int(pos[1] - h / 2)))


def hintergrund():
    bild = Image.new("RGBA", (B, H), NAVY + (255,))
    # Diagonale rot-blaue Streifen, nur in den Ecken oben rechts und unten links
    streifen = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(streifen)
    breite = 80 * S
    for i in range(-25, 30):
        x = i * breite
        sd.polygon([(x, 0), (x + breite, 0), (x + breite - H, H), (x - H, H)],
                   fill=(ROT if i % 2 == 0 else BLAU) + (255,))
    maske = Image.new("L", (B, H), 0)
    md = ImageDraw.Draw(maske)
    md.ellipse([B * 0.55, -H * 0.35, B * 1.5, H * 0.35], fill=120)
    md.ellipse([-B * 0.5, H * 0.65, B * 0.45, H * 1.35], fill=120)
    md.rectangle([0, 0, B, H], outline=60, width=40 * S)
    maske = maske.filter(ImageFilter.GaussianBlur(70 * S))
    bild.paste(streifen, (0, 0), maske)
    return bild


def rahmen(bild):
    d = ImageDraw.Draw(bild)
    a = 18 * S
    d.rectangle([a, a, B - a, H - a], outline=GOLD, width=4 * S)
    d.rectangle([a + 10 * S, a + 10 * S, B - a - 10 * S, H - a - 10 * S], outline=GOLD_DUNKEL, width=2 * S)
    l = 70 * S
    for ex, ey, sx, sy in ((a, a, 1, 1), (B - a, a, -1, 1), (a, H - a, 1, -1), (B - a, H - a, -1, -1)):
        d.line([(ex, ey + sy * l), (ex + sx * l, ey)], fill=GOLD, width=4 * S)
        d.polygon([(ex, ey), (ex + sx * 34 * S, ey), (ex, ey + sy * 34 * S)], fill=GOLD)
        r = 6 * S
        cx, cy = ex + sx * 26 * S, ey + sy * 26 * S
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NAVY, outline=GOLD, width=2 * S)


def wappen_einfuegen(bild, mitte, groesse):
    if not os.path.exists(WAPPEN):
        return
    w = Image.open(WAPPEN).convert("RGBA")
    breite, hoehe = w.size
    rand = int(min(breite, hoehe) * 0.04)
    w = w.crop((rand, rand, breite - rand, hoehe - rand)).resize((groesse, groesse), Image.LANCZOS)
    # Rand weich ausblenden, damit der Hintergrund des Wappens verschwindet
    maske = Image.new("L", (groesse, groesse), 0)
    ImageDraw.Draw(maske).ellipse([groesse * 0.06, groesse * 0.04, groesse * 0.94, groesse * 0.96], fill=255)
    maske = maske.filter(ImageFilter.GaussianBlur(groesse * 0.05))
    w.putalpha(maske)
    bild.alpha_composite(w, (int(mitte[0] - groesse / 2), int(mitte[1] - groesse / 2)))


def kopfzeile(bild, formation):
    wappen_einfuegen(bild, (175 * S, 170 * S), 290 * S)
    d = ImageDraw.Draw(bild)
    mitte_x = 650 * S
    gold_text(bild, (mitte_x, 120 * S), "FC KATALONIA", schrift(SCHRIFT_TITEL, 76 * S))

    f = schrift(SCHRIFT_TITEL, 38 * S)
    text = formation.upper()
    tb = d.textbbox((0, 0), text, font=f)
    w = (tb[2] - tb[0]) + 70 * S
    y = 212 * S
    h = 62 * S
    box = [mitte_x - w / 2, y - h / 2, mitte_x + w / 2, y + h / 2]
    d.rounded_rectangle(box, radius=10 * S, fill=NAVY, outline=GOLD, width=3 * S)
    d.rounded_rectangle([box[0] + 6 * S, box[1] + 6 * S, box[2] - 6 * S, box[3] - 6 * S], radius=7 * S,
                        outline=GOLD_DUNKEL, width=2 * S)
    for richtung in (-1, 1):
        x0 = mitte_x + richtung * (w / 2 + 12 * S)
        x1 = mitte_x + richtung * 300 * S
        x1 = min(x1, B - 60 * S) if richtung > 0 else max(x1, 360 * S)
        if (x1 - x0) * richtung > 20 * S:
            d.line([(x0, y), (x1, y)], fill=GOLD, width=3 * S)
            d.polygon([(x1, y - 6 * S), (x1 + richtung * 10 * S, y), (x1, y + 6 * S)], fill=GOLD)
    gold_text(bild, (mitte_x, y + 2 * S), text, f, schatten=False)


# --- Spielfeld in leichter Perspektive -------------------------------------------------
FELD_OBEN, FELD_UNTEN = 300 * S, 1335 * S
BREITE_OBEN, BREITE_UNTEN = 760 * S, 930 * S


def projiziere(x, y):
    """x/y von 0 bis 1 (y=0 vorne) -> Bildkoordinaten auf dem perspektivischen Feld."""
    breite = BREITE_OBEN + (BREITE_UNTEN - BREITE_OBEN) * y
    return B / 2 + (x - 0.5) * breite, FELD_OBEN + (FELD_UNTEN - FELD_OBEN) * y


def spielfeld(bild):
    ebene = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ebene)

    def linie(punkte, breite=3):
        d.line([projiziere(x, y) for x, y in punkte], fill=GOLD + (230,), width=breite * S, joint="curve")

    d.polygon([projiziere(0, 0), projiziere(1, 0), projiziere(1, 1), projiziere(0, 1)], fill=NAVY_HELL + (170,))
    linie([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], 4)
    linie([(0, 0.5), (1, 0.5)])
    linie([(0.5 + 0.13 * math.cos(t / 60 * 2 * math.pi), 0.5 + 0.09 * math.sin(t / 60 * 2 * math.pi))
           for t in range(61)])
    mx, my = projiziere(0.5, 0.5)
    d.ellipse([mx - 5 * S, my - 5 * S, mx + 5 * S, my + 5 * S], fill=GOLD)
    for y_kante, r in ((0, 1), (1, -1)):
        linie([(0.22, y_kante), (0.22, y_kante + r * 0.15), (0.78, y_kante + r * 0.15), (0.78, y_kante)])
        linie([(0.37, y_kante), (0.37, y_kante + r * 0.055), (0.63, y_kante + r * 0.055), (0.63, y_kante)])
        linie([(0.5 + 0.1 * math.cos(t / 30 * math.pi), y_kante + r * (0.15 + 0.04 * math.sin(t / 30 * math.pi)))
               for t in range(6, 25)])
    bild.alpha_composite(ebene)


# --- Trikots ---------------------------------------------------------------------------
TRIKOT_FORM = [
    (-0.13, -0.50), (-0.34, -0.45), (-0.55, -0.27), (-0.44, -0.08), (-0.32, -0.16),
    (-0.32, 0.50), (0.32, 0.50), (0.32, -0.16), (0.44, -0.08), (0.55, -0.27),
    (0.34, -0.45), (0.13, -0.50), (0.0, -0.40),
]


def trikot(bild, cx, cy, g, torwart=False):
    """Zeichnet ein Trikot der Größe g mit Mittelpunkt (cx, cy)."""
    w, h = int(1.4 * g), int(1.35 * g)
    ox, oy = w / 2, h * 0.45                 # Trikot-Mitte innerhalb des Ausschnitts
    punkte = [(ox + px * g, oy + py * g) for px, py in TRIKOT_FORM]
    ebene = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    schatten = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(schatten).polygon([(x + 5 * S, y + 8 * S) for x, y in punkte], fill=(0, 0, 0, 170))
    ebene.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(6 * S)))

    stoff = Image.new("RGBA", (w, h))
    sd = ImageDraw.Draw(stoff)
    if torwart:
        sd.rectangle([0, 0, w, h], fill=(22, 22, 26))
    else:
        links = ox - 0.55 * g
        anzahl = 9
        sd.rectangle([0, 0, w, h], fill=ROT)
        for i in range(1, anzahl, 2):
            x0 = links + 1.1 * g * i / anzahl
            sd.rectangle([x0, 0, x0 + 1.1 * g / anzahl, h], fill=BLAU)
    licht = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(licht)
    for x in range(w):
        t = min(1, abs((x - ox) / (0.55 * g) + 0.15))
        ld.line([(x, 0), (x, h)], fill=(0, 0, 0, int(160 * t ** 2)))
    stoff.alpha_composite(licht)
    glanz = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glanz).ellipse([ox - 0.35 * g, oy - 0.7 * g, ox + 0.1 * g, oy + 0.05 * g],
                                  fill=(255, 255, 255, 40))
    stoff.alpha_composite(glanz.filter(ImageFilter.GaussianBlur(g * 0.1)))

    maske = Image.new("L", (w, h), 0)
    ImageDraw.Draw(maske).polygon(punkte, fill=255)
    ebene.paste(stoff, (0, 0), maske)

    d = ImageDraw.Draw(ebene)
    d.line(punkte + [punkte[0]], fill=GOLD, width=3 * S, joint="curve")
    d.line([(ox - 0.13 * g, oy - 0.5 * g), (ox, oy - 0.40 * g), (ox + 0.13 * g, oy - 0.5 * g)],
           fill=GOLD, width=5 * S, joint="curve")
    for r in (-1, 1):
        v = 0.06 * g
        d.line([(ox + r * 0.55 * g - r * v, oy - 0.27 * g + v * 0.3),
                (ox + r * 0.44 * g - r * v, oy - 0.08 * g - v * 0.3)], fill=GOLD, width=3 * S)
    # Kleine Krone auf der Brust
    kx, ky, k = ox, oy - 0.3 * g, g * 0.05
    d.polygon([(kx - k, ky + k * 0.6), (kx - k, ky - k * 0.4), (kx - k * 0.5, ky), (kx, ky - k * 0.8),
               (kx + k * 0.5, ky), (kx + k, ky - k * 0.4), (kx + k, ky + k * 0.6)], fill=GOLD)

    bild.alpha_composite(ebene, (int(cx - ox), int(cy - oy)))


def passende_schrift(text, namen, start, max_breite):
    groesse = start
    while groesse > 12 * S:
        f = schrift(namen, groesse)
        if f.getlength(text) <= max_breite:
            return f
        groesse -= 2 * S
    return schrift(namen, groesse)


def kuerzen(text, max_laenge=14):
    return text if len(text) <= max_laenge else text[: max_laenge - 1] + "…"


def erstelle_bild(formation: str, spieler: list) -> io.BytesIO:
    """spieler: Liste von (position, x, y, name). x/y von 0 bis 1, y=0 ist vorne."""
    bild = hintergrund()
    rahmen(bild)
    spielfeld(bild)
    kopfzeile(bild, formation)

    g = 122 * S
    plaetze = []
    for position, x, y, name in sorted(spieler, key=lambda s: s[2]):
        cx, cy = projiziere(x, y)
        cy -= 22 * S
        plaetze.append((position, cx, cy, name))
        trikot(bild, cx, cy, g, torwart=(position == "TW"))

    # Texte erst nach allen Trikots, damit nichts verdeckt wird
    f_pos = schrift(SCHRIFT_TITEL, 22 * S)
    for position, cx, cy, name in plaetze:
        text = kuerzen(name or "frei").upper()
        f = passende_schrift(text, SCHRIFT_NAME, 28 * S, 0.58 * g)
        gold_text(bild, (cx, cy + 0.06 * g), text, f, schatten=False)
        gold_text(bild, (cx, cy + 0.66 * g), position, f_pos)

    ende = bild.convert("RGB").resize((B // S, H // S), Image.LANCZOS)
    puffer = io.BytesIO()
    ende.save(puffer, format="PNG", optimize=True)
    puffer.seek(0)
    return puffer
