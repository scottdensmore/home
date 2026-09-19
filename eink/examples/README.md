# Example Apps

This directory contains example apps that demonstrate how to interact with the `badger2040` library & picographics API.

Note that while each example app is in its own directory, all of the files for each app will need to be copied directly into the `/examples/` directory to correctly show up as an app in the launcher menu.

## Badge++
Just like the badge app that came with your Badger 2350, but with a few extra features to make sure your badge is truly one of a kind.

Installation instructions:
1. Run the accompanying `profile_pic_download.py` script to generate a few images to try out on your badge.
2. Copy the resulting images to the `/badges/` directory on your badge.
3. Copy the `badge++.py` and `icon-badge++.jpg` files to the `/example/` directory on your badge just like any other app.

How to customize your badge:
- A/B: Cycle back and forth through the font options.
- UP/DOWN: Cycle back and forth through every badge and image in the `/badges/` directory.

Find the combination that looks best to you!

### Holding more than one badge

Badge++ can hold several completely different badges -- a personal one, a work one -- and UP/DOWN scrolls through all of them without leaving the app.

A *card* is one badge: a `/badges/<name>.txt` holding the text, plus any `/badges/<name>-*` or `/badges/<name>_*` images that belong with it. Badge++ walks every (card, image) pair in order, so scrolling moves through your images *and* your different badges. A card with no images still renders as a text-only badge.

```
/badges
  badge.txt                   <- your default badge
  badge-1-headshot_100.png       both images belong to badge.txt
  badge-2-avatar_100.png
  work.txt                    <- a second badge, different title
  work-logo_100.png
```

That gives four slides: headshot, avatar, then the work badge with its logo. To add another badge, drop in a new `.txt` and name its images to match -- no code change. Cards are ordered by filename, as are the images within a card, so a numeric prefix pins the order.

The pixel width in an image filename (`badge-2-avatar_100.png`) is what reserves space for your text -- a file with no `_<width>` suffix is drawn full screen as a background instead.

To generate correctly sized and dithered images, use [`tools/badge_image.py`](../tools/badge_image.py):

```bash
# your GitHub avatar
python3 tools/badge_image.py --user <handle> --width 100 --format png

# a photo, cropped tighter on the face
python3 tools/badge_image.py --input headshot.jpg --width 100 --format png \
    --zoom 1.3 --centering 0.5,0.35

# compare contrast settings before committing to one
python3 tools/badge_image.py --input headshot.jpg --width 100 --variants
```

### Playful GitHub badges

[`tools/github_card.py`](../tools/github_card.py) builds two extras from a GitHub handle: your avatar over a contribution grid, and your avatar over a QR code pointing at your profile.

```bash
python3 tools/github_card.py --user <handle> --card github
python3 tools/github_card.py --user <handle> --card github --only grid --weeks 26
```

It writes `github-1-grid_100.png` and `github-2-qr_100.png`, ready to sit in `/badges/` next to a `github.txt`. The badge has no WiFi, so the contribution data is fetched and rendered on your computer and baked into the image -- re-run the tool to refresh it.

The QR needs the `qrcode` package (`pip install qrcode`); pass `--only grid` to skip it.

`--dither` picks how grey becomes black-and-white, which matters more than it sounds at this size:

| mode | look |
| --- | --- |
| `fs` | Floyd-Steinberg, the default. Softest, holds the most mid-tone detail. |
| `atkinson` | Propagates only 6/8 of the error, so it clips toward pure black and white. Crisper and more graphic; good for faces. |
| `bayer` | Ordered 8x8 threshold, a regular retro crosshatch. |
| `halftone` | Newsprint dot screen. Striking on graphics, but too coarse for a face in a 100px slot. |
| `none` | Hard threshold. Right for artwork that is already pure black and white. |

`--fade PX` ramps the left edge of an image to white so a wide one can bleed toward the text rather than hard-edging against it. It only helps for photos with a real background -- on a subject shot against white there is nothing to fade.

Use `--format png` on a Universe 2024 badge: PNG is lossless, so the image can be dithered to 1-bit up front. On a 2023 badge use `--format jpg`, which ships a grayscale JPEG and lets the badge dither it -- pre-dithering then JPEG-compressing destroys the pattern.

_Note:_ Badge++ detects whether the badge has `pngdec` and ignores PNG images when it does not, so the same file runs on a Universe 2023 badge (RP2040, JPEG only) and a 2024 one (RP2350). Use `--format jpg` for a 2023 badge.

## Copilot
Have some time before your next session? Read this guide to help you get the most out of GitHub Copilot.

How to use:
- A: Change font size
- B: Change font
- UP/DOWN: Scroll text

## Dino
Forked from [niutech/dino-badger2040](https://github.com/niutech/dino-badger2040). This is the Dino Game from Google Chrome coded in MicroPython and ported to [Pimoroni Badger 2040](https://shop.pimoroni.com/products/badger-2040) e-ink device based on [RP2040](https://www.raspberrypi.com/products/rp2040/) MCU. It is based on [dino-game-micropython](https://github.com/danielkurek/dino-game-micropython) by Daniel Kurek. [Demo video](https://twitter.com/niu_tech/status/1598804559270486033).

## Hello
There's nothing like a classic. This app will display "Hello Universe!" on the screen.

## Life
The Game of Life by @link- forked from [glich-stream/gol-badger-2350](https://github.com/glich-stream/gol-badger-2350)

How to play:
- A: Reset the grid (press and HOLD for 2s)
- B: Pause/Resume the simulation (press and HOLD for 2s)
- UP: Increase the refresh rate (press and HOLD for 2s)
- DOWN: Decrease the refresh rate (press and HOLD for 2s)

## Wordle
Forked from [makew0rld/wordle-badger2040](https://github.com/makew0rld/wordle-badger2040) and lightly updated to run on the latest version of the picographics library.

How to play:
1. Use the *B* and *C* buttons to cycle through the alphabet.
2. Use the arrow buttons to move between squares.
3. Press the *A* button to submit a word.

# Other Credits
- @martinwoodward & @ashleymcnamara - inception, hardware, inspiration
- @peckjon & @tbries - tutorials, integration
- @alliekpeck - testing