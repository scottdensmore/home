#!/usr/bin/env python3
"""Build playful GitHub badge images: your avatar over a contribution grid, or
over a QR code pointing at your profile.

The e-ink Badger has no WiFi, so everything is fetched and rendered here and
baked into a 1-bit PNG. Re-run it to refresh the contribution data.

Output filenames follow the badge++ card convention -- <card>-<n>-<name>_<width>
-- so they drop straight into /badges alongside a matching <card>.txt.

Usage:
    ./github_card.py --user mona --card github
    ./github_card.py --user mona --card github --only grid --weeks 26
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from badge_image import fetch_avatar, prepare, save_png  # noqa: E402

SCREEN_H = 128
CONTRIBS_URL = "https://github.com/{user}.contribs"
PROFILE_URL = "https://github.com/{user}"


def fetch_contribs(user):
    req = urllib.request.Request(CONTRIBS_URL.format(user=user),
                                 headers={"User-Agent": "badge-image"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def draw_cell(img, x, y, s, level):
    """One contribution day.

    At 4px a dither pattern is indistinguishable between levels, so the level
    is encoded as how much of the cell is inked instead.
    """
    d = ImageDraw.Draw(img)
    if level == 0:
        d.point([(x, y)], fill=0)          # faint trace keeps the grid visible
        return
    size = {1: max(1, s - 2), 2: max(1, s - 1), 3: s, 4: s}[level]
    off = (s - size) // 2
    d.rectangle([x + off, y + off, x + off + size - 1, y + off + size - 1], fill=0)
    if level == 3:
        d.point([(x + s - 1, y)], fill=1)  # notch so level 3 reads apart from 4


def contribution_grid(weeks, n_weeks, cell_px, gap):
    sel = weeks[-n_weeks:]
    step = cell_px + gap
    grid = Image.new("1", (len(sel) * step - gap, 7 * step - gap), 1)
    for wi, week in enumerate(sel):
        for day in week["contribution_days"]:
            draw_cell(grid, wi * step, day["weekday"] * step, cell_px, day["level"])
    return grid


def qr_matrix(url):
    try:
        import qrcode
    except ImportError:
        raise SystemExit("the QR image needs the qrcode package: pip install qrcode\n"
                         "(or pass --only grid to skip it)")
    # 4 modules is the spec minimum quiet zone; 2 can fail to scan.
    q = qrcode.QRCode(border=4, box_size=1)
    q.add_data(url)
    q.make(fit=True)
    return [[1 if c else 0 for c in row] for row in q.get_matrix()]


def qr_image(matrix, scale):
    n = len(matrix)
    img = Image.new("1", (n * scale, n * scale), 1)
    d = ImageDraw.Draw(img)
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            if v:
                d.rectangle([x * scale, y * scale,
                             x * scale + scale - 1, y * scale + scale - 1], fill=0)
    return img


def avatar_1bit(user, size, contrast):
    src = fetch_avatar(user, max(size, 200))
    return prepare(src, size, size, contrast, True).convert(
        "1", dither=Image.FLOYDSTEINBERG)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True, help="GitHub handle")
    p.add_argument("--card", default="github",
                   help="card name, must match <card>.txt (default: github)")
    p.add_argument("--width", type=int, default=100,
                   help="slot width in px (default: 100)")
    p.add_argument("--weeks", type=int, default=20,
                   help="weeks of history in the grid (default: 20)")
    p.add_argument("--only", choices=["grid", "qr"],
                   help="build just one of the two (default: both)")
    p.add_argument("--contrast", type=float, default=1.4,
                   help="avatar contrast before dithering (default: 1.4)")
    p.add_argument("--outdir", type=Path, default=Path("."))
    args = p.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    W = args.width
    built = []

    if args.only != "qr":
        grid = contribution_grid(fetch_contribs(args.user)["weeks"], args.weeks, 4, 1)
        if grid.width > W:
            raise SystemExit(
                f"grid is {grid.width}px but the slot is {W}px; "
                f"lower --weeks (max ~{W // 5}) or raise --width")
        canvas = Image.new("1", (W, SCREEN_H), 1)
        av = avatar_1bit(args.user, W - 14, args.contrast)
        canvas.paste(av, ((W - av.width) // 2, 1))
        canvas.paste(grid, ((W - grid.width) // 2, SCREEN_H - grid.height - 2))
        out = args.outdir / f"{args.card}-1-grid_{W}.png"
        save_png(canvas, out, dither=False)
        built.append(out)

    if args.only != "grid":
        qr = qr_image(qr_matrix(PROFILE_URL.format(user=args.user)), 2)
        if qr.width > W:
            raise SystemExit(f"QR is {qr.width}px but the slot is {W}px; raise --width")
        canvas = Image.new("1", (W, SCREEN_H), 1)
        av = avatar_1bit(args.user, 48, args.contrast)
        canvas.paste(av, ((W - av.width) // 2, 2))
        canvas.paste(qr, ((W - qr.width) // 2, SCREEN_H - qr.height - 2))
        out = args.outdir / f"{args.card}-2-qr_{W}.png"
        save_png(canvas, out, dither=False)
        built.append(out)

    for b in built:
        print("wrote", b)
    print(f"\nCopy into /badges/ next to {args.card}.txt, then scroll with UP/DOWN.")


if __name__ == "__main__":
    sys.exit(main())
