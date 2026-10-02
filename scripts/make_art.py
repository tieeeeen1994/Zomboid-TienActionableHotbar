"""Builds the mod's icon, poster and Workshop preview.

    python3 scripts/make_art.py

Needs Pillow. Reads item icons from the local Project Zomboid install (media/texturepacks/UI2.pack, UI.pack), writes:
  Contents/mods/TienActionableHotbar/42/icon.png      128x128
  Contents/mods/TienActionableHotbar/42/poster.png    512x512
  preview.png                                         512x512
"""

import io
import math
import os
import re
import struct

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MOD = os.path.join(REPO, "Contents", "mods", "TienActionableHotbar", "42")
PZ = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/ProjectZomboid/"
    "Project Zomboid.app/Contents/Java"
)
PACKS = [os.path.join(PZ, "media", "texturepacks", name) for name in ("UI2.pack", "UI.pack")]
FONT = "/System/Library/Fonts/Helvetica.ttc"

UI = os.path.join(PZ, "media", "ui")

SS = 4
GLOW = (78, 66, 48)
DARK = (14, 14, 17)
ACCENT = (255, 205, 80)
BORDER = (204, 204, 204, 255)
GOOD = (110, 176, 92)
INK = (12, 12, 12, 255)

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


def ui_image(name):
    path = os.path.join(UI, name)
    if not os.path.exists(path):
        raise SystemExit("Missing game image: " + path)
    return Image.open(path).convert("RGBA")


def font(px, bold=False):
    return ImageFont.truetype(FONT, max(6, round(px)), index=1 if bold else 0)


def backdrop(size):
    """Dark, with a warm glow behind the bottle."""
    img = Image.new("RGBA", (size, size))
    px = img.load()
    cx, cy, r = size * 0.5, size * 0.4, size * 0.62
    for y in range(size):
        for x in range(size):
            t = min(1.0, ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / r)
            t = t * t * (3 - 2 * t)
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(GLOW, DARK)) + (255,)
    return img


def dilate(alpha, px):
    return alpha.filter(ImageFilter.MaxFilter(2 * px + 1)) if px > 0 else alpha


