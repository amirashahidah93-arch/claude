"""Versi voice-over: TAK PASTI BERAPA PREMIUM INSURANS? (watak SA + gambar Ativa + suara lelaki)
1) python3 tts_insurans.py   (jana vo/*.mp3 + vo/timing.json)
2) python3 insurans_vo.py    (render)   |  python3 insurans_vo.py preview 3 10 ...
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool
import insurans as B
from insurans import (W, H, FPS, font, FONT_XB, FONT_B, FONT_SB, YELLOW, NAVY, WHITE, RED, clamp, prog, lerp,
                      ease_out_cubic, ease_in_out, ease_out_back, pop, emoji, paste_scaled, text_sticker, outlined_text,
                      wrap, word_img, bokeh_layer, light_rays, finish, bubble, stamp, factor_card, FACTORS)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 40.0
SR = 44100
TIM = json.load(open(os.path.join(HERE, "vo", "timing.json")))
# when each voice segment starts (seconds in video)
VO_AT = {"v1": 0.3, "v2": 7.3, "v3": 15.3, "v4a": 27.1, "v4b": 35.9}
SC = [(0, 7, "s1"), (7, 15, "s2"), (15, 27, "s3"), (27, 40, "s4")]

def wt(seg, word, nth=0):
    """absolute video time of a spoken word"""
    c = 0
    for w, o, _ in TIM[seg]:
        if w.lower().strip(",.!?") == word.lower():
            if c == nth: return VO_AT[seg] + o
            c += 1
    raise KeyError(word)

def times_for(text, seg):
    """map each displayed word to its spoken time (sequential match)."""
    spoken = [(w.lower().strip(",.!?"), VO_AT[seg] + o) for w, o, _ in TIM[seg]]
    out, j, last = [], 0, VO_AT[seg]
    for dw in text.split():
        key = dw.lower().strip(",.!?:")
        for k in range(j, len(spoken)):
            if spoken[k][0] == key:
                last = spoken[k][1]; j = k + 1; break
        else:
            last += .05
        out.append(last)
    return out

_tcache = {}
def kinetic_vo(frame, text, seg, T, y, size=72, maxw=940, hl=(), fg=WHITE):
    """words appear exactly when spoken (T = absolute time)."""
    k = (text, seg)
    if k not in _tcache: _tcache[k] = times_for(text, seg)
    times = _tcache[k]
    lines = wrap(text, size, maxw)
    f = font(FONT_XB, size)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    idx = 0
    for ln in lines:
        words = ln.split()
        widths = [d0.textlength(w + " ", font=f) for w in words]
        x = W / 2 - sum(widths) / 2
        for w, ww in zip(words, widths):
            p = prog(T, times[idx] - .05, times[idx] + .2)
            if p > 0:
                col = YELLOW if w.strip("?!,.:").upper() in hl else fg
                im = word_img(w, size, col, max(6, size // 9), NAVY, FONT_XB)
                paste_scaled(frame, im, x + ww / 2 - size * .12, y + (1 - ease_out_cubic(p)) * 30, 1 + .15 * (1 - p), alpha=p)
            x += ww; idx += 1
        y += size * 1.18
    return y

# ------------------------------------------------------------ assets
A = {}
def init():
    if A: return
    B.init()
    sa = Image.open(os.path.join(HERE, "sa.png")).convert("RGBA")
    A["sa"] = sa.resize((700, int(700 * sa.height / sa.width)), Image.LANCZOS)
    car = Image.open(os.path.join(HERE, "car_ativa_side.jpg")).convert("RGB")
    A["car"] = car
    # cinematic band: car photo full width with soft top/bottom fade
    bw = W; bh = int(car.height * bw / car.width)
    band = car.resize((int(bw * 1.12), int(bh * 1.12)), Image.LANCZOS).convert("RGBA")
    A["band_src"] = band
    m = np.ones((band.height, band.width), np.float32)
    fade = int(band.height * .18)
    ramp = np.linspace(0, 1, fade)[:, None]
    m[:fade] *= ramp; m[-fade:] *= ramp[::-1]
    A["band_mask"] = Image.fromarray((m * 255).astype(np.uint8))
    # car cutout-free "hero card" for CTA
    A["car_card"] = B.rounded_card(car.resize((900, 600), Image.LANCZOS), 30, 8)
    env = np.load(os.path.join(HERE, "vo", "env.npy")) if os.path.exists(os.path.join(HERE, "vo", "env.npy")) else None
    A["env"] = env

def talk(T):
    env = A["env"]
    if env is None: return 0
    i = int(T * FPS)
    return float(env[i]) if 0 <= i < len(env) else 0

def car_band(frame, t, cy, zoom0=1.0, zoom1=1.08, dur=7, grade=.25):
    src = A["band_src"]
    z = lerp(zoom0, zoom1, clamp(t / dur))
    cw, ch = src.width / z, src.height / z
    x0 = (src.width - cw) / 2 + 30 * t / dur
    x0 = clamp(x0, 0, src.width - cw)
    y0 = (src.height - ch) / 2
    out_h = int(src.height / 1.12)
    im = src.resize((W, out_h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    if grade:
        im = Image.blend(im, Image.new("RGBA", im.size, (10, 15, 35, 255)), grade)
    mask = A["band_mask"].resize(im.size)
    im.putalpha(mask)
    frame.alpha_composite(im, (0, int(cy - out_h / 2)))

def place_sa(frame, T, x, y, scale=1.0, enter=None, flip=False):
    sa = A["sa"]
    if flip: sa = sa.transpose(Image.FLIP_LEFT_RIGHT)
    a = talk(T)
    s = scale * (1 + .025 * a) * (1 + .006 * math.sin(T * 2.2))
    rot = 1.2 * math.sin(T * 1.7) + 2.0 * a
    if enter is not None:
        p = ease_out_cubic(prog(T, enter, enter + .6))
        x = lerp(-450 if not flip else W + 450, x, p)
    paste_scaled(frame, sa, x, y - 8 * a, s, rot=rot)

# ------------------------------------------------------------ scenes (t = local, T = absolute)
def s1(t, T):
    f = B.G["night"].copy()
    light_rays(f, t, col=(255, 120, 120)); bokeh_layer(f, t, (255, 140, 140))
    car_band(f, t, 1330, 1.0, 1.1, 7, grade=.35)
    dp = ease_out_back(prog(t, .6, 1.2), 1.4)
    if dp > 0: paste_scaled(f, B.G["doc"], W / 2, 760 + 10 * math.sin(t * 2), .62 * dp, rot=-5 + 2 * math.sin(t))
    ts = wt("v1", "tamat")
    sp = prog(T, ts, ts + .25)
    if sp > 0: paste_scaled(f, stamp(), W / 2 + 10, 820, lerp(2.0, .8, ease_out_cubic(sp)), rot=14, alpha=sp)
    kinetic_vo(f, "Insurans kereta dah nak tamat?", "v1", T, 230, 96, hl=("TAMAT",))
    tp = wt("v1", "premium")
    if T >= tp:
        digits = "".join("0123456789"[int((t * 37 + i * 7) % 10)] for i in range(3)) if T < tp + 1.0 else "???"
        paste_scaled(f, outlined_text(f"RM {digits}", 120, fg=YELLOW, stroke_w=14), W / 2 + (8 * math.sin(t * 60) if T < tp + 1 else 0), 1080, pop(T, tp, .3))
        paste_scaled(f, emoji("🤔", 120), W - 140, 1020, pop(T, tp + 1.0), rot=10)
    kinetic_vo(f, "Tapi tak pasti berapa premium yang kena bayar nanti?", "v1", T, 1560, 68, hl=("PREMIUM",))
    return f

def s2(t, T):
    f = B.G["dawn"].copy()
    light_rays(f, t, cx=W * .8, cy=-300, col=(200, 255, 240)); bokeh_layer(f, t, (180, 255, 240))
    for i in range(8):
        a = i / 8 * 2 * math.pi + t * 1.5
        r = 260 + 400 * ease_in_out(prog(t, 1.0, 2.2)); al = 1 - prog(t, 1.4, 2.2)
        if al > 0:
            paste_scaled(f, outlined_text("?", 90, fg=WHITE, stroke_w=8), W / 2 + r * math.cos(a), 1000 + r * .6 * math.sin(a), 1, rot=math.degrees(a), alpha=al)
    tj, tr = wt("v2", "jangan"), wt("v2", "risau")
    paste_scaled(f, outlined_text("JANGAN", 120, fg=WHITE, stroke_w=12), W / 2, 260, pop(T, tj, .35), rot=-3)
    paste_scaled(f, outlined_text("RISAU!", 170, fg=YELLOW, stroke_w=14), W / 2, 410, pop(T, tr, .35), rot=-3)
    place_sa(f, T, 340, 1380, .95, enter=7.4)
    ta = wt("v2", "anda")
    b = ease_out_back(prog(T, ta - .1, ta + .3), 1.4)
    if b > 0:
        paste_scaled(f, bubble("Anda tak perlu pening-pening nak agak berapa kos insurans kereta.", 50, 500), 760, 760, b)
    tk = wt("v2", "kereta")
    s2_ = pop(T, tk + .4)
    if s2_:
        paste_scaled(f, text_sticker("KAMI BANTU!", 56, fg=NAVY, bg=YELLOW, pad=(30, 14)), 790, 1180, s2_, rot=-4)
    return f

FACT_WORDS = [("model", 0), ("nilai", 0), ("n", 0), ("jenis", 0)]
def s3(t, T):
    f = B.G["brand"].copy()
    light_rays(f, t, col=(150, 230, 255)); bokeh_layer(f, t, (150, 220, 255))
    paste_scaled(f, outlined_text("SEBENARNYA,", 70, fg=WHITE, stroke_w=9), W / 2, 220, pop(T, wt("v3", "sebenarnya"), .3))
    kinetic_vo(f, "premium insurans bergantung pada beberapa faktor:", "v3", T, 330, 62, hl=("PREMIUM", "FAKTOR:"))
    ft = [wt("v3", w, n) for w, n in FACT_WORDS]
    end = wt("v3", "dipilih") + .6
    for i, ((ic, ti, sub), t0) in enumerate(zip(FACTORS, ft)):
        p = ease_out_back(prog(T, t0 - .1, t0 + .35), 1.3)
        if p <= 0: continue
        active = t0 <= T < (ft[i + 1] if i + 1 < 4 else end)
        x = W / 2 + (1 - p) * (1100 if i % 2 == 0 else -1100)
        paste_scaled(f, factor_card(ic, ti, sub, active), x, 620 + i * 225, 1.04 if active else 1.0)
        paste_scaled(f, text_sticker(str(i + 1), 44, fg=NAVY, bg=YELLOW, pad=(20, 6), radius=30), x - 440, 620 + i * 225 - 85, p)
    if T >= end:
        paste_scaled(f, text_sticker("= ANGGARAN PREMIUM ANDA", 54, fg=NAVY, bg=YELLOW, pad=(36, 18)), W / 2, 1560,
                     pop(T, end, .35) * (1 + .03 * math.sin(t * 8)))
    # small SA peeking bottom-right, presenting
    place_sa(f, T, W - 170, 1740, .5, flip=True)
    return f

def call_card():
    card = Image.new("RGBA", (520, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle((10, 12, 519, 359), 40, fill=(0, 0, 0, 100))
    d.rounded_rectangle((0, 0, 509, 347), 40, fill=WHITE)
    d.text((255, 70), "HUBUNGI", font=font(FONT_B, 44), fill=(90, 100, 120), anchor="mm")
    d.text((255, 150), "PERODUA", font=font(FONT_XB, 72), fill=NAVY, anchor="mm")
    d.rounded_rectangle((115, 200, 395, 262), 18, fill=RED)
    d.text((255, 231), "DUNGUN", font=font(FONT_XB, 44), fill=WHITE, anchor="mm")
    d.text((255, 305), "hari ini", font=font(FONT_B, 40), fill=NAVY, anchor="mm")
    return card

SPLIT = 8.75  # local time in s4 where part B starts
def s4(t, T):
    if t < SPLIT:
        f = B.G["warm"].copy()
        light_rays(f, t, col=(255, 210, 160)); bokeh_layer(f, t, (255, 210, 150))
        kinetic_vo(f, "Nak tahu berapa anggaran premium insurans kereta anda?", "v4a", T, 220, 66, hl=("ANGGARAN", "PREMIUM"))
        tm = wt("v4a", "mudah")
        paste_scaled(f, outlined_text("MUDAH SAHAJA!", 110, fg=YELLOW, stroke_w=12), W / 2, 590, pop(T, tm, .35), rot=-3)
        place_sa(f, T, 330, 1300, .9, enter=27.15)
        th = wt("v4a", "hubungi")
        c = ease_out_back(prog(T, th - .1, th + .3), 1.4)
        if c > 0:
            paste_scaled(f, call_card(), 790, 960, c * .95 * (1 + .02 * math.sin(t * 6)))
            paste_scaled(f, emoji("📞", 110), 600, 800, c * (1 + .12 * abs(math.sin(t * 12))), rot=-15 + 10 * math.sin(t * 20))
        tk = wt("v4a", "kami")
        if T > tk - .1:
            st = text_sticker("Kami sedia bantu semak untuk anda", 46, fg=NAVY, bg=YELLOW, pad=(28, 14), fpath=FONT_B)
            paste_scaled(f, st, W / 2, 1680, pop(T, tk - .1))
        return f
    tt = t - SPLIT
    f = B.G["brand"].copy()
    light_rays(f, t, col=(255, 210, 160)); bokeh_layer(f, t, (255, 210, 150))
    car_band(f, tt, 1180, 1.0, 1.06, 4.5, grade=.1)
    cal = Image.new("RGBA", (360, 380), (0, 0, 0, 0)); d = ImageDraw.Draw(cal)
    d.rounded_rectangle((10, 14, 359, 379), 36, fill=(0, 0, 0, 110))
    d.rounded_rectangle((0, 0, 349, 365), 36, fill=WHITE)
    d.rounded_rectangle((0, 0, 349, 100), 36, fill=RED); d.rectangle((0, 70, 349, 100), fill=RED)
    d.text((175, 52), "TAMAT", font=font(FONT_XB, 52), fill=WHITE, anchor="mm")
    days = max(0, 7 - int(tt * 4))
    d.text((175, 230), str(days), font=font(FONT_XB, 170), fill=NAVY, anchor="mm")
    d.text((175, 330), "HARI LAGI", font=font(FONT_B, 34), fill=(110, 110, 120), anchor="mm")
    paste_scaled(f, cal, W / 2, 330, ease_out_back(prog(tt, 0, .4), 1.4), rot=3 * math.sin(tt * 14) if 1.6 < tt < 2.2 else 0)
    kinetic_vo(f, "Jangan tunggu sampai insurans tamat baru nak renew!", "v4b", T, 600, 74, hl=("JANGAN", "TAMAT", "RENEW!"))
    b = pop(tt, 2.6, .4)
    if b:
        brand = Image.new("RGBA", (860, 230), (0, 0, 0, 0)); bd = ImageDraw.Draw(brand)
        bd.rounded_rectangle((10, 14, 859, 229), 40, fill=(0, 0, 0, 110))
        bd.rounded_rectangle((0, 0, 849, 215), 40, fill=WHITE)
        bd.text((425, 75), "PERODUA", font=font(FONT_XB, 104), fill=NAVY, anchor="mm")
        bd.rounded_rectangle((235, 132, 615, 196), 20, fill=RED)
        bd.text((425, 165), "DUNGUN", font=font(FONT_XB, 50), fill=WHITE, anchor="mm")
        paste_scaled(f, brand, W / 2, 1530, b)
    s = pop(tt, 3.1)
    if s:
        st = text_sticker("Hubungi kami untuk semakan premium", 44, fg=NAVY, bg=YELLOW, pad=(84, 18), radius=40, fpath=FONT_B)
        st.alpha_composite(emoji("📞", 50), (22, (st.height - 12 - 50) // 2))
        paste_scaled(f, st, W / 2, 1720, s * (1 + .03 * math.sin(tt * 6)))
    return f

FN = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
def render(T):
    for a, b, k in SC:
        if a <= T < b or (b == 40 and T >= a): break
    f = FN[k](T - a, T)
    starts = [a for a, _, _ in SC[1:]] + [27 + SPLIT]
    for st in starts:
        if 0 <= T - st < .35:
            p = (T - st) / .35
            z = 1 + .12 * (1 - ease_out_cubic(p))
            f = f.resize((int(W * z), int(H * z)), Image.BILINEAR).crop((int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
            f = Image.blend(f, Image.new("RGBA", (W, H), WHITE), .6 * (1 - p))
    if T < .4: f = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), f, T / .4)
    return finish(f, T).convert("RGB")

def work(i):
    init(); return render(i / FPS).tobytes()

# ------------------------------------------------------------ audio: VO + ducked music + sfx
def load_mp3(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def build_audio():
    n = int(SR * DUR)
    vo = np.zeros(n)
    for k, at in VO_AT.items():
        x = load_mp3(os.path.join(HERE, "vo", f"{k}.mp3"))
        i = int(at * SR); j = min(n, i + len(x)); vo[i:j] += x[: j - i]
    vo = vo / (np.max(np.abs(vo)) + 1e-9) * .95
    # envelope per video frame (for SA talking animation)
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(vo[i * hop:(i + 1) * hop] ** 2)) for i in range(int(DUR * FPS))])
    env = np.clip(env / (env.max() + 1e-9) * 1.6, 0, 1)
    np.save(os.path.join(HERE, "vo", "env.npy"), env)
    # music from base script (cinematic), rendered to wav then ducked
    mpath = os.path.join(HERE, "music_insurans_vo.wav")
    old_ft = B.FACT_T
    B.FACT_T = []  # we add our own dings below
    B.synth(mpath)
    B.FACT_T = old_ft
    with wave.open(mpath) as w:
        m = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2)[:, 0].astype(np.float32) / 32768
    m = np.pad(m, (0, max(0, n - len(m))))[:n]
    # sidechain duck
    e = np.repeat(env, hop)[:n]; e = np.pad(e, (0, n - len(e)))
    k = int(.15 * SR); e = np.convolve(e, np.ones(k) / k, mode="same")
    music = m * (0.42 - 0.24 * np.clip(e * 1.5, 0, 1))
    # extra sfx synced to voice
    tt = lambda d: np.arange(int(d * SR)) / SR
    def ding(fq):
        t = tt(.5); return (np.sin(2 * np.pi * fq * t) + .4 * np.sin(2 * np.pi * fq * 2.01 * t)) * np.exp(-t * 8) * .25
    sfx = np.zeros(n)
    def add(sig, at, g=1.0):
        i = int(at * SR); j = min(n, i + len(sig)); sfx[i:j] += sig[: j - i] * g
    for w, nn in FACT_WORDS: add(ding(1568), wt("v3", w, nn), .8)
    add(ding(2093), wt("v3", "dipilih") + .6, .8)
    add(ding(1760), wt("v4a", "hubungi"), .7)
    mix = vo * 1.0 + music + sfx
    mix = np.tanh(mix * 1.05)
    fl = int(.8 * SR); mix[-fl:] *= np.linspace(1, 0, fl)
    mix = mix / np.max(np.abs(mix)) * .95
    out = os.path.join(HERE, "audio_insurans_vo.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
    return out

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        if not os.path.exists(os.path.join(HERE, "vo", "env.npy")): build_audio()
        init()
        for ts in sys.argv[2:]:
            render(float(ts)).save(os.path.join(HERE, f"vo_preview_{ts}.jpg"), quality=85)
        sys.exit()
    apath = build_audio(); print("audio ok", flush=True)
    N = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", apath, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           os.path.join(HERE, "Perodua_Dungun_Premium_Insurans_VO.mp4")], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, buf in enumerate(pool.imap(work, range(N), chunksize=4)):
            ff.stdin.write(buf)
            if i % 300 == 0: print(f"frame {i}/{N}", flush=True)
    ff.stdin.close(); ff.wait(); print("done")
