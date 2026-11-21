"""Video 40s 9:16 - TAK PASTI BERAPA PREMIUM INSURANS? (SA cinematic animation)
Render: python3 insurans.py   |  preview: python3 insurans.py preview 3 10 ...
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool
from render import (W, H, FPS, font, FONT_XB, FONT_B, FONT_SB, YELLOW, NAVY, WHITE, RED, clamp, prog, lerp,
                    ease_out_cubic, ease_in_out, ease_out_back, pop, emoji, paste_scaled, text_sticker,
                    outlined_text, rounded_card, check_icon)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 40.0
TEAL = (0, 170, 160)
GOLD = (255, 196, 60)
SKIN = (214, 160, 120)
SKIN_D = (180, 125, 90)

# ------------------------------------------------------------ text helpers
def wrap(text, size, maxw, fpath=FONT_XB):
    f = font(fpath, size)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) <= maxw: cur = test
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

_wc = {}
def word_img(w, size, col, sw, sc, fpath):
    k = (w, size, col, sw, sc, fpath)
    if k not in _wc:
        f = font(fpath, size)
        d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        tw = d0.textlength(w, font=f)
        im = Image.new("RGBA", (int(tw + 2 * sw + 10), int(size * 1.5 + 2 * sw)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((sw + 5, sw + size * 1.15), w, font=f, fill=col, anchor="ls", stroke_width=sw, stroke_fill=sc)
        _wc[k] = im
    return _wc[k]

def kinetic(frame, text, t, t0, y, size=72, fg=WHITE, maxw=940, stroke=NAVY, gap=1.18, per_word=.07, fpath=FONT_XB, hl=()):
    """word-by-word reveal; words in hl get YELLOW."""
    if t < t0: return y
    lines = wrap(text, size, maxw, fpath)
    f = font(fpath, size)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    k = 0
    for ln in lines:
        words = ln.split()
        widths = [d0.textlength(w + " ", font=f) for w in words]
        x = W / 2 - sum(widths) / 2
        for w, ww in zip(words, widths):
            p = prog(t, t0 + k * per_word, t0 + k * per_word + .3)
            if p > 0:
                col = YELLOW if w.strip("?!,.").upper() in hl else fg
                im = word_img(w, size, col, max(6, size // 9), stroke, fpath)
                paste_scaled(frame, im, x + ww / 2 - size * .12, y + (1 - ease_out_cubic(p)) * 40, alpha=p)
            x += ww; k += 1
        y += size * gap
    return y

# ------------------------------------------------------------ cinematic background
rng = np.random.default_rng(3)
BOKEH = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 60), rng.uniform(.2, 1), rng.uniform(-20, 20), rng.uniform(-40, -10))
         for _ in range(45)]

def gradient(top, bot):
    y = np.linspace(0, 1, H)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - y) + np.array(bot)[None, None, :] * y
    return Image.fromarray(np.repeat(arr, W, axis=1).astype(np.uint8)).convert("RGBA")

G = {}
def init():
    if G: return
    G["night"] = gradient((8, 12, 35), (40, 20, 60))
    G["dawn"] = gradient((10, 40, 80), (0, 120, 140))
    G["warm"] = gradient((60, 15, 30), (200, 60, 40))
    G["brand"] = gradient((5, 20, 45), (0, 90, 110))
    v = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .7)) ** 2)
    vig = (np.clip(r - .55, 0, 1) * 260).clip(0, 160).astype(np.uint8)
    G["vig"] = Image.fromarray(np.dstack([np.zeros_like(vig)] * 3 + [vig]), "RGBA")
    G["grain"] = []
    for i in range(6):
        n = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        g = Image.fromarray(n).resize((W, H))
        a = Image.fromarray((np.full((H // 2, W // 2), 18)).astype(np.uint8)).resize((W, H))
        im = Image.merge("RGBA", (g, g, g, a)); G["grain"].append(im)
    G["car"] = draw_car((220, 30, 45))
    G["doc"] = draw_doc()

def bokeh_layer(frame, t, tint=(255, 220, 150)):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x, y, r, a, vx, vy in BOKEH:
        px, py = (x + vx * t) % W, (y + vy * t) % H
        al = int(70 * a * (0.6 + 0.4 * math.sin(t * 1.5 + x)))
        d.ellipse((px - r, py - r, px + r, py + r), fill=tint + (al,))
    frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))

def light_rays(frame, t, cx=W / 2, cy=-200, col=(255, 230, 180)):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(7):
        a = math.radians(70 + i * 7 + 4 * math.sin(t * .5 + i))
        L = 2600
        w = math.radians(1.6)
        pts = [(cx, cy), (cx + L * math.cos(a - w), cy + L * math.sin(a - w)), (cx + L * math.cos(a + w), cy + L * math.sin(a + w))]
        d.polygon(pts, fill=col + (22,))
    frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(18)))

def finish(frame, t):
    frame.alpha_composite(G["vig"])
    frame.alpha_composite(G["grain"][int(t * FPS) % len(G["grain"])])
    # cinematic letterbox
    d = ImageDraw.Draw(frame)
    d.rectangle((0, 0, W, 70), fill=(0, 0, 0)); d.rectangle((0, H - 70, W, H), fill=(0, 0, 0))
    return frame

# ------------------------------------------------------------ illustrations
def draw_car(col):
    S = 2; w, h = 900 * S, 380 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    dark = tuple(int(c * .6) for c in col)
    body = [(40, 260), (60, 190), (170, 170), (290, 80), (560, 70), (720, 150), (860, 175), (880, 260), (860, 300), (40, 300)]
    d.polygon([(x * S, y * S) for x, y in body], fill=col)
    d.rounded_rectangle((30 * S, 240 * S, 890 * S, 305 * S), 30 * S, fill=col)
    d.polygon([(x * S, y * S) for x, y in [(305, 95), (450, 90), (450, 165), (210, 170)]], fill=(40, 60, 90))
    d.polygon([(x * S, y * S) for x, y in [(470, 90), (560, 88), (690, 160), (470, 165)]], fill=(40, 60, 90))
    d.line([(320 * S, 100 * S), (260 * S, 160 * S)], fill=(120, 150, 190), width=8 * S)
    d.line([(40 * S, 230 * S), (880 * S, 230 * S)], fill=dark, width=5 * S)
    d.rounded_rectangle((835 * S, 190 * S, 880 * S, 215 * S), 8 * S, fill=(255, 240, 180))
    d.rounded_rectangle((35 * S, 200 * S, 70 * S, 225 * S), 8 * S, fill=(255, 60, 60))
    for cx in (210, 700):
        d.ellipse(((cx - 75) * S, (230) * S, (cx + 75) * S, (380) * S), fill=(25, 25, 30))
        d.ellipse(((cx - 40) * S, (265) * S, (cx + 40) * S, (345) * S), fill=(190, 190, 200))
    return im.resize((w // S, h // S), Image.LANCZOS)

def draw_doc():
    w, h = 560, 720
    im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((14, 18, w + 13, h + 17), 30, fill=(0, 0, 0, 120))
    d.rounded_rectangle((0, 0, w - 1, h - 1), 30, fill=(250, 250, 245))
    d.rounded_rectangle((0, 0, w - 1, 150), 30, fill=NAVY); d.rectangle((0, 110, w - 1, 150), fill=NAVY)
    d.text((w / 2, 78), "POLISI INSURANS", font=font(FONT_XB, 44), fill=WHITE, anchor="mm")
    # shield
    sx, sy = w / 2, 260
    d.polygon([(sx, sy - 80), (sx + 70, sy - 50), (sx + 60, sy + 40), (sx, sy + 85), (sx - 60, sy + 40), (sx - 70, sy - 50)], fill=TEAL)
    d.line([(sx - 28, sy), (sx - 5, sy + 25), (sx + 32, sy - 22)], fill=WHITE, width=12, joint="curve")
    for i, (lab, val) in enumerate([("Kenderaan", "PERODUA"), ("Perlindungan", "Komprehensif"), ("Tarikh Tamat", "?? / ?? / ????")]):
        y = 400 + i * 85
        d.text((50, y), lab, font=font(FONT_SB, 28), fill=(120, 120, 130))
        d.text((50, y + 34), val, font=font(FONT_XB, 34), fill=NAVY if i < 2 else RED)
    return im

def stamp(text="HAMPIR TAMAT"):
    f = font(FONT_XB, 62)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tw = d0.textlength(text, font=f)
    im = Image.new("RGBA", (int(tw + 70), 130), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, im.width - 5, im.height - 5), 18, outline=RED + (230,), width=9)
    d.text((im.width / 2, im.height / 2), text, font=f, fill=RED + (230,), anchor="mm")
    return im

def draw_sa(t, wave_arm=False, phone=False, point=False, mouth=1.0, scale=1.0):
    """Flat illustrated Sales Advisor. Returns RGBA approx 520x1000."""
    S = 2
    w, h = 520 * S, 1000 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = lambda *v: [x * S for x in v]
    bob = 6 * math.sin(t * 3)
    cx = 260
    # legs
    d.rounded_rectangle(s(cx - 85, 640, cx - 10, 960), 30 * S, fill=(25, 25, 32))
    d.rounded_rectangle(s(cx + 10, 640, cx + 85, 960), 30 * S, fill=(25, 25, 32))
    for x0 in (cx - 100, cx + 5):
        d.rounded_rectangle(s(x0, 940, x0 + 100, 990), 20 * S, fill=(15, 15, 18))
        d.line(s(x0 + 20, 958, x0 + 80, 972), fill=(240, 240, 240), width=6 * S)
    # torso (jersey white/black/red)
    y0 = 340 + bob
    d.rounded_rectangle(s(cx - 140, y0, cx + 140, 680), 70 * S, fill=WHITE)
    d.polygon(s(cx - 140, y0 + 200, cx + 140, y0 + 120, cx + 140, 680, cx - 140, 680), fill=(30, 30, 38))
    d.polygon(s(cx - 140, y0 + 175, cx + 140, y0 + 95, cx + 140, y0 + 125, cx - 140, y0 + 205), fill=RED)
    d.rectangle(s(cx - 140, 640, cx + 140, 680), fill=(25, 25, 32))
    # collar + lanyard + ID
    d.polygon(s(cx - 50, y0, cx, y0 + 50, cx + 50, y0), fill=(30, 30, 38))
    d.line(s(cx - 40, y0 + 5, cx - 5, y0 + 170), fill=(30, 140, 90), width=8 * S)
    d.line(s(cx + 40, y0 + 5, cx + 5, y0 + 170), fill=(30, 140, 90), width=8 * S)
    d.rounded_rectangle(s(cx - 40, y0 + 165, cx + 40, y0 + 265), 10 * S, fill=(170, 230, 120))
    d.rectangle(s(cx - 28, y0 + 185, cx + 28, y0 + 215), fill=WHITE)
    d.text(((cx) * S, (y0 + 240) * S), "SA", font=font(FONT_XB, 34 * S), fill=NAVY, anchor="mm")
    # arms
    def arm(sx, sy, a1, a2, hand_extra=None):
        L1, L2 = 150, 140
        ex, ey = sx + L1 * math.cos(a1), sy + L1 * math.sin(a1)
        hx, hy = ex + L2 * math.cos(a2), ey + L2 * math.sin(a2)
        d.line(s(sx, sy, ex, ey), fill=WHITE, width=56 * S)
        d.line(s(ex, ey, hx, hy), fill=SKIN, width=44 * S)
        d.ellipse(s(sx - 28, sy - 28, sx + 28, sy + 28), fill=WHITE)
        d.ellipse(s(ex - 22, ey - 22, ex + 22, ey + 22), fill=SKIN)
        d.ellipse(s(hx - 30, hy - 30, hx + 30, hy + 30), fill=SKIN)
        return hx, hy
    # left arm (viewer's left)
    if point:
        arm(cx - 120, y0 + 50, math.radians(200), math.radians(195 + 4 * math.sin(t * 8)))
    else:
        arm(cx - 120, y0 + 50, math.radians(110), math.radians(95))
    # right arm
    if wave_arm:
        a = math.radians(-60 + 25 * math.sin(t * 10))
        arm(cx + 120, y0 + 50, math.radians(-20), a)
    elif phone:
        hx, hy = arm(cx + 120, y0 + 50, math.radians(80), math.radians(-115))
        d.rounded_rectangle(s(hx - 28, hy - 70, hx + 22, hy + 20), 10 * S, fill=(20, 20, 25))
        d.rounded_rectangle(s(hx - 22, hy - 62, hx + 16, hy + 10), 6 * S, fill=(80, 200, 255))
    else:
        arm(cx + 120, y0 + 50, math.radians(70), math.radians(85))
    # head
    hy = 210 + bob
    d.rectangle(s(cx - 35, hy + 90, cx + 35, y0 + 20), fill=SKIN_D)
    d.ellipse(s(cx - 120, hy - 130, cx + 120, hy + 130), fill=SKIN)
    d.ellipse(s(cx - 140, hy - 20, cx - 100, hy + 40), fill=SKIN_D); d.ellipse(s(cx + 100, hy - 20, cx + 140, hy + 40), fill=SKIN_D)
    # hair (fade style)
    d.chord(s(cx - 125, hy - 150, cx + 125, hy + 40), 180, 360, fill=(20, 20, 24))
    d.polygon(s(cx - 125, hy - 55, cx - 60, hy - 120, cx + 130, hy - 70, cx + 120, hy - 30, cx - 120, hy - 20), fill=(20, 20, 24))
    # eyes (blink)
    blink = (t % 3.2) < .12
    for ex in (cx - 45, cx + 45):
        if blink: d.line(s(ex - 18, hy + 5, ex + 18, hy + 5), fill=(20, 20, 24), width=6 * S)
        else:
            d.ellipse(s(ex - 16, hy - 12, ex + 16, hy + 20), fill=WHITE)
            d.ellipse(s(ex - 9, hy - 4, ex + 9, hy + 14), fill=(30, 20, 15))
        d.line(s(ex - 22, hy - 32, ex + 20, hy - 36), fill=(20, 20, 24), width=7 * S)
    # mouth: talk animation
    mo = mouth * (0.5 + 0.5 * abs(math.sin(t * 11)))
    d.chord(s(cx - 30, hy + 45, cx + 30, hy + 62 + 22 * mo), 0, 180, fill=(120, 30, 40))
    d.chord(s(cx - 22, hy + 45, cx + 22, hy + 56), 0, 180, fill=WHITE)
    out = im.resize((int(w / S * scale), int(h / S * scale)), Image.LANCZOS)
    return out

def bubble(text, size=46, maxw=640):
    lines = wrap(text, size, maxw, FONT_B)
    f = font(FONT_B, size)
    lh = size * 1.25
    bw = maxw + 80; bh = int(len(lines) * lh + 70)
    im = Image.new("RGBA", (bw + 20, bh + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 14, bw + 11, bh + 13), 40, fill=(0, 0, 0, 100))
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), 40, fill=WHITE)
    d.polygon([(90, bh - 5), (170, bh - 5), (70, bh + 60)], fill=WHITE)
    for i, ln in enumerate(lines):
        d.text((bw / 2, 35 + i * lh + lh / 2), ln, font=f, fill=NAVY, anchor="mm")
    return im

# ------------------------------------------------------------ scenes
def scene1(t):  # 0-7 hook
    f = G["night"].copy()
    light_rays(f, t, col=(255, 120, 120))
    bokeh_layer(f, t, (255, 140, 140))
    # car slow push-in
    z = 1 + .05 * t / 7
    car_y = 1430
    paste_scaled(f, G["car"], W / 2 + 30 - t * 8, car_y, .95 * z * ease_out_cubic(prog(t, 0, .8)) + .001,
                 alpha=prog(t, 0, .6))
    # document floats in with stamp
    dp = ease_out_back(prog(t, .6, 1.2), 1.4)
    if dp > 0:
        paste_scaled(f, G["doc"], W / 2, 830 + 10 * math.sin(t * 2), .78 * dp, rot=-5 + 2 * math.sin(t))
    sp = prog(t, 1.8, 2.05)
    if sp > 0:
        sc = lerp(2.2, 1.0, ease_out_cubic(sp))
        paste_scaled(f, stamp(), W / 2 + 10, 900, sc * .9, rot=14, alpha=sp)
    # text
    kinetic(f, "Insurans kereta dah nak tamat?", t, .3, 230, 96, hl=("TAMAT",))
    # RM ??? glitch
    if t >= 3.4:
        q = pop(t, 3.4, .3)
        digits = "".join("0123456789"[int((t * 37 + i * 7) % 10)] for i in range(3)) if t < 4.6 else "???"
        im = outlined_text(f"RM {digits}", 130, fg=YELLOW, stroke_w=14)
        jx = 8 * math.sin(t * 60) if t < 4.6 else 0
        paste_scaled(f, im, W / 2 + jx, 1120, q * 1.0)
        paste_scaled(f, emoji("🤔", 130), W - 150, 1060, pop(t, 4.6), rot=10)
    if t >= 4.0:
        kinetic(f, "Tapi tak pasti berapa premium yang kena bayar nanti?", t, 4.0, 1600, 70, hl=("PREMIUM",), per_word=.06)
    return f

def scene2(t):  # 7-15 masalah -> reassurance
    f = G["dawn"].copy()
    light_rays(f, t, cx=W * .8, cy=-300, col=(200, 255, 240))
    bokeh_layer(f, t, (180, 255, 240))
    # dizzy question marks fly away
    for i in range(8):
        a = i / 8 * 2 * math.pi + t * 1.5
        r = 260 + 400 * ease_in_out(prog(t, 1.0, 2.2))
        al = 1 - prog(t, 1.4, 2.2)
        if al > 0:
            q = outlined_text("?", 90, fg=WHITE, stroke_w=8)
            paste_scaled(f, q, W / 2 + r * math.cos(a), 1000 + r * .6 * math.sin(a), 1, rot=math.degrees(a), alpha=al)
    # "JANGAN RISAU!"
    s = pop(t, .2, .4)
    if s:
        paste_scaled(f, outlined_text("JANGAN", 120, fg=WHITE, stroke_w=12), W / 2, 260, s, rot=-3)
        paste_scaled(f, outlined_text("RISAU!", 170, fg=YELLOW, stroke_w=14), W / 2, 410, pop(t, .35, .4), rot=-3)
    # SA character slides in
    p = ease_out_cubic(prog(t, .8, 1.6))
    sa = draw_sa(t, wave_arm=t < 3.5, mouth=1.0 if 2.0 < t < 7.2 else 0.15, scale=.95)
    paste_scaled(f, sa, lerp(-300, 320, p), 1330)
    # speech bubble
    b = ease_out_back(prog(t, 2.0, 2.4), 1.4)
    if b > 0:
        bb = bubble("Anda tak perlu pening-pening nak agak berapa kos insurans kereta.", 54, 580)
        paste_scaled(f, bb, 690, 820, b)
    # crossed dizzy emoji
    s2 = pop(t, 4.5)
    if s2:
        paste_scaled(f, emoji("😵‍💫", 140), 800, 1300, s2)
        lay = Image.new("RGBA", (220, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.ellipse((10, 10, 210, 210), outline=RED, width=16); d.line((40, 180, 180, 40), fill=RED, width=16)
        paste_scaled(f, lay, 800, 1300, s2)
    if t > 5.6:
        paste_scaled(f, text_sticker("KAMI BANTU!", 54, fg=NAVY, bg=YELLOW, pad=(30, 14)), 800, 1520, pop(t, 5.6), rot=-4)
    return f

FACTORS = [("🚗", "MODEL KERETA", "Jenis & model kenderaan"),
           ("🛡️", "NILAI PERLINDUNGAN", "Jumlah diinsuranskan"),
           ("⭐", "NCD", "No Claim Discount"),
           ("📋", "JENIS PERLINDUNGAN", "Komprehensif / pihak ketiga")]
FACT_T = [3.0, 5.2, 7.4, 9.6]

def factor_card(icon, title, sub, active):
    w, h = 900, 190
    im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 14, w + 11, h + 13), 36, fill=(0, 0, 0, 110))
    d.rounded_rectangle((0, 0, w - 1, h - 1), 36, fill=WHITE if active else (225, 232, 240))
    if active: d.rounded_rectangle((0, 0, w - 1, h - 1), 36, outline=YELLOW, width=8)
    d.ellipse((30, 30, 160, 160), fill=NAVY)
    e = emoji(icon, 80); im.alpha_composite(e, (95 - e.width // 2, 95 - e.height // 2))
    d.text((195, 62), title, font=font(FONT_XB, 54), fill=NAVY, anchor="lm")
    d.text((195, 128), sub, font=font(FONT_SB, 36), fill=(90, 100, 120), anchor="lm")
    return im

def scene3(t):  # 15-28 solusi
    f = G["brand"].copy()
    light_rays(f, t, col=(150, 230, 255))
    bokeh_layer(f, t, (150, 220, 255))
    s = pop(t, .2)
    if s:
        paste_scaled(f, outlined_text("SEBENARNYA,", 70, fg=WHITE, stroke_w=9), W / 2, 220, s)
    kinetic(f, "premium insurans bergantung pada beberapa faktor:", t, .6, 330, 62, hl=("PREMIUM", "FAKTOR:"), per_word=.06)
    for i, ((ic, ti, sub), t0) in enumerate(zip(FACTORS, FACT_T)):
        p = ease_out_back(prog(t, t0, t0 + .45), 1.3)
        if p <= 0: continue
        active = t0 <= t < (FACT_T[i + 1] if i + 1 < 4 else 11.8)
        card = factor_card(ic, ti, sub, active)
        x = W / 2 + (1 - p) * (1100 if i % 2 == 0 else -1100)
        paste_scaled(f, card, x, 640 + i * 235, 1.04 if active else 1.0)
        paste_scaled(f, text_sticker(str(i + 1), 44, fg=NAVY, bg=YELLOW, pad=(20, 6), radius=30), x - 440, 640 + i * 235 - 85, p)
    # result: premium meter
    if t >= 11.6:
        q = pop(t, 11.6, .35)
        st = text_sticker("= ANGGARAN PREMIUM ANDA", 54, fg=NAVY, bg=YELLOW, pad=(36, 18))
        paste_scaled(f, st, W / 2, 1640, q * (1 + .03 * math.sin(t * 8)))
    return f

def scene4(t):  # 28-40 CTA
    f = G["warm"].copy() if t < 6.5 else G["brand"].copy()
    light_rays(f, t, col=(255, 210, 160))
    bokeh_layer(f, t, (255, 210, 150))
    if t < 6.5:
        kinetic(f, "Nak tahu berapa anggaran premium insurans kereta anda?", t, .2, 230, 66, hl=("ANGGARAN", "PREMIUM"), per_word=.06)
        s = pop(t, 2.4)
        if s: paste_scaled(f, outlined_text("MUDAH SAHAJA!", 110, fg=YELLOW, stroke_w=12), W / 2, 640, s, rot=-3)
        sa = draw_sa(t, phone=True, mouth=1.0 if t > 2.5 else .2, scale=.9)
        paste_scaled(f, sa, 330, 1310)
        # phone call card
        c = ease_out_back(prog(t, 3.0, 3.4), 1.4)
        if c > 0:
            card = Image.new("RGBA", (520, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
            d.rounded_rectangle((10, 12, 519, 359), 40, fill=(0, 0, 0, 100))
            d.rounded_rectangle((0, 0, 509, 347), 40, fill=WHITE)
            d.text((255, 70), "HUBUNGI", font=font(FONT_B, 44), fill=(90, 100, 120), anchor="mm")
            d.text((255, 150), "PERODUA", font=font(FONT_XB, 72), fill=NAVY, anchor="mm")
            d.rounded_rectangle((115, 200, 395, 262), 18, fill=RED)
            d.text((255, 231), "DUNGUN", font=font(FONT_XB, 44), fill=WHITE, anchor="mm")
            d.text((255, 305), "hari ini", font=font(FONT_B, 40), fill=NAVY, anchor="mm")
            paste_scaled(f, card, 790, 1050, c * .95 * (1 + .02 * math.sin(t * 6)))
            paste_scaled(f, emoji("📞", 110), 600, 890, c * (1 + .12 * abs(math.sin(t * 12))), rot=-15 + 10 * math.sin(t * 20))
        if t > 4.6:
            paste_scaled(f, text_sticker("Kami sedia bantu semak untuk anda", 44, fg=NAVY, bg=YELLOW, pad=(28, 14), fpath=FONT_B),
                         W / 2, 1660, pop(t, 4.6))
        return f
    # 6.5-12: warning + brand end
    tt = t - 6.5
    # calendar warning
    cal = Image.new("RGBA", (420, 440), (0, 0, 0, 0)); d = ImageDraw.Draw(cal)
    d.rounded_rectangle((10, 14, 419, 439), 40, fill=(0, 0, 0, 110))
    d.rounded_rectangle((0, 0, 409, 425), 40, fill=WHITE)
    d.rounded_rectangle((0, 0, 409, 120), 40, fill=RED); d.rectangle((0, 80, 409, 120), fill=RED)
    d.text((205, 62), "TAMAT", font=font(FONT_XB, 60), fill=WHITE, anchor="mm")
    days = max(0, 7 - int(tt * 4)) if tt < 2.2 else 0
    d.text((205, 270), str(days), font=font(FONT_XB, 200), fill=NAVY, anchor="mm")
    d.text((205, 385), "HARI LAGI", font=font(FONT_B, 40), fill=(110, 110, 120), anchor="mm")
    paste_scaled(f, cal, W / 2, 620, ease_out_back(prog(tt, 0, .4), 1.4) * (1 + .03 * math.sin(tt * 10)),
                 rot=3 * math.sin(tt * 14) if 2.0 < tt < 2.6 else 0)
    kinetic(f, "Jangan tunggu sampai insurans tamat baru nak renew!", tt, .4, 1000, 74, hl=("JANGAN", "TAMAT", "RENEW!"), per_word=.07)
    b = pop(tt, 2.8, .4)
    if b:
        brand = Image.new("RGBA", (860, 230), (0, 0, 0, 0)); bd = ImageDraw.Draw(brand)
        bd.rounded_rectangle((10, 14, 859, 229), 40, fill=(0, 0, 0, 110))
        bd.rounded_rectangle((0, 0, 849, 215), 40, fill=WHITE)
        bd.text((425, 75), "PERODUA", font=font(FONT_XB, 104), fill=NAVY, anchor="mm")
        bd.rounded_rectangle((235, 132, 615, 196), 20, fill=RED)
        bd.text((425, 165), "DUNGUN", font=font(FONT_XB, 50), fill=WHITE, anchor="mm")
        paste_scaled(f, brand, W / 2, 1440, b)
    s = pop(tt, 3.3)
    if s:
        st = text_sticker("Hubungi kami untuk semakan premium", 44, fg=NAVY, bg=YELLOW, pad=(84, 18), radius=40, fpath=FONT_B)
        st.alpha_composite(emoji("📞", 50), (22, (st.height - 12 - 50) // 2))
        paste_scaled(f, st, W / 2, 1640, s * (1 + .03 * math.sin(tt * 6)))
    return f

SCENES = [(0, 7, scene1), (7, 15, scene2), (15, 28, scene3), (28, 40, scene4)]

def render(t):
    for a, b, fn in SCENES:
        if a <= t < b or (b == 40 and t >= a): break
    f = fn(t - a)
    # transition: zoom punch + white flash at scene start, fade from black at 0
    if a > 0 and t - a < .35:
        p = (t - a) / .35
        z = 1 + .12 * (1 - ease_out_cubic(p))
        f = f.resize((int(W * z), int(H * z)), Image.BILINEAR).crop((int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
        f = Image.blend(f, Image.new("RGBA", (W, H), WHITE), .6 * (1 - p))
    if t < .4: f = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), f, t / .4)
    if t > 39.5: f = Image.blend(f, Image.new("RGBA", (W, H), (0, 0, 0, 255)), (t - 39.5) / .5 * .0)
    return finish(f, t).convert("RGB")

def work(i):
    init(); return render(i / FPS).tobytes()

# ------------------------------------------------------------ cinematic music
SR = 44100
def synth(path):
    n = int(SR * DUR); out = np.zeros(n); r = np.random.default_rng(5)
    def add(sig, t0, g=1.0):
        i = int(t0 * SR)
        if i >= n or i < 0: return
        j = min(n, i + len(sig)); out[i:j] += sig[: j - i] * g
    tt = lambda d: np.arange(int(d * SR)) / SR
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    def lp(x, a):
        y = np.empty_like(x); s = 0.0
        for i in range(len(x)): s = a * s + (1 - a) * x[i]; y[i] = s
        return y
    def pad(ms, d):
        t = tt(d); s = sum(np.sin(2 * np.pi * hz(m) * t) + .5 * np.sin(2 * np.pi * hz(m) * 1.003 * t) + .25 * np.sin(2 * np.pi * hz(m + 12) * t) for m in ms)
        env = np.minimum(1, t / 1.0) * np.minimum(1, (d - t) / 1.0)
        return s / len(ms) * env
    def pluck(m, d=.4):
        t = tt(d); f = hz(m)
        return (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2 * f * t) + .1 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t * 7)
    def kick():
        t = tt(.4); return np.sin(2 * np.pi * np.cumsum(45 + 100 * np.exp(-t * 30)) / SR) * np.exp(-t * 8)
    def hat():
        t = tt(.04); x = r.standard_normal(len(t)); return (x - np.roll(x, 1)) * np.exp(-t * 90) * .15
    def boom():
        t = tt(3.0); return (np.sin(2 * np.pi * np.cumsum(32 + 60 * np.exp(-t * 6)) / SR) * np.exp(-t * 1.6)
                             + lp(r.standard_normal(len(t)), .97) * np.exp(-t * 3) * 2)
    def riser(d=1.5):
        t = tt(d); x = r.standard_normal(len(t)); x = x - np.roll(x, 1)
        return x * (t / d) ** 2.5 * .4 + np.sin(2 * np.pi * (200 + 1200 * (t / d) ** 2) * t) * (t / d) ** 2 * .2
    def ding(f=1568):
        t = tt(.6); return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2.01 * t)) * np.exp(-t * 7) * .3
    def tick():
        t = tt(.03); return np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 150) * .25
    BEAT = .5
    # chord plan per 4s: Am F C G (minor = tension at start), brighter later
    CH = [[57, 60, 64], [53, 57, 60], [60, 64, 67], [55, 59, 62]]
    for k in range(10):
        add(pad(CH[k % 4], 4.6), k * 4 - .3, .35)
        add(pad([CH[k % 4][0] - 24], 4.6), k * 4 - .3, .4)
    ARP = [0, 1, 2, 1, 2, 3, 2, 1]
    for b in range(int(DUR / (BEAT / 2))):
        t0 = b * BEAT / 2
        if t0 >= 39.0: break
        ch = CH[int(t0 // 4) % 4]
        notes = ch + [ch[0] + 12]
        if t0 >= 1.0: add(pluck(notes[ARP[b % 8]] + 12), t0, .18 if t0 < 7 else .24)
        if t0 >= 7 and b % 2 == 0:
            if (b // 2) % 2 == 0: add(kick(), t0, .55)
            add(hat(), t0 + BEAT / 4, .8)
    for a in (7, 15, 28):
        add(riser(1.4), a - 1.4, .7); add(boom(), a, .8)
    add(boom(), 0.0, .6); add(boom(), 34.5, .7)
    add(ding(1318), 1.8, .8)  # stamp
    x = 3.4
    while x < 4.6: add(tick(), x, 1.0); x += .06
    for ft in FACT_T: add(ding(1568), 15 + ft, .8)
    add(ding(2093), 15 + 11.6, .9)
    add(ding(1760), 28 + 3.0, .7)
    for i in range(8): add(tick(), 34.5 + i * .25, 1.2)
    t = tt(4.0); add(pad([60, 64, 67, 72], 4.0), 36.0, .45)
    out = np.tanh(out * 1.1)
    fl = int(1.0 * SR); out[-fl:] *= np.linspace(1, 0, fl)
    out = out / np.max(np.abs(out)) * .9
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.stack([out, out], 1) * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        init()
        for ts in sys.argv[2:]:
            render(float(ts)).save(os.path.join(HERE, f"ins_preview_{ts}.jpg"), quality=85)
        sys.exit()
    synth(os.path.join(HERE, "music_insurans.wav")); print("audio ok", flush=True)
    N = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", os.path.join(HERE, "music_insurans.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           os.path.join(HERE, "Perodua_Dungun_Premium_Insurans.mp4")], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, buf in enumerate(pool.imap(work, range(N), chunksize=4)):
            ff.stdin.write(buf)
            if i % 300 == 0: print(f"frame {i}/{N}", flush=True)
    ff.stdin.close(); ff.wait(); print("done")