def sticker(icon, scale, ring):
    """Pixel art scaled by a whole number, with a thin dark line and then a white outline one art
    pixel wide, stepped like the pixels (the series' sticker look)."""
    art = icon.resize((icon.width * scale, icon.height * scale), Image.NEAREST)
    pad = ring * 3
    canvas = Image.new("RGBA", (art.width + pad * 2, art.height + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(art, (pad, pad))
    alpha = canvas.getchannel("A").point(lambda a: 255 if a > 40 else 0)
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    white = Image.new("RGBA", canvas.size, (255, 255, 255, 255))
    dark = max(1, ring // 3)
    out.paste(white, (0, 0), dilate(alpha, ring + dark))
    out.paste(Image.new("RGBA", canvas.size, INK), (0, 0), dilate(alpha, dark))
    out.alpha_composite(canvas)
    return out


def shadow(img, layer, at, blur, alpha, offset):
    mask = layer.getchannel("A").point(lambda a: a * alpha // 255)
    pad = blur * 3
    sh = Image.new("RGBA", (layer.width + pad * 2, layer.height + pad * 2), (0, 0, 0, 0))
    black = Image.new("RGBA", layer.size, (0, 0, 0, 255))
    sh.paste(black, (pad, pad), mask)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(sh, (at[0] - pad + offset[0], at[1] - pad + offset[1]))


def place(img, layer, centre):
    at = (round(centre[0] - layer.width / 2), round(centre[1] - layer.height / 2))
    img.alpha_composite(layer, at)
    return at


def slot(img, box, number, icon, k, lit=False):
    """A hotbar slot as the game draws it: thin light border, the slot number top left."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle(box, fill=(255, 255, 255, 46) if lit else (0, 0, 0, 120))
    d.rectangle(box, outline=ACCENT + (255,) if lit else BORDER, width=max(1, round(3 * k)))
    img.alpha_composite(layer)
    if icon is not None:
        scale = max(1, int((box[2] - box[0]) * 0.78 // icon.width))
        art = icon.resize((icon.width * scale, icon.height * scale), Image.NEAREST)
        place(img, art, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
    ImageDraw.Draw(img).text((box[0] + round(8 * k), box[1] + round(4 * k)), number, font=font(24 * k),
                             fill=(255, 255, 255, 255))


def keycap(size, label):
    """A keyboard key, light grey with a darker base, the label in bold."""
    w = size
    h = round(size * 1.06)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = round(size * 0.18)
    edge = max(2, round(size * 0.05))
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=INK)
    d.rounded_rectangle([edge, edge, w - 1 - edge, h - 1 - edge], radius=r - edge, fill=(150, 150, 156, 255))
    d.rounded_rectangle([edge * 2, edge * 1.6, w - 1 - edge * 2, h - 1 - edge * 3.6], radius=r - edge,
                        fill=(232, 232, 236, 255))
    d.text((w / 2, (h - edge * 2) / 2), label, font=font(size * 0.56, bold=True), fill=(40, 40, 44, 255), anchor="mm")
    return img


def moodle(size):
    """The game's Thirst moodle on a good-moodle green background, ringed so it reads as a badge."""
    bg = ui_image("Moodles/128/_Moodles_BGsolid.png")
    tint = Image.new("RGBA", bg.size, GOOD + (255,))
    disc = ImageChops.multiply(bg, tint)
    disc.putalpha(bg.getchannel("A"))
    glass = ui_image("Moodles/128/Status_Thirst.png")
    disc.alpha_composite(glass)
    disc = disc.resize((size, size), Image.LANCZOS)
    ring = max(2, round(size * 0.045))
    out = Image.new("RGBA", (size + ring * 4, size + ring * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.ellipse([0, 0, out.width - 1, out.height - 1], fill=(255, 255, 255, 255))
    d.ellipse([ring, ring, out.width - 1 - ring, out.height - 1 - ring], fill=INK)
    out.alpha_composite(disc, (ring * 2, ring * 2))
    return out


def poster(size):
    k = size / 512.0
    img = backdrop(size)
    bat = item_icon("Item_BaseballBat")
    whiskey = item_icon("Item_Whiskey")
    pills = item_icon("Item_PillsPainkiller")

    cell = round(128 * k)
    gap = round(16 * k)
    total = cell * 3 + gap * 2
    left = (size - total) // 2
    top = size - cell - round(34 * k)
    bar = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(bar).rectangle([left - gap, top - gap, left + total + gap, top + cell + gap],
                                  fill=(0, 0, 0, 130), outline=BORDER, width=max(1, round(2 * k)))
    img.alpha_composite(bar)
    boxes = [(left + i * (cell + gap), top, left + i * (cell + gap) + cell, top + cell) for i in range(3)]
    slot(img, boxes[0], "1", bat, k)
    slot(img, boxes[1], "2", None, k, lit=True)
    slot(img, boxes[2], "3", pills, k)

    bottle = sticker(whiskey, max(1, round(7 * k)), max(1, round(7 * k)))
    centre = (size / 2, round(178 * k))
    at = (round(centre[0] - bottle.width / 2), round(centre[1] - bottle.height / 2))
    shadow(img, bottle, at, max(2, round(10 * k)), 170, (round(10 * k), round(14 * k)))
    img.alpha_composite(bottle, at)

    d = ImageDraw.Draw(img)
    s2 = boxes[1]
    for dx in (-30, 0, 30):
        x = (s2[0] + s2[2]) / 2 + dx * k
        y0, y1 = s2[1] - round(10 * k), s2[1] - round((34 if dx else 46) * k)
        d.line([(x, y0), (x, y1)], fill=(0, 0, 0, 200), width=max(2, round(10 * k)))
        d.line([(x, y0), (x, y1)], fill=ACCENT + (255,), width=max(2, round(5 * k)))

    key = keycap(round(92 * k), "2")
    key_at = (at[0] - round(34 * k), at[1] + round(18 * k))
    shadow(img, key, key_at, max(2, round(6 * k)), 160, (round(6 * k), round(8 * k)))
    img.alpha_composite(key, key_at)

    badge = moodle(round(104 * k))
    badge_at = (at[0] + bottle.width - round(96 * k), at[1] + bottle.height - badge.height + round(14 * k))
    shadow(img, badge, badge_at, max(2, round(6 * k)), 160, (round(6 * k), round(8 * k)))
    img.alpha_composite(badge, badge_at)
    return img


def icon(size):
    big = size * SS
    k = big / 128.0
    img = backdrop(big)
    bottle = sticker(item_icon("Item_Whiskey"), round(3 * k), round(1.2 * k))
    centre = (big * 0.47, big * 0.5)
    at = (round(centre[0] - bottle.width / 2), round(centre[1] - bottle.height / 2))
    shadow(img, bottle, at, round(3 * k), 160, (round(2 * k), round(3 * k)))
    img.alpha_composite(bottle, at)
    key = keycap(round(40 * k), "2")
    img.alpha_composite(key, (round(6 * k), round(6 * k)))
    badge = moodle(round(46 * k))
    img.alpha_composite(badge, (big - badge.width - round(5 * k), big - badge.height - round(5 * k)))
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
