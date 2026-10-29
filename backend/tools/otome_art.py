"""生成示例乙游用的背景、立绘和短循环音乐。画面是原创色块，方便之后在后台替换。"""
import io
import math
import random
import struct
import wave

from PIL import Image, ImageDraw


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(size, top, mid, bottom):
    width, height = size
    column = Image.new("RGB", (1, height))
    pixels = column.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        if t < 0.62:
            color = _lerp(top, mid, t / 0.62)
        else:
            color = _lerp(mid, bottom, (t - 0.62) / 0.38)
        pixels[0, y] = color
    return column.resize((width, height), Image.Resampling.LANCZOS)


def _glow(diameter, color, max_alpha):
    image = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    pixels = image.load()
    center = diameter / 2
    for y in range(diameter):
        for x in range(diameter):
            distance = math.hypot(x - center, y - center) / center
            if distance >= 1:
                continue
            alpha = int(max_alpha * (1 - distance) ** 2)
            pixels[x, y] = (color[0], color[1], color[2], alpha)
    return image


def _stars(draw, width, height, count, seed):
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(8, width - 8)
        y = rng.randint(8, int(height * 0.72))
        radius = rng.choice((1, 1, 2, 2, 3))
        tone = rng.randint(210, 255)
        draw.ellipse([x, y, x + radius, y + radius], fill=(tone, tone, rng.randint(220, 255)))


def _shade(image):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    draw.rectangle([0, 0, width, 160], fill=(0, 0, 0, 70))
    draw.rectangle([0, height - 460, width, height], fill=(0, 0, 0, 120))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _png(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _night_base():
    image = _gradient((900, 1600), (8, 10, 28), (28, 36, 78), (42, 24, 58))
    glow = _glow(520, (232, 226, 196), 90)
    image.paste(glow, (430, 90), glow)
    draw = ImageDraw.Draw(image)
    draw.ellipse([610, 210, 760, 360], fill=(246, 236, 210))
    draw.ellipse([640, 230, 790, 380], fill=(18, 28, 62))
    _stars(draw, 900, 1600, 90, 20261012)
    return image, draw


def render_roof():
    image, draw = _night_base()
    draw.polygon([(0, 1180), (900, 1040), (900, 1600), (0, 1600)], fill=(18, 16, 28))
    draw.rectangle([0, 1120, 900, 1160], fill=(46, 40, 58))
    for x in range(40, 880, 70):
        draw.rectangle([x, 1040, x + 8, 1160], fill=(70, 62, 84))
    return _png(_shade(image))


def render_dome():
    image, draw = _night_base()
    draw.pieslice([180, 760, 720, 1300], 180, 360, fill=(36, 40, 62))
    draw.rectangle([250, 1020, 650, 1320], fill=(24, 26, 42))
    draw.ellipse([400, 900, 500, 1000], fill=(232, 196, 120))
    draw.polygon([(0, 1320), (900, 1240), (900, 1600), (0, 1600)], fill=(16, 14, 24))
    return _png(_shade(image))


def render_hall():
    image = _gradient((900, 1600), (48, 24, 32), (92, 48, 42), (28, 18, 22))
    glow = _glow(360, (232, 186, 96), 140)
    image.paste(glow, (270, 180), glow)
    image.paste(_glow(180, (232, 186, 96), 110), (80, 360), _glow(180, (232, 186, 96), 110))
    image.paste(_glow(180, (232, 186, 96), 110), (640, 360), _glow(180, (232, 186, 96), 110))
    draw = ImageDraw.Draw(image)
    draw.polygon([(0, 0), (140, 0), (220, 1600), (0, 1600)], fill=(62, 22, 32))
    draw.polygon([(900, 0), (760, 0), (680, 1600), (900, 1600)], fill=(62, 22, 32))
    draw.rectangle([0, 1180, 900, 1600], fill=(72, 42, 36))
    draw.rectangle([0, 1180, 900, 1210], fill=(196, 154, 86))
    return _png(_shade(image))


def render_cover():
    return render_roof()


def _bust(hair, cloth, accent, eye, long_hair):
    scale = 2
    width, height = 640 * scale, 980 * scale
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values):
        return [int(v * scale) for v in values]

    hair_bottom = 860 if long_hair else 560
    draw.ellipse(box([70, 30, 570, hair_bottom]), fill=hair)
    draw.polygon(box([40, 980, 150, 500, 490, 500, 600, 980]), fill=cloth)
    draw.polygon(box([230, 500, 320, 430, 410, 500]), fill=accent)
    draw.rectangle(box([270, 430, 370, 560]), fill=(242, 214, 196))
    draw.ellipse(box([155, 120, 485, 500]), fill=(247, 222, 206))
    draw.polygon(box([150, 210, 320, 90, 490, 210, 430, 250, 210, 250]), fill=hair)
    if long_hair:
        draw.ellipse(box([60, 240, 190, 820]), fill=hair)
        draw.ellipse(box([450, 240, 590, 820]), fill=hair)
        draw.ellipse(box([175, 150, 465, 430]), fill=(247, 222, 206))
        draw.polygon(box([170, 200, 320, 110, 470, 200, 400, 230, 230, 230]), fill=hair)
    draw.ellipse(box([230, 250, 292, 292]), fill=(255, 255, 255))
    draw.ellipse(box([348, 250, 410, 292]), fill=(255, 255, 255))
    draw.ellipse(box([244, 260, 278, 286]), fill=eye)
    draw.ellipse(box([362, 260, 396, 286]), fill=eye)
    draw.ellipse(box([252, 268, 266, 282]), fill=(40, 30, 46))
    draw.ellipse(box([370, 268, 384, 282]), fill=(40, 30, 46))
    draw.ellipse(box([248, 262, 258, 270]), fill=(255, 255, 255))
    draw.ellipse(box([366, 262, 376, 270]), fill=(255, 255, 255))
    draw.arc(box([280, 330, 360, 390]), 20, 160, fill=(186, 122, 128), width=3 * scale)
    image = image.resize((640, 980), Image.Resampling.LANCZOS)
    return _fade(image)


