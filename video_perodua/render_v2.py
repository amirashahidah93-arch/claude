"""Video 40s 9:16 - Balik Kampung bersama Perodua Aruz, Ativa & Bezza.
Render: python3 render.py  -> output video.mp4
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

W, H, FPS, DUR = 1080, 1920, 30, 40.0
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

YELLOW = (255, 210, 0)
NAVY = (12, 24, 48)
WHITE = (255, 255, 255)
RED = (230, 30, 45)

# ---------------------------------------------------------------- helpers
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)

def ease_out_cubic(p): return 1 - (1 - p) ** 3
def ease_in_out(p): return 3 * p * p - 2 * p * p * p
def ease_out_back(p, s=1.9):
    p -= 1
    return p * p * ((s + 1) * p + s) + 1
def ease_out_bounce(p):
    n, d = 7.5625, 2.75
    if p < 1 / d: return n * p * p
    if p < 2 / d: p -= 1.5 / d; return n * p * p + .75
    if p < 2.5 / d: p -= 2.25 / d; return n * p * p + .9375
    p -= 2.625 / d; return n * p * p + .984375

def lerp(a, b, p): return a + (b - a) * p

_emoji_cache = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _emoji_cache:
        f = ImageFont.truetype(EMOJI, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        im = im.crop(im.getbbox())
        sc = size / max(im.size)
        _emoji_cache[k] = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    return _emoji_cache[k]

def paste_scaled(dst, src, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01: return
    im = src
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    dst.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def text_sticker(text, size, fg=NAVY, bg=YELLOW, pad=(34, 18), radius=22, fpath=FONT_XB, shadow=True, stroke=None):
    f = font(fpath, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke[0] if stroke else 0)
    tw, th = r - l, b - t
    w, h = tw + pad[0] * 2, th + pad[1] * 2
    sh = 12 if shadow and bg else 0
    im = Image.new("RGBA", (w + sh, h + sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg:
        if shadow:
            d.rounded_rectangle((sh, sh, w + sh - 1, h + sh - 1), radius, fill=(0, 0, 0, 110))
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=bg)
    kw = {}
    if stroke: kw = dict(stroke_width=stroke[0], stroke_fill=stroke[1])
    d.text((pad[0] - l, pad[1] - t), text, font=f, fill=fg, **kw)
    return im

def outlined_text(text, size, fg=WHITE, stroke_w=10, stroke_c=NAVY, fpath=FONT_XB):
    return text_sticker(text, size, fg=fg, bg=None, pad=(stroke_w + 6, stroke_w + 6), fpath=fpath,
                        shadow=False, stroke=(stroke_w, stroke_c))

def pop(t, t0, dur=0.35):
    """scale for a pop-in sticker"""
    p = prog(t, t0, t0 + dur)
    return 0 if p <= 0 else ease_out_back(p)

# ---------------------------------------------------------------- suitcase art
def make_suitcase(w, h, color, kind="hard"):
    S = 2
    w2, h2 = w * S, h * S
    im = Image.new("RGBA", (w2, h2 + 0), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.7) for c in color)
    light = tuple(min(255, int(c * 1.0 + 60)) for c in color)
    if kind == "duffel":
        top = int(h2 * 0.28)
        d.arc((w2 * .25, 0, w2 * .75, top * 2.2), 180, 360, fill=dark, width=int(10 * S))
        d.rounded_rectangle((0, top, w2 - 1, h2 - 1), radius=int(h2 * .35), fill=color)
        d.line((w2 * .12, top + (h2 - top) * .45, w2 * .88, top + (h2 - top) * .45), fill=dark, width=int(5 * S))
        d.rounded_rectangle((w2 * .1, top + 10 * S, w2 * .45, top + 22 * S), radius=8 * S, fill=light)
        return im.resize((w, h), Image.LANCZOS)
    handle_h = int(h2 * 0.12)
    wheel = int(h2 * 0.05)
    body = (0, handle_h, w2 - 1, h2 - wheel - 1)
    # handle
    d.rounded_rectangle((w2 * .3, 0, w2 * .7, handle_h + 12 * S), radius=10 * S, outline=(40, 40, 40), width=int(7 * S))
    # wheels
    for x in (w2 * .15, w2 * .85):
        d.ellipse((x - wheel, h2 - 2 * wheel, x + wheel, h2 - 1), fill=(30, 30, 30))
    d.rounded_rectangle(body, radius=int(w2 * .12), fill=color)
    # ribs
    for fx in (.3, .5, .7):
        d.rounded_rectangle((w2 * fx - 4 * S, handle_h + 18 * S, w2 * fx + 4 * S, h2 - wheel - 18 * S), radius=4 * S, fill=dark)
    # highlight
    d.rounded_rectangle((w2 * .07, handle_h + 14 * S, w2 * .16, h2 - wheel - 40 * S), radius=6 * S, fill=light + (150,))
    return im.resize((w, h), Image.LANCZOS)

BAG_COLORS = [(232, 52, 92), (40, 150, 230), (255, 186, 0), (40, 190, 120), (150, 90, 220), (250, 120, 40)]

def drop_shadow(dst, cx, by, w, alpha):
    if alpha <= 0: return
    sh = Image.new("RGBA", (int(w * 1.1), int(w * .22)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(0, 0, 0, int(120 * alpha)))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    dst.alpha_composite(sh, (int(cx - sh.width / 2), int(by - sh.height / 2)))

def draw_drop(dst, bag, cx, bottom_y, t, t_land, fall=500, fall_dur=0.32):
    """bag falls and lands at t_land with squash."""
    t0 = t_land - fall_dur
    if t < t0: return
    if t < t_land:
        p = (t - t0) / fall_dur
        y = bottom_y - fall * (1 - p * p)
        sx, sy = 0.92, 1.08
        drop_shadow(dst, cx, bottom_y, bag.width, p)
    else:
        q = t - t_land
        y = bottom_y
        sq = 0.16 * math.exp(-q * 9) * math.cos(q * 30)
        sx, sy = 1 + sq, 1 - sq
        drop_shadow(dst, cx, bottom_y, bag.width, 1)
    im = bag.resize((max(1, int(bag.width * sx)), max(1, int(bag.height * sy))), Image.BICUBIC)
    dst.alpha_composite(im, (int(cx - im.width / 2), int(y - im.height)))

# ---------------------------------------------------------------- backgrounds
def make_sunset():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([255, 120, 40]); mid = np.array([255, 190, 70]); bot = np.array([255, 225, 140])
    g = np.where(y < .55, top + (mid - top) * (y / .55), mid + (bot - mid) * ((y - .55) / .45))
    arr = np.repeat(g[:, None, :], W, axis=1).reshape(H, W, 3)
    im = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    # sun
    sun = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sun).ellipse((W / 2 - 230, 1050, W / 2 + 230, 1510), fill=(255, 245, 200, 255))
    sun = sun.filter(ImageFilter.GaussianBlur(4))
    glow = sun.filter(ImageFilter.GaussianBlur(80))
    im.alpha_composite(glow); im.alpha_composite(sun)
    # hills
    d = ImageDraw.Draw(im)
    pts = [(0, 1380)] + [(x, 1380 - 70 * math.sin(x / 170) - 40 * math.sin(x / 61)) for x in range(0, W + 20, 20)] + [(W, H), (0, H)]
    d.polygon(pts, fill=(210, 90, 60))
    pts = [(0, 1460)] + [(x, 1450 - 50 * math.sin(x / 120 + 2) - 25 * math.sin(x / 47)) for x in range(0, W + 20, 20)] + [(W, H), (0, H)]
    d.polygon(pts, fill=(140, 60, 60))
    # coconut trees
    def tree(x, base, h, lean):
        tx = x + lean
        d.line([(x, base), (x + lean * .4, base - h * .5), (tx, base - h)], fill=(60, 30, 40), width=16, joint="curve")
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            ex, ey = tx + math.cos(a) * 130, base - h + math.sin(a) * 60 + 30
            d.polygon([(tx, base - h), (ex, ey), (tx + math.cos(a) * 60, base - h + math.sin(a) * 25 + 12)], fill=(60, 30, 40))
    tree(110, 1520, 420, 40); tree(980, 1500, 360, -50); tree(880, 1520, 260, 30)
    # ground / road
    d.rectangle((0, 1500, W, H), fill=(80, 40, 50))
    d.polygon([(W / 2 - 90, 1500), (W / 2 + 90, 1500), (W + 300, H), (-300, H)], fill=(45, 45, 60))
    return im

def road_dashes(im, t):
    d = ImageDraw.Draw(im)
    for i in range(8):
        z = ((i / 8) + t * 0.9) % 1.0
        y0 = 1500 + (H - 1500) * z * z
        y1 = 1500 + (H - 1500) * min(1, (z + .06)) ** 2
        w0, w1 = 4 + 30 * z * z, 4 + 30 * min(1, z + .06) ** 2
        d.polygon([(W / 2 - w0 / 2, y0), (W / 2 + w0 / 2, y0), (W / 2 + w1 / 2, y1), (W / 2 - w1 / 2, y1)], fill=(255, 220, 90))

def make_blur_bg(photo):
    sc = max(W / photo.width, H / photo.height) * 1.15
    im = photo.resize((int(photo.width * sc), int(photo.height * sc)), Image.BILINEAR)
    l = (im.width - W) // 2; tp = (im.height - H) // 2
    im = im.crop((l, tp, l + W, tp + H)).filter(ImageFilter.GaussianBlur(38))
    dark = Image.new("RGB", (W, H), (10, 20, 40))
    return Image.blend(im.convert("RGB"), dark, 0.45).convert("RGBA")

# ---------------------------------------------------------------- assets (global, built once per process)
A = {}
def init():
    if A: return
    A["sunset"] = make_sunset()
    for k in ("aruz", "aruz2", "ativa", "bezza"):
        p = Image.open(os.path.join(HERE, k + ".jpg")).convert("RGBA")
        A[k] = p
        A[k + "_bg"] = make_blur_bg(p)
    A["bags"] = [make_suitcase(200, 300, c) for c in BAG_COLORS]
    A["big_bags"] = [make_suitcase(int(260 * s), int(380 * s), c) for s, c in
                     zip((1.0, .9, 1.1, .8, .95), BAG_COLORS)]
    A["duffel"] = make_suitcase(320, 200, (90, 110, 140), "duffel")

# ---------------------------------------------------------------- card (photo + camera)


def camera_crop(photo, cx, cy, zoom, out_w, out_h):
    """cx, cy in normalized photo coords; zoom 1 = cover"""
    ar = out_w / out_h
    if photo.width / photo.height > ar:
        bh = photo.height; bw = bh * ar
    else:
        bw = photo.width; bh = bw / ar
    cw, ch = bw / zoom, bh / zoom
    x = clamp(cx * photo.width - cw / 2, 0, photo.width - cw)
    y = clamp(cy * photo.height - ch / 2, 0, photo.height - ch)
    return photo.resize((out_w, out_h), Image.BICUBIC, box=(max(0, x), max(0, y), min(photo.width, x + cw), min(photo.height, y + ch)))

def interp_cam(keys, t):
    """keys: list of (time, cx, cy, zoom, rot); eased moves of 0.35s into each key"""
    cur = keys[0][1:]
    for i in range(1, len(keys)):
        k = keys[i]
        if t >= k[0]:
            p = ease_out_cubic(prog(t, k[0], k[0] + 0.4))
            prev = cur
            cur = tuple(lerp(a, b, p) for a, b in zip(prev, k[1:]))
            if p < 1:
                return cur
    return cur

def rounded_card(img, radius=36, border=8):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    out = Image.new("RGBA", (w + border * 2 + 20, h + border * 2 + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((14, 18, w + border * 2 + 13, h + border * 2 + 17), radius + border, fill=(0, 0, 0, 120))
    d.rounded_rectangle((0, 0, w + border * 2 - 1, h + border * 2 - 1), radius + border, fill=WHITE)
    img = img.convert("RGBA"); img.putalpha(mask)
    out.alpha_composite(img, (border, border))
    return out

def check_icon(size, color=(30, 190, 100)):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=color)
    d.line([(size * .27, size * .52), (size * .44, size * .69), (size * .74, size * .33)], fill=WHITE, width=max(3, size // 9), joint="curve")
    return im

# ---------------------------------------------------------------- per-car scene
CARS = {
    "aruz": dict(num="01", name="PERODUA ARUZ", sub="Jom tengok ruang boot\n3 model ni!"),
    "ativa": dict(num="02", name="PERODUA ATIVA", sub="Praktikal untuk\nperjalanan anda.",
                  liters=(303, 369), count=(3.0, 4.2),
                  cam=[(0, .5, .5, 1.0, 0), (2.5, .5, .62, 1.35, 0), (6.5, .6, .6, 1.25, 3)]),
    "bezza": dict(num="03", name="PERODUA BEZZA", sub="Ruang boot luas untuk\nbarang keperluan anda.",
                  liters=(508,), count=(3.0, 4.2),
                  cam=[(0, .5, .6, 1.0, 0), (2.5, .46, .7, 1.45, 0), (6.5, .56, .68, 1.3, -3)]),
}
ARUZ_PANELS = [  # image, label, liters, focus start, count window
    ("aruz", "7 TEMPAT DUDUK", 213, 2.5, (2.6, 3.6)),
    ("aruz2", "BARIS KE-3 DILIPAT", 514, 5.5, (5.6, 6.6)),
]
CARD_W, CARD_H, CARD_CY = 860, 860, 990
SUB_Y = 1545

def liter_badge(text, size=120):
    big = outlined_text(text, size, fg=YELLOW, stroke_w=12, stroke_c=NAVY)
    return big

def count_val(v, tau, win):
    return int(round(v * ease_out_cubic(prog(tau, *win))))

def header_and_sub(frame, cfg, tau):
    s = pop(tau, 0.15)
    paste_scaled(frame, text_sticker(cfg["num"], 120, fg=NAVY, bg=YELLOW, pad=(34, 10)), 190, 380, s, rot=-6)
    nm = outlined_text(cfg["name"].split(" ")[1], 150, fg=WHITE, stroke_w=12, stroke_c=NAVY)
    sx = ease_out_cubic(prog(tau, 0.3, 0.7))
    paste_scaled(frame, outlined_text("PERODUA", 64, fg=YELLOW, stroke_w=8), 290 + (1 - sx) * 900 + 175, 335, alpha=sx)
    paste_scaled(frame, nm, 640 + (1 - sx) * 900 - 30, 445, alpha=sx)
    sp = ease_out_cubic(prog(tau, 0.9, 1.3))
    if sp > 0:
        for i, ln in enumerate(cfg["sub"].split("\n")):
            st = text_sticker(ln, 54, fg=NAVY, bg=WHITE, pad=(30, 12), radius=16, fpath=FONT_B)
            paste_scaled(frame, st, W / 2 + (1 - sp) * (-200 if i % 2 == 0 else 200), SUB_Y + i * 98, alpha=sp)

def blur_bg(key, tau):
    bg = A[key + "_bg"]
    z = 1 + 0.04 * tau / 9
    f = bg.resize((int(W * z), int(H * z)), Image.BILINEAR)
    return f.crop(((f.width - W) // 2, (f.height - H) // 2, (f.width - W) // 2 + W, (f.height - H) // 2 + H))

def funny_sticker(frame, tau, t0, x, y):
    s = pop(tau, t0)
    if s:
        st = text_sticker("ORANG PUN MUAT!", 46, fg=WHITE, bg=RED, pad=(26, 12), radius=40)
        paste_scaled(frame, st, x, y, s * (1 + .04 * math.sin(tau * 8)), rot=6)
        paste_scaled(frame, emoji("😆", 80), x + st.width / 2 - 10, y - 40, s, rot=12)

def scene_aruz(tau):
    cfg = CARS["aruz"]
    frame = blur_bg("aruz", tau)
    pw, phh, cy = 480, 700, 960
    for j, (img, label, lit, foc, win) in enumerate(ARUZ_PANELS):
        p_in = ease_out_back(prog(tau, 0.1 + j * .15, 0.55 + j * .15), 1.3)
        if p_in <= 0: continue
        active = foc <= tau < (ARUZ_PANELS[j + 1][3] if j + 1 < len(ARUZ_PANELS) else 99)
        zoom = 1.2 + 0.15 * ease_in_out(prog(tau, foc, foc + 1.5))
        crop = camera_crop(A[img], .5, .58, zoom, pw, phh)
        if tau >= 2.5 and not active:
            crop = Image.blend(crop.convert("RGB"), Image.new("RGB", crop.size, (10, 20, 40)), .45)
        card = rounded_card(crop, 30, 8 if not active else 12)
        if active:
            card = rounded_card(crop, 30, 12)
            d = ImageDraw.Draw(card)
            d.rounded_rectangle((0, 0, card.width - 21, card.height - 21), 42, outline=YELLOW, width=12)
        sc = (0.6 + 0.4 * p_in) * (1.06 if active else 1.0)
        x = 285 + j * 510
        paste_scaled(frame, card, x, cy, sc, rot=(-3 if j == 0 else 3), alpha=clamp(p_in * 1.5))
        paste_scaled(frame, text_sticker(label, 34, fg=NAVY, bg=WHITE, pad=(18, 8), radius=14, fpath=FONT_XB),
                     x, cy - phh / 2 + 10, alpha=clamp(p_in))
        if tau >= win[0]:
            v = count_val(lit, tau, win)
            bump = 1 + .2 * math.exp(-(tau - win[1]) * 10) if tau >= win[1] else 1
            paste_scaled(frame, liter_badge(f"{v}L", 120), x, cy + phh / 2 - 20, bump * pop(tau, win[0], .25))
    # arrow between
    if tau >= 5.3:
        paste_scaled(frame, emoji("➡️", 90), W / 2, 1330, pop(tau, 5.3) * (1 + .1 * math.sin(tau * 10)))
    tag = text_sticker("● " + ("WIDE" if tau < 2.5 else "CLOSE-UP" if tau < 6.5 else "SIDE ANGLE"), 26, fg=WHITE,
                       bg=(0, 0, 0, 150), pad=(16, 8), radius=14, shadow=False, fpath=FONT_B)
    header_and_sub(frame, cfg, tau)
    return frame

def scene_car(key, tau):
    if key == "aruz":
        return scene_aruz(tau)
    cfg = CARS[key]
    frame = blur_bg(key, tau)
    cx, cy, zoom, rot = interp_cam(cfg["cam"], tau)
    zoom *= 1 + 0.015 * math.sin(tau * 1.3)
    crop = camera_crop(A[key], cx, cy, zoom, CARD_W, CARD_H)
    card = rounded_card(crop)
    p_in = ease_out_back(prog(tau, 0.0, 0.45), 1.3)
    paste_scaled(frame, card, W / 2, CARD_CY, scale=0.6 + 0.4 * p_in, rot=rot, alpha=clamp(p_in * 1.5))
    shot = "WIDE" if tau < 2.5 else ("CLOSE-UP" if tau < 6.5 else "SIDE ANGLE")
    tag = text_sticker("● " + shot, 26, fg=WHITE, bg=(0, 0, 0, 150), pad=(16, 8), radius=14, shadow=False, fpath=FONT_B)
    # liter count-up
    win = cfg["count"]
    if tau >= win[0]:
        vals = [count_val(v, tau, win) for v in cfg["liters"]]
        txt = " - ".join(str(v) for v in vals) + "L"
        bump = 1 + .2 * math.exp(-(tau - win[1]) * 10) if tau >= win[1] else 1
        lab = text_sticker("RUANG BOOT", 34, fg=WHITE, bg=RED, pad=(18, 8), radius=14)
        y = CARD_CY + CARD_H / 2 - 40
        paste_scaled(frame, lab, W / 2, y - 95, pop(tau, win[0], .25))
        paste_scaled(frame, liter_badge(txt, 140 if len(cfg["liters"]) == 1 else 118), W / 2, y,
                     bump * pop(tau, win[0], .25))
    header_and_sub(frame, cfg, tau)
    return frame

# ---------------------------------------------------------------- scene 1 hook
HOOK_LAND = [0.5, 1.0, 1.5, 2.0, 2.5]
HOOK_POS = [(270, 1600), (810, 1600), (540, 1600), (400, 1235), (690, 1195)]

def scene_hook(t):
    base = A["sunset"].copy()
    road_dashes(base, t)
    for i, (bag, (x, by), tl) in enumerate(zip(A["big_bags"], HOOK_POS, HOOK_LAND)):
        draw_drop(base, bag, x, by, t, tl, fall=900)
    # wobble of the stack after all landed
    # shocked emoji
    s = pop(t, 2.75, .3)
    if s:
        paste_scaled(base, emoji("😱", 200), 900, 960, s * (1 + .05 * math.sin(t * 25)), rot=12)
        paste_scaled(base, emoji("😱", 140), 160, 1000, s * (1 + .05 * math.sin(t * 25 + 1)), rot=-14)
    # camera: close-up on bags -> medium
    zp = ease_in_out(prog(t, 1.8, 2.6))
    zoom = lerp(1.55, 1.04, zp)
    shake = 0
    for tl in HOOK_LAND:
        if t >= tl: shake += 14 * math.exp(-(t - tl) * 14) * math.sin((t - tl) * 70)
    focus_y = lerp(1330, H / 2, zp)
    cw, ch = W / zoom, H / zoom
    x0 = clamp((W - cw) / 2 + shake, 0, W - cw)
    y0 = clamp(focus_y - ch / 2, 0, H - ch)
    frame = base.resize((W, H), Image.BICUBIC, box=(max(0, x0), max(0, y0), min(W, x0 + cw), min(H, y0 + ch)))
    # text
    lines = [("BALIK KAMPUNG NANTI,", 0.25, WHITE, 74), ("BEG BANYAK…", 1.15, YELLOW, 120), ("KERETA MUAT", 2.1, WHITE, 112), ("KE TAK?", 2.35, YELLOW, 150)]
    ys = [330, 460, 600, 750]
    for (txt, t0, col, sz), y in zip(lines, ys):
        s = pop(t, t0, .3)
        if s: paste_scaled(frame, outlined_text(txt, sz, fg=col, stroke_w=12), W / 2, y, s, rot=-2 if col == YELLOW else 0)
    return frame

# ---------------------------------------------------------------- scene 5 engagement
MONT = ["aruz", "ativa", "bezza"]
NAMES = {"aruz": "ARUZ", "ativa": "ATIVA", "bezza": "BEZZA"}
FULL_CAM = {"aruz": (.5, .62), "ativa": (.5, .6), "bezza": (.47, .66)}

def scene_engage(tau):
    if tau < 2.0:
        i = int(tau / 0.333) % 3
        k = MONT[i]
        lt = tau % 0.333
        frame = A[k + "_bg"].copy()
        cx, cy = FULL_CAM[k]
        img = camera_crop(A[k], cx, cy, 1.0 + 0.25 * lt / .333, 1000, 1300)
        paste_scaled(frame, rounded_card(img), W / 2, 960, 1.0)
        lbl = outlined_text(NAMES[k], 190, fg=YELLOW, stroke_w=14)
        paste_scaled(frame, lbl, W / 2, 1500, 1 + .3 * math.exp(-lt * 15), rot=-4)
        # flash
        if lt < 0.05:
            frame = Image.blend(frame, Image.new("RGBA", (W, H), WHITE), 0.5)
        return frame
    frame = Image.new("RGBA", (W, H), NAVY)
    # stripes
    d = ImageDraw.Draw(frame)
    off = (tau * 120) % 160
    for x in range(-H, W + 160, 160):
        d.polygon([(x + off, 0), (x + off + 60, 0), (x + off + 60 + H, H), (x + off + H, H)], fill=(20, 40, 75))
    s = pop(tau, 2.0)
    paste_scaled(frame, outlined_text("SO, WHICH ONE", 100, fg=WHITE, stroke_w=10, stroke_c=(0, 0, 0)), W / 2, 300, s)
    paste_scaled(frame, outlined_text("IS YOUR PICK?", 118, fg=YELLOW, stroke_w=10, stroke_c=(0, 0, 0)), W / 2, 425, pop(tau, 2.15), rot=-3)
    ys = [720, 1060, 1400]
    for j, k in enumerate(MONT):
        p = ease_out_back(prog(tau, 2.25 + j * .12, 2.65 + j * .12), 1.4)
        if p <= 0: continue
        img = camera_crop(A[k], *FULL_CAM[k], 1.1, 640, 300)
        c = rounded_card(img, 26, 6)
        x = W / 2 - 110 + (1 - p) * (-900 if j % 2 == 0 else 900)
        paste_scaled(frame, c, x, ys[j])
        paste_scaled(frame, text_sticker(NAMES[k], 58, fg=NAVY, bg=YELLOW, pad=(22, 10)), x + 390, ys[j] - 90, rot=6)
        # pointing hand
        sel = int(max(0, tau - 3.4) / 0.45) % 3 if tau >= 3.4 else -1
        if sel == j:
            paste_scaled(frame, emoji("👈", 150), x + 440, ys[j] + 50, 1 + .08 * math.sin(tau * 18))
    s = pop(tau, 3.0)
    if s: paste_scaled(frame, text_sticker("ARUZ, ATIVA ATAU BEZZA?", 62, fg=NAVY, bg=YELLOW, pad=(30, 16)), W / 2, 1640, s)
    return frame

# ---------------------------------------------------------------- scene 6 closing
def scene_close(tau):
    frame = A["sunset"].copy()
    road_dashes(frame, 36 + tau)
    ov = Image.new("RGBA", (W, H), (10, 20, 40, 90))
    frame.alpha_composite(ov)
    p = pop(tau, 0.05)
    paste_scaled(frame, outlined_text("JOM PILIH KERETA", 96, fg=WHITE, stroke_w=11), W / 2, 330, p)
    paste_scaled(frame, outlined_text("UNTUK BALIK KAMPUNG!", 84, fg=YELLOW, stroke_w=11), W / 2, 445, pop(tau, 0.2), rot=-2)
    # three cars in a row (wide closing)
    for j, k in enumerate(MONT):
        q = ease_out_back(prog(tau, 0.3 + j * .12, 0.75 + j * .12), 1.5)
        if q <= 0: continue
        img = camera_crop(A[k], *FULL_CAM[k], 1.0, 320, 400)
        c = rounded_card(img, 22, 6)
        x = 190 + j * 350
        paste_scaled(frame, c, x, 820 + (1 - q) * 300 + 6 * math.sin(tau * 3 + j), alpha=clamp(q))
        paste_scaled(frame, text_sticker(NAMES[k], 44, fg=NAVY, bg=YELLOW, pad=(18, 8), radius=14), x, 1045 + (1 - q) * 300, alpha=clamp(q))
    s = pop(tau, 1.0, .4)
    if s:
        brand = Image.new("RGBA", (860, 230), (0, 0, 0, 0))
        bd = ImageDraw.Draw(brand)
        bd.rounded_rectangle((10, 14, 859, 229), 40, fill=(0, 0, 0, 110))
        bd.rounded_rectangle((0, 0, 849, 215), 40, fill=WHITE)
        bd.text((425, 75), "PERODUA", font=font(FONT_XB, 104), fill=NAVY, anchor="mm")
        bd.rounded_rectangle((235, 132, 615, 196), 20, fill=RED)
        bd.text((425, 165), "DUNGUN", font=font(FONT_XB, 50), fill=WHITE, anchor="mm")
        paste_scaled(frame, brand, W / 2, 1250, s)
    s = pop(tau, 1.5)
    if s:
        st = text_sticker("Hubungi kami untuk maklumat lanjut", 46, fg=NAVY, bg=YELLOW, pad=(84, 18), radius=40, fpath=FONT_B)
        st.alpha_composite(emoji("📞", 50), (22, (st.height - 12 - 50) // 2))
        paste_scaled(frame, st, W / 2, 1445, s * (1 + 0.03 * math.sin(tau * 6)))
    return frame

# ---------------------------------------------------------------- timeline
SCENES = [
    (0.0, 4.0, lambda t: scene_hook(t)),
    (4.0, 13.0, lambda t: scene_car("aruz", t - 4.0)),
    (13.0, 22.0, lambda t: scene_car("ativa", t - 13.0)),
    (22.0, 31.0, lambda t: scene_car("bezza", t - 22.0)),
    (31.0, 36.0, lambda t: scene_engage(t - 31.0)),
    (36.0, 40.0, lambda t: scene_close(t - 36.0)),
]
TRANS = 0.3

def scene_at(t):
    for a, b, f in SCENES:
        if a <= t < b: return a, f
    return SCENES[-1][0], SCENES[-1][2]

def hblur(im, amount):
    if amount < 2: return im
    arr = np.asarray(im).astype(np.float32)
    n = 6
    acc = np.zeros_like(arr)
    for i in range(n):
        acc += np.roll(arr, int(amount * (i / (n - 1) - .5)), axis=1)
    return Image.fromarray((acc / n).astype(np.uint8), "RGBA")

def render(t):
    a, f = scene_at(t)
    cur = f(t)
    if a > 0 and t < a + TRANS:  # whip-pan transition from previous scene
        pa, pf = scene_at(a - 1e-3)
        prev = pf(a - 1e-3)
        p = ease_in_out((t - a) / TRANS)
        off = int(W * p)
        out = Image.new("RGBA", (W, H), NAVY)
        out.alpha_composite(prev, (-off, 0)) if off < W else None
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.paste(cur, (W - off, 0))
        if off < W:
            out.paste(prev.crop((off, 0, W, H)), (0, 0))
        blur = 160 * math.sin(math.pi * p)
        cur = hblur(out, blur)
    return cur.convert("RGB")

def work(i):
    init()
    return render(i / FPS).tobytes()

# ---------------------------------------------------------------- audio
SR = 44100
BPM = 120
BEAT = 60 / BPM

def synth_audio(path):
    """Lagu raya ORIGINAL: kompang + gendang + akordion + bass. 120 BPM."""
    n = int(SR * DUR)
    out = np.zeros(n)
    rng = np.random.default_rng(11)
    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        if i >= n or i < 0: return
        j = min(n, i + len(sig)); out[i:j] += sig[: j - i] * gain
    tt = lambda d: np.arange(int(d * SR)) / SR
    noise = lambda d: rng.standard_normal(int(d * SR))
    def hp(x): return x - np.concatenate([[0], x[:-1]])
    def lp(x, a):
        y = np.empty_like(x); s = 0.0; b = 1 - a
        for i in range(len(x)):
            s = a * s + b * x[i]; y[i] = s
        return y
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    # --- instruments (pre-rendered)
    t = tt(.12)
    KP = (hp(noise(.12)) * .6 + np.sin(2 * np.pi * 420 * t) * .8) * np.exp(-t * 38)          # kompang "pak"
    t = tt(.3)
    KB = (np.sin(2 * np.pi * np.cumsum(110 + 60 * np.exp(-t * 30)) / SR) + lp(noise(.3), .8) * .3) * np.exp(-t * 11)  # kompang "bung"
    t = tt(.45)
    GD = np.sin(2 * np.pi * np.cumsum(70 + 70 * np.exp(-t * 25)) / SR) * np.exp(-t * 7)         # gendang low
    t = tt(.05)
    SH = hp(hp(noise(.05))) * np.exp(-t * 70) * .3                                              # shaker
    def accordion(m, d):
        t = tt(d + .05); f = hz(m)
        vib = 1 + .004 * np.sin(2 * np.pi * 5.5 * t)
        ph = np.cumsum(f * vib) / SR
        s = (2 * (ph % 1) - 1) * .5 + (2 * ((ph * 1.004) % 1) - 1) * .5 + np.sign(np.sin(2 * np.pi * ph * .5)) * .25
        env = np.minimum(1, t / .02) * np.where(t > d, np.exp(-(t - d) * 40), 1) * (1 + .15 * np.sin(2 * np.pi * 6 * t))
        return lp(s, .55) * env
    def chord_pad(ms, d):
        return sum(accordion(m, d) for m in ms) / len(ms)
    def bass(m, d=.22):
        t = tt(d); f = hz(m)
        return lp(np.sin(2 * np.pi * f * t) + .25 * np.sign(np.sin(2 * np.pi * f * t)), .6) * np.minimum(1, t * 300) * np.exp(-t * 5)
    def thud():
        t = tt(.3); f = 60 + 90 * np.exp(-t * 25)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
    def ding(f=1568):
        t = tt(.5); return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2.01 * t)) * np.exp(-t * 8) * .35
    def tick():
        t = tt(.03); return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 150) * .25
    def whoosh(d=.45):
        t = tt(d); env = np.sin(np.pi * t / d) ** 2
        return lp(noise(d), .9) * env * 3
    def riser(d=.9):
        t = tt(d); return hp(noise(d)) * (t / d) ** 2 * .3
    def impact():
        t = tt(1.2)
        return np.sin(2 * np.pi * np.cumsum(40 + 80 * np.exp(-t * 12)) / SR) * np.exp(-t * 3) + lp(noise(1.2), .95) * np.exp(-t * 5) * 1.5

    # --- original melody (eighth notes, None = rest), chords C G Am F
    CH = [[60, 64, 67], [59, 62, 67], [60, 64, 69], [60, 65, 69]]
    RT = [48, 43, 45, 41]
    MEL = [
        [72, 74, 76, 79, 76, 74, 72, None], [74, 76, 77, 79, 77, 76, 74, None],
        [76, 79, 81, 79, 76, 74, 76, None], [77, 76, 74, 72, 74, 72, 69, None],
        [79, None, 79, 81, 79, 76, 74, 72], [74, None, 74, 76, 74, 71, 67, None],
        [72, 74, 76, None, 76, 77, 79, None], [81, 79, 77, 76, 74, None, 72, 72],
    ]
    E = BEAT / 2
    PAUSE = (33.0, 34.0)
    nbars = int(DUR / (4 * BEAT)) + 1
    for bar in range(nbars):
        bt = bar * 4 * BEAT
        ci = bar % 4
        for k in range(8):  # eighth grid
            t0 = bt + k * E
            if PAUSE[0] - .01 <= t0 < PAUSE[1] or t0 >= 39.5: continue
            # kompang pattern: bung on beats 1 & 3, pak interlocking
            if k in (0, 4): add(KB, t0, .7)
            if k in (1, 3, 5, 6, 7): add(KP, t0, .45 if k % 2 else .3)
            if k in (0, 3, 6): add(GD, t0, .55)
            add(SH, t0 + E / 2, .6)
            # bass joget pattern
            if k in (0, 3, 4, 6): add(bass(RT[ci] + (7 if k == 6 else 0)), t0, .5)
            # chord stabs (accordion) on off-beats
            if k in (1, 3, 5, 7): add(chord_pad(CH[ci], .16), t0, .22)
            # melody (intro 0-4s quieter, full after)
            m = MEL[bar % 8][k]
            if m is not None and t0 >= 0:
                dur = E * (2 if (k + 1 < 8 and MEL[bar % 8][k + 1] is None) else 1) * .92
                add(accordion(m, dur), t0, .32 if t0 >= 4 else .2)
    # --- sfx
    for tl in HOOK_LAND: add(thud(), tl, .8)
    add(ding(1318), 2.75, .6); add(ding(1760), 2.85, .6)
    windows = [(4 + w[0], 4 + w[1]) for *_, w in ARUZ_PANELS] + [(13 + CARS["ativa"]["count"][0], 13 + CARS["ativa"]["count"][1]),
                                                                (22 + CARS["bezza"]["count"][0], 22 + CARS["bezza"]["count"][1])]
    for a, b in windows:
        add(thud(), a, .6)
        x = a
        while x < b:
            add(tick(), x, 1.0); x += .07
        add(ding(2093), b, .9)
    for a in (4, 13, 22, 31, 36):
        add(riser(), a - .9, .8); add(whoosh(), a - .1, .8)
    add(impact(), 34.0, .8); add(impact(), 36.0, .6)
    t = tt(2.5)
    add(sum(accordion(m, 1.8)[: len(t)] if len(accordion(m, 1.8)) >= len(t) else np.pad(accordion(m, 1.8), (0, len(t) - len(accordion(m, 1.8)))) for m in [60, 64, 67, 72]) * .3, 38.0)
    out = np.tanh(out * 1.3)
    fade = np.ones(n); fl = int(.6 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    out *= fade
    out = out / np.max(np.abs(out)) * .9
    st = np.stack([out, out], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

# ---------------------------------------------------------------- main
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        init()
        for ts in sys.argv[2:]:
            render(float(ts)).save(os.path.join(HERE, f"preview_{ts}.jpg"), quality=85)
        sys.exit()
    synth_audio(os.path.join(HERE, "music_raya.wav"))
    print("audio ok", flush=True)
    nframes = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", os.path.join(HERE, "music_raya.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           os.path.join(HERE, "Perodua_Dungun_Balik_Kampung_Raya.mp4")], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, buf in enumerate(pool.imap(work, range(nframes), chunksize=4)):
            ff.stdin.write(buf)
            if i % 150 == 0: print(f"frame {i}/{nframes}", flush=True)
    ff.stdin.close(); ff.wait()
    print("done")
