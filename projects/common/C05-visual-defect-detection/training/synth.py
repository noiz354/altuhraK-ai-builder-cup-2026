"""Synthetic household-plate photos for exercising the pipeline end to end.

Stand-in until the collected dataset is wired in. It models the scenario in
which MBG portions are served on each household's own plates: every
"household" (group) keeps one plate style and table surface across its
photos, which is exactly the correlation the group split has to respect.

These images only prove the plumbing. They are not a substitute for real
photos and must never be used to report model quality.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from dataset import COMPONENTS

SIZE = (640, 480)
PLATE_TYPES = ('home_plate', 'bowl', 'tray_compartment', 'lunchbox', 'banana_leaf')

COLORS = {
    'carbohydrate': [(246, 244, 236), (236, 230, 214), (226, 196, 140)],   # rice, nasi uduk, noodles
    'protein': [(150, 92, 52), (196, 140, 80), (240, 214, 120), (176, 120, 96)],  # chicken, tempe, egg, fish
    'vegetable': [(64, 140, 60), (98, 160, 72), (40, 110, 70), (210, 120, 50)],   # leafy greens, beans, carrot
}


def _table(draw: ImageDraw.ImageDraw, rng: random.Random, style: dict):
    w, h = SIZE
    draw.rectangle([0, 0, w, h], fill=style['table'])
    if style['table_pattern'] == 'wood':
        for y in range(0, h, rng.randint(14, 22)):
            draw.line([0, y, w, y + rng.randint(-6, 6)], fill=tuple(max(0, c - 18) for c in style['table']), width=2)
    elif style['table_pattern'] == 'cloth':
        step = 40
        for x in range(0, w, step):
            draw.rectangle([x, 0, x + step // 2, h], fill=tuple(min(255, c + 14) for c in style['table']))


def _blob(draw, rng, cx, cy, r, color, grains=False):
    pts = []
    for k in range(14):
        a = 2 * math.pi * k / 14
        rr = r * rng.uniform(0.75, 1.1)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.8))
    draw.polygon(pts, fill=color)
    if grains:
        for _ in range(int(r * 1.5)):
            gx, gy = cx + rng.uniform(-r * 0.7, r * 0.7), cy + rng.uniform(-r * 0.5, r * 0.5)
            draw.ellipse([gx, gy, gx + 3, gy + 2], fill=tuple(max(0, c - 22) for c in color))


def _plate(draw, rng, style) -> list[tuple[int, int, int]]:
    """Draw the vessel and return three food anchor points (cx, cy, radius)."""
    w, h = SIZE
    kind, color = style['plate_type'], style['plate']
    cx, cy = w // 2 + rng.randint(-30, 30), h // 2 + rng.randint(-20, 20)
    if kind == 'tray_compartment':
        draw.rounded_rectangle([cx - 250, cy - 180, cx + 250, cy + 180], 24, fill=color)
        wells = [(cx - 150, cy - 70, 70), (cx + 30, cy - 70, 70), (cx - 60, cy + 90, 70)]
        for x, y, r in wells:
            draw.rounded_rectangle([x - r - 10, y - r + 10, x + r + 10, y + r - 10], 14,
                                   fill=tuple(max(0, c - 16) for c in color))
        return wells
    if kind == 'lunchbox':
        draw.rounded_rectangle([cx - 230, cy - 160, cx + 230, cy + 160], 18, fill=color)
        draw.line([cx, cy - 150, cx, cy + 150], fill=tuple(max(0, c - 40) for c in color), width=6)
        return [(cx - 115, cy - 50, 70), (cx + 115, cy - 60, 62), (cx + 110, cy + 80, 55)]
    if kind == 'banana_leaf':
        draw.ellipse([cx - 280, cy - 190, cx + 280, cy + 190], fill=(58, 128, 52))
        draw.line([cx - 270, cy, cx + 270, cy], fill=(90, 160, 80), width=4)
        return [(cx - 90, cy - 20, 85), (cx + 110, cy - 70, 55), (cx + 100, cy + 80, 55)]
    r = 200 if kind == 'home_plate' else 160
    draw.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=color)
    if style['rim']:
        draw.ellipse([cx - r + 14, cy - r * 0.8 + 12, cx + r - 14, cy + r * 0.8 - 12],
                     outline=style['rim'], width=5)
    if kind == 'bowl':
        draw.ellipse([cx - r + 30, cy - r * 0.8 + 26, cx + r - 30, cy + r * 0.8 - 26],
                     fill=tuple(max(0, c - 20) for c in color))
        return [(cx - 50, cy - 25, 70), (cx + 60, cy - 30, 48), (cx + 20, cy + 55, 48)]
    return [(cx - 70, cy - 10, 85), (cx + 95, cy - 55, 55), (cx + 85, cy + 65, 55)]


def household_style(rng: random.Random, plate_type: str) -> dict:
    plates = [(250, 250, 248), (236, 228, 214), (196, 220, 236), (240, 206, 206), (220, 236, 210), (205, 205, 210)]
    tables = [(150, 108, 72), (196, 160, 120), (120, 120, 126), (210, 200, 186), (176, 58, 58)]
    return {'plate_type': plate_type, 'plate': rng.choice(plates),
            'rim': rng.choice([None, (60, 100, 170), (170, 60, 80), (70, 130, 80)]),
            'table': rng.choice(tables), 'table_pattern': rng.choice(['wood', 'cloth', 'plain'])}


def render(rng: random.Random, style: dict, present: set[str], degrade: str | None) -> Image.Image:
    img = Image.new('RGB', SIZE)
    draw = ImageDraw.Draw(img)
    _table(draw, rng, style)
    anchors = _plate(draw, rng, style)
    for key, (x, y, r) in zip(COMPONENTS, anchors):
        if key in present:
            colors = COLORS[key]
            if style['plate_type'] == 'banana_leaf' and key == 'vegetable':
                # Green on green would be invisible, which makes the label wrong, not hard.
                colors = [c for c in colors if c[1] < 130 or c[0] > 150]
            _blob(draw, rng, x, y, r * 0.85, rng.choice(colors), grains=(key == 'carbohydrate'))
    if degrade == 'occluded_component':
        x, y, r = anchors[rng.randrange(3)]
        draw.rounded_rectangle([x - r - 20, y - r, x + r + 40, y + r + 20], 30, fill=(214, 170, 140))  # a hand
    img = img.rotate(rng.uniform(-12, 12), resample=Image.BICUBIC, fillcolor=style['table'])
    if degrade == 'blurred_image':
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(7, 11)))
    elif degrade == 'poor_lighting':
        img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.12, 0.22))
    elif degrade == 'component_out_of_frame':
        w, h = SIZE
        img = img.crop((w // 2 + 40, 0, w, h)).resize(SIZE)
    else:
        img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.85, 1.15))
    return img


def generate(out_dir: Path, households: int = 40, photos_per_household: int = 4, seed: int = 7) -> dict:
    """Write images/ and manifest.jsonl. Roughly 45% complete, 35% missing, 20% uncertain."""
    rng = random.Random(seed)
    out_dir = Path(out_dir)
    (out_dir / 'images').mkdir(parents=True, exist_ok=True)
    rows = []
    for h in range(households):
        # Most households use their own plate; some schools still send trays home.
        plate_type = rng.choices(PLATE_TYPES, weights=[45, 15, 15, 15, 10])[0]
        style = household_style(rng, plate_type)
        for p in range(photos_per_household):
            roll = rng.random()
            missing: list[str] = []
            reason = None
            if roll < 0.45:
                label = 'meal_complete'
            elif roll < 0.80:
                label = 'missing_component'
                missing = sorted(rng.sample(COMPONENTS, rng.choice([1, 1, 2])))
            else:
                label = 'uncertain'
                reason = rng.choice(['occluded_component', 'poor_lighting', 'blurred_image', 'component_out_of_frame'])
            present = set(COMPONENTS) - set(missing)
            img = render(rng, style, present, reason)
            name = f'images/hh{h:03d}_{p:02d}.jpg'
            img.save(out_dir / name, format='JPEG', quality=rng.randint(70, 92))
            rows.append({'image': name, 'label': label, 'missing': missing, 'plate_type': plate_type,
                         'group_id': f'household-{h:03d}', 'source': 'synthetic',
                         'uncertain_reason': reason, 'boxes': [], 'notes': 'synthetic; pipeline test only'})
    with (out_dir / 'manifest.jsonl').open('w', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row) + '\n')
    return {'images': len(rows), 'households': households, 'out_dir': str(out_dir)}