def _fade(image):
    width, height = image.size
    alpha = image.getchannel("A")
    mask = Image.new("L", (width, height), 255)
    pixels = mask.load()
    start = int(height * 0.78)
    for y in range(start, height):
        value = int(255 * (1 - (y - start) / max(height - start, 1)))
        for x in range(width):
            pixels[x, y] = value
    from PIL import ImageChops
    image.putalpha(ImageChops.multiply(alpha, mask))
    return _png(image)


def render_portrait_gu():
    return _bust((54, 36, 84), (232, 228, 238), (214, 186, 120), (124, 96, 186), True)


def render_portrait_lu():
    return _bust((32, 28, 32), (28, 30, 40), (196, 154, 78), (176, 122, 62), False)


def _wav(notes, seconds=8, rate=22050):
    count = int(seconds * rate)
    samples = []
    for index in range(count):
        moment = index / rate
        value = 0.0
        edge = min(1.0, moment / 0.08, (seconds - moment) / 0.35)
        for freq, start, duration, gain in notes:
            if start <= moment < start + duration:
                local = moment - start
                envelope = min(1.0, local / 0.04) * min(1.0, (duration - local) / 0.35)
                value += math.sin(2 * math.pi * freq * local) * gain * envelope
                value += math.sin(2 * math.pi * freq * 2 * local) * gain * envelope * 0.16
        value = max(-1.0, min(1.0, value * edge))
        samples.append(int(value * 28000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return buffer.getvalue()


def _arp(scale, seconds=8, step=0.55, gain=0.22):
    notes = []
    moment = 0.0
    index = 0
    while moment < seconds:
        freq = scale[index % len(scale)]
        notes.append((freq, moment, 1.15, gain))
        moment += step
        index += 1
    notes.append((scale[0] / 2, 0.0, seconds, gain * 0.28))
    return _wav(notes, seconds=seconds)


def render_bgm_night():
    return _arp([220.0, 261.63, 329.63, 392.0, 440.0], step=0.62, gain=0.2)


def render_bgm_hall():
    return _arp([146.83, 185.0, 220.0, 293.66, 369.99], step=0.5, gain=0.18)
