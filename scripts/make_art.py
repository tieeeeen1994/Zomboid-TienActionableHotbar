"""Builds the mod's icon, poster and Workshop preview.

    python3 scripts/make_art.py

Needs Pillow. Reads item icons from the local Project Zomboid install (media/texturepacks/UI2.pack, UI.pack), writes:
  Contents/mods/TienActionableHotbar/42/icon.png      128x128
  Contents/mods/TienActionableHotbar/42/poster.png    512x512
  preview.png                                         512x512
"""

import io
import os
import re
import struct

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MOD = os.path.join(REPO, "Contents", "mods", "TienActionableHotbar", "42")
PZ = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/ProjectZomboid/"
    "Project Zomboid.app/Contents/Java"
)
PACKS = [os.path.join(PZ, "media", "texturepacks", name) for name in ("UI2.pack", "UI.pack")]
FONT = "/System/Library/Fonts/Helvetica.ttc"

SS = 4
BG_TOP = (44, 46, 52)
BG_BOTTOM = (14, 15, 18)
ACCENT = (255, 205, 80)
BORDER = (204, 204, 204, 204)
MENU_BG = (26, 26, 26, 235)
MENU_HOVER = (80, 80, 80, 255)
TEXT = (235, 235, 235, 255)

_PACKS = {}


def pack_index(path):
    """name -> (page, x, y, w, h, offsetX, offsetY, originalW, originalH). A .pack is a run of
    int32-length-prefixed entry names, each followed by eight int32s, then once per page a plain
    PNG of the sheet; an entry belongs to the first PNG that starts after it."""
    if path in _PACKS:
        return _PACKS[path]
    if not os.path.exists(path):
        raise SystemExit("Missing game file: " + path)
    blob = open(path, "rb").read()
    pages = list(zip(
        [m.start() for m in re.finditer(rb"\x89PNG\r\n\x1a\n", blob)],
        [m.start() + 12 for m in re.finditer(rb"IEND\xaeB`\x82", blob)],
    ))
    index = {}
    for match in re.finditer(rb"[A-Za-z0-9_]{3,60}", blob):
        at, run = match.start(), match.group()
        if at < 4:
            continue
        length = struct.unpack_from("<i", blob, at - 4)[0]
        if not 3 <= length <= len(run):
            continue
        try:
            rect = struct.unpack_from("<8i", blob, at + length)
        except struct.error:
            continue
        page = next((i for i, p in enumerate(pages) if p[0] > at), None)
        if page is not None:
            index[run[:length].decode()] = (page,) + rect
    _PACKS[path] = {"blob": blob, "pages": pages, "sheets": {}, "index": index}
    return _PACKS[path]


def item_icon(name):
    """The game's item icon, from the first pack that has it (B42 icons are in UI2.pack, older ones
    such as the baseball bat and painkillers only in UI.pack)."""
    for path in PACKS:
        pack = pack_index(path)
        if name not in pack["index"]:
            continue
        page, x, y, w, h, ox, oy, ow, oh = pack["index"][name]
        if page not in pack["sheets"]:
            start, end = pack["pages"][page]
            pack["sheets"][page] = Image.open(io.BytesIO(pack["blob"][start:end])).convert("RGBA")
        icon = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
        icon.paste(pack["sheets"][page].crop((x, y, x + w, y + h)), (ox, oy))
        return icon
    raise SystemExit("No icon named %s in UI2.pack or UI.pack" % name)


def blend(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def backdrop(size):
    img = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=blend(BG_TOP, BG_BOTTOM, y / max(1, size - 1)) + (255,))
    return img


def font(px):
    return ImageFont.truetype(FONT, max(6, round(px)))


