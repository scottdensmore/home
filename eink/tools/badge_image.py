#!/usr/bin/env python3
"""Convert a GitHub avatar or a local photo into an image the e-ink Badger can display.

The badge++ app (eink/examples/badge++) inventories /badges and blits one image per
press of UP/DOWN. It parses the pixel width out of the filename -- "profile_100.jpg"
means "this image is 100px wide" -- and reserves the remaining width for your name.
A file with no _<width> suffix is treated as a full-screen background instead.

Screen is 296x128, 1-bit black and white.

Usage:
    ./badge_image.py --user mona --width 100
    ./badge_image.py --input photo.jpg --width 120 --format png
    ./badge_image.py --input photo.jpg --background
    ./badge_image.py --input logo.png --icon myapp
"""

import argparse
import io
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

SCREEN_W, SCREEN_H = 296, 128
ICON_SIZE = 52


def fetch_avatar(user, size):
    """Pull a GitHub avatar. github.com/<user>.png redirects to the real avatar host."""
    url = f"https://github.com/{user}.png?size={max(size, 200)}"
    req = urllib.request.Request(url, headers={"User-Agent": "badge-image"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return Image.open(io.BytesIO(resp.read()))


def zoom_crop(img, zoom, centering):
    """Crop to 1/zoom of the frame around `centering` before fitting.

    Portraits usually have dead space above the head; zooming in pulls the face
    up to badge size instead of wasting pixels on background.
    """
    if zoom <= 1.0:
        return img
    cw, ch = int(img.width / zoom), int(img.height / zoom)
    left = int((img.width - cw) * centering[0])
    top = int((img.height - ch) * centering[1])
    return img.crop((left, top, left + cw, top + ch))


def fit(img, w, h, centering):
    """Center-crop to the target aspect ratio, then resize. Never distorts."""
    return ImageOps.fit(img, (w, h), method=Image.LANCZOS, centering=centering)


def prepare(img, w, h, contrast, autocontrast, zoom=1.0, centering=(0.5, 0.5)):
    img = img.convert("RGBA")
    # Flatten transparency onto white so avatars with alpha don't go black.
    flat = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat.alpha_composite(img)
    img = flat.convert("L")

    img = zoom_crop(img, zoom, centering)
    img = fit(img, w, h, centering)
    if autocontrast:
        img = ImageOps.autocontrast(img, cutoff=2)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    return img


def save_jpeg(img, path):
    """Baseline (non-progressive) grayscale JPEG. The badge dithers it on-device."""
    img.convert("L").save(
        path, "JPEG", quality=95, optimize=True, progressive=False, subsampling=0
    )


def save_png(img, path, dither):
    """1-bit PNG, no alpha. Pre-dithered because PNG is lossless and holds the pattern."""
    out = img.convert("1", dither=Image.FLOYDSTEINBERG if dither else Image.NONE)
    out.save(path, "PNG", optimize=True)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--user", help="GitHub handle; fetches that account's avatar")
    src.add_argument("--input", type=Path, help="path to a local image")

    p.add_argument("--width", type=int, default=100,
                   help="width of the image strip in px (default: 100)")
    p.add_argument("--height", type=int,
                   help="height in px (default: full 128 for photos, square for avatars)")
    p.add_argument("--background", action="store_true",
                   help="full-screen 296x128 background instead of a side strip")
    p.add_argument("--icon", metavar="APPNAME",
                   help="emit a 52x52 launcher icon named icon-<APPNAME>")

    p.add_argument("--format", choices=["jpg", "png"], default="jpg",
                   help="jpg works on every badge; png needs a 2024 badge (default: jpg)")
    p.add_argument("--contrast", type=float, default=1.4,
                   help="contrast multiplier applied before dithering (default: 1.4)")
    p.add_argument("--no-autocontrast", action="store_true",
                   help="skip the automatic level stretch")
    p.add_argument("--no-dither", action="store_true",
                   help="PNG only: hard threshold instead of Floyd-Steinberg")
    p.add_argument("--variants", action="store_true",
                   help="also emit -lo/-hi contrast versions so you can compare")
    p.add_argument("--zoom", type=float, default=1.0,
                   help="crop tighter before fitting; 1.5 fills the frame with "
                        "the middle two-thirds (default: 1.0, no crop)")
    p.add_argument("--centering", default="0.5,0.5", metavar="X,Y",
                   help="crop anchor as two 0-1 floats; 0.5,0.35 favours the top "
                        "of the frame, which suits headshots (default: 0.5,0.5)")
    p.add_argument("--name", help="override the output filename stem")
    p.add_argument("--outdir", type=Path, default=Path("."),
                   help="where to write output (default: current directory)")

    args = p.parse_args()

    try:
        cx, cy = (float(v) for v in args.centering.split(","))
    except ValueError:
        p.error("--centering wants two comma-separated floats, e.g. 0.5,0.35")
    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0):
        p.error("--centering values must be between 0 and 1")
    centering = (cx, cy)

    if args.user:
        src_img = fetch_avatar(args.user, args.width)
        stem_hint = args.user
        default_square = True
    else:
        if not args.input.exists():
            p.error(f"no such file: {args.input}")
        src_img = Image.open(args.input)
        stem_hint = args.input.stem
        default_square = False

    # Work out geometry and the filename badge++ expects.
    if args.icon:
        w = h = ICON_SIZE
        name_for = lambda s: f"icon-{args.icon}{s}"
    elif args.background:
        w, h = SCREEN_W, SCREEN_H
        # No _<width> suffix: badge++ reads that as "draw me full screen".
        name_for = lambda s: f"bg-{args.name or stem_hint}{s}"
    else:
        w = args.width
        if not 1 <= w <= SCREEN_W:
            p.error(f"--width must be between 1 and {SCREEN_W}")
        h = args.height or (w if default_square else SCREEN_H)
        h = min(h, SCREEN_H)
        # The _<width> suffix is load-bearing: badge++ parses it to size the text
        # column, so the variant tag has to sit before it, not after.
        name_for = lambda s: f"{args.name or 'profile'}{s}_{w}"

    args.outdir.mkdir(parents=True, exist_ok=True)

    builds = [("", args.contrast)]
    if args.variants:
        builds += [("-lo", max(args.contrast - 0.4, 0.2)),
                   ("-hi", args.contrast + 0.5)]

    for suffix, contrast in builds:
        img = prepare(src_img, w, h, contrast, not args.no_autocontrast,
                      zoom=args.zoom, centering=centering)
        out = args.outdir / f"{name_for(suffix)}.{args.format}"
        if args.format == "jpg":
            save_jpeg(img, out)
        else:
            save_png(img, out, not args.no_dither)
        print(f"wrote {out}  ({w}x{h}, {args.format})")

    if args.icon:
        print(f"\nCopy into /examples/ on the badge, alongside {args.icon}.py")
        return
    if not args.background:
        text_w = SCREEN_W - 7 - w
        print(f"\nbadge++ will draw this at x={SCREEN_W - w}, y=0 "
              f"and leave {text_w}px for your name/title.")
    print("Copy into /badges/ on the badge, then launch badge++ "
          "and cycle images with UP/DOWN.")


if __name__ == "__main__":
    sys.exit(main())