def paste_icon(img, icon, box):
    """Pixel art: whole-number nearest-neighbour scale, centred in box."""
    x0, y0, x1, y1 = box
    scale = max(1, int(min(x1 - x0, y1 - y0) * 0.8 // icon.width))
    grown = icon.resize((icon.width * scale, icon.height * scale), Image.NEAREST)
    img.alpha_composite(grown, (round((x0 + x1 - grown.width) / 2), round((y0 + y1 - grown.height) / 2)))


def slot(img, box, number, icon, hovered, k):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle(box, fill=(0, 0, 0, 110))
    if hovered:
        d.rectangle(box, fill=(255, 255, 255, 50))
    d.rectangle(box, outline=BORDER, width=max(1, round(2 * k)))
    img.alpha_composite(layer)
    paste_icon(img, icon, box)
    ImageDraw.Draw(img).text((box[0] + round(6 * k), box[1] + round(3 * k)), number, font=font(20 * k), fill=TEXT)


def arrow(d, x, cy, k):
    s = 5 * k
    d.polygon([(x - s, cy - s), (x + s * 0.4, cy), (x - s, cy + s)], fill=TEXT)


def check(d, x, cy, k):
    w = max(2, round(3 * k))
    d.line([(x, cy), (x + 5 * k, cy + 5 * k), (x + 13 * k, cy - 6 * k)], fill=ACCENT + (255,), width=w, joint="curve")


def menu(img, x, y, w, rows, k, hover=None):
    """rows: (text, has_submenu, checked). Drawn like the game's context menu."""
    row_h = round(30 * k)
    pad = round(6 * k)
    h = row_h * len(rows) + pad * 2
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([x, y, x + w, y + h], fill=MENU_BG, outline=(110, 110, 110, 255), width=max(1, round(2 * k)))
    if hover is not None:
        top = y + pad + hover * row_h
        d.rectangle([x + round(3 * k), top, x + w - round(3 * k), top + row_h], fill=MENU_HOVER)
    img.alpha_composite(layer)
    d = ImageDraw.Draw(img)
    f = font(17 * k)
    for i, (text, sub, checked) in enumerate(rows):
        cy = y + pad + i * row_h + row_h / 2
        if checked:
            check(d, x + round(8 * k), cy, k)
        d.text((x + round(30 * k), cy), text, font=f, fill=TEXT, anchor="lm")
        if sub:
            arrow(d, x + w - round(14 * k), cy, k)
    return [(x, y + pad + i * row_h, x + w, y + pad + (i + 1) * row_h) for i in range(len(rows))]


def poster(size):
    """The hotbar with a baseball bat, whiskey and painkillers; the whiskey's right-click menu
    is open on Change Default Action > Every Whiskey, with Drink > All ticked."""
    k = size / 512.0
    img = backdrop(size)
    icons = [item_icon("Item_BaseballBat"), item_icon("Item_Whiskey"), item_icon("Item_PillsPainkiller")]
    cell = round(112 * k)
    pad = round(18 * k)
    total = cell * 3 + pad * 2
    left = (size - total) // 2
    top = size - cell - round(40 * k)
    bar = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(bar).rectangle(
        [left - pad, top - pad, left + total + pad, top + cell + pad],
        fill=(0, 0, 0, 120), outline=BORDER, width=max(1, round(2 * k)))
    img.alpha_composite(bar)
    for i, icon in enumerate(icons):
        x = left + i * (cell + pad)
        slot(img, (x, top, x + cell, top + cell), str(i + 1), icon, i == 1, k)

    root = menu(img, round(16 * k), round(40 * k), round(224 * k), [
        ("Drink", True, False),
        ("Rename", False, False),
        ("Remove from Hotbar", False, False),
        ("Change Default Action", True, False),
    ], k, hover=3)
    sub_x = root[3][2] - round(4 * k)
    sub = menu(img, sub_x, root[3][1] - round(6 * k), round(212 * k), [
        ("Every Whiskey", True, True),
        ("Only this Whiskey", True, False),
    ], k, hover=0)
    menu(img, sub_x, sub[1][3] + round(14 * k), round(236 * k), [
        ("The game's usual action", False, False),
        ("Drink > All", False, True),
        ("Drink > Half", False, False),
        ("Drink > Quarter", False, False),
    ], k, hover=1)
    return img


def icon(size):
    """One hotbar slot holding whiskey, with a menu badge: the slot does what you picked."""
    big = size * SS
    k = big / 128.0
    img = backdrop(big)
    m = round(10 * k)
    slot(img, (m, m, big - m, big - m), "2", item_icon("Item_Whiskey"), False, k * 1.5)
    r = round(26 * k)
    cx, cy = big - m - r + round(4 * k), big - m - r + round(4 * k)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r - round(3 * k), cy - r - round(3 * k), cx + r + round(3 * k), cy + r + round(3 * k)], fill=(12, 12, 12, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT + (255,))
    w = round(5 * k)
    for dy in (-9, 0, 9):
        yy = cy + round(dy * k)
        d.line([(cx - round(11 * k), yy), (cx + round(11 * k), yy)], fill=(12, 12, 12, 255), width=w)
    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(MOD, exist_ok=True)
    icon(128).convert("RGB").save(os.path.join(MOD, "icon.png"))
    art = poster(512).convert("RGB")
    art.save(os.path.join(MOD, "poster.png"))
    art.save(os.path.join(REPO, "preview.png"))
    print("Wrote icon.png, poster.png and preview.png")


if __name__ == "__main__":
    main()
