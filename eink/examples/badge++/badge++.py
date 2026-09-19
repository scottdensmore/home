import badger2040
import badger_os
import jpegdec
import os
import re

# Global Constants
# Measurements are in pixels
WIDTH = badger2040.WIDTH
HEIGHT = badger2040.HEIGHT

LEFT_PADDING = 7
NAME_HEIGHT = 45
LASTNAME_HEIGHT = 30
DETAILS_HEIGHT = 18
LINE_SPACING = 2
DETAILS_TEXT_SIZE = 2

BADGE_DIR = "/badges"
DEFAULT_CARD = "badge"

# A "card" is one badge: a /badges/<name>.txt holding the text, plus any
# /badges/<name>-*.png or /badges/<name>_*.jpg images that belong with it.
# UP/DOWN walks every (card, image) pair, so one scroll moves through your
# images *and* your different badges. Add a badge by dropping in a new .txt
# and naming its images to match; no code change needed.
#
# The pixel width in an image filename ("gcloud-logo_100.png") is what reserves
# space for the text. An image with no _<width> is drawn full screen instead.

FONTS = ["bitmap8", "serif", "sans", "gothic"]
THICKNESSES = [1, 4, 4, 2]
SIZE_ADJ = [1, 0.3, 0.3, 0.3]

# Written to <DEFAULT_CARD>.txt if /badges holds no .txt at all.
# Event, first name, last name, company, title, pronouns, handle - one per line.
DEFAULT_TEXT = """Universe 2024
Mona Lisa
Octocat
GitHub
Company Mascot
she/her
@mona
"""

# ------------------------------
#      Utility functions
# ------------------------------


# Reduce the size of a string until it fits within a given width
def truncate_string(text, text_size, width):
    while True:
        length = display.measure_text(text, text_size)
        if length > 0 and length > width:
            text = text[:-1]
        else:
            text += ""
            return text


# Shrink text until it fits the column, the way the name lines do, and only
# chop it as a last resort. Chopping first loses whole words off a job title
# that would have fitted a size down.
def fit_text(text, size, width, floor=0.4, step=0.05):
    while size > floor and display.measure_text(text, size) > width:
        size -= step
    return truncate_string(text, size, width), size


# Extract the width of the image based on the file name.
# It should be just before the extenstion and follow after an underscore.
def extract_image_width_from_filename(filename):
    match = re.search(r'_(\d+)\.', filename)
    if match:
        return int(match.group(1))
    return 0


def is_image(name):
    if name.endswith(".jpg"):
        return True
    return name.endswith(".png") and PNG_SUPPORTED


def discover_slides():
    """Every (card, image) pair in /badges, in display order.

    A card with no images still gets one text-only slide, so a badge always
    renders even before you have artwork for it.
    """
    try:
        entries = sorted(os.listdir(BADGE_DIR))
    except OSError:
        entries = []

    cards = [e[:-4] for e in entries if e.endswith(".txt")]
    if not cards:
        with open(f"{BADGE_DIR}/{DEFAULT_CARD}.txt", "w") as f:
            f.write(DEFAULT_TEXT)
            f.flush()
        cards = [DEFAULT_CARD]
        entries = sorted(os.listdir(BADGE_DIR))

    slides = []
    for card in cards:
        # Require a separator so a card named "badge" cannot swallow the
        # images belonging to a card named "badgeX".
        images = [e for e in entries
                  if (e.startswith(card + "-") or e.startswith(card + "_"))
                  and is_image(e)]
        if images:
            for image in images:
                slides.append((card, image))
        else:
            slides.append((card, None))
    return slides


def read_card(card):
    """Parse /badges/<card>.txt into the fields the badge draws."""
    try:
        with open(f"{BADGE_DIR}/{card}.txt", "r") as f:
            lines = f.read().split("\n")
    except OSError:
        lines = DEFAULT_TEXT.split("\n")
    while len(lines) < 7:
        lines.append("")

    first_name, last_name = lines[1], lines[2]
    title, pronouns, handle = lines[4], lines[5], lines[6]

    # If the first name is empty, use the last name as the first name
    if first_name.strip() == "":
        first_name = last_name
        last_name = ""

    # Deliberately not truncated here: how much fits depends on the font and on
    # the image width, and both change as you cycle. draw_badge() does it.
    return first_name, last_name, title, pronouns, handle


_card_cache = {}


def card_text(card):
    if card not in _card_cache:
        _card_cache[card] = read_card(card)
    return _card_cache[card]


# ------------------------------
#      Drawing functions
# ------------------------------

# Draw the badge, including user text
def draw_badge():
    card, target_image = SLIDES[state["slide_idx"]]
    first_name, last_name, title, pronouns, handle = card_text(card)

    display.set_pen(15)
    display.clear()

    # Draw the background. A text-only card still needs a usable TEXT_WIDTH,
    # so set it before anything that can fail.
    TEXT_WIDTH = WIDTH - LEFT_PADDING
    if target_image is not None:
        try:
            image_size = extract_image_width_from_filename(target_image)
            TEXT_WIDTH = WIDTH - LEFT_PADDING - image_size

            # If no image was pulled from the name, it must be the background.
            if(image_size == 0):
                image_size = WIDTH

            image_path = f"{BADGE_DIR}/{target_image}"
            print(image_path)
            if image_path.endswith(".png"):
                png.open_file(image_path)
                png.decode(WIDTH - image_size, 0)
            else:
                jpeg.open_file(image_path)
                jpeg.decode(WIDTH - image_size, 0)
        except OSError:
            print("Badge background error")

    # Draw the firstname.
    display.set_pen(0)
    display.set_font(FONTS[state["font_idx"]])
    display.set_thickness(THICKNESSES[state["font_idx"]])

    size_adjustment = SIZE_ADJ[state["font_idx"]]
    vertical_adjustment = (int(1 / size_adjustment) - 1) * 5

    # Draw the firstname, scaling it based on the available width
    display.set_pen(0)
    name_size = 4 * size_adjustment  # A sensible starting scale
    while True:
        name_length = display.measure_text(first_name, name_size)
        if name_length >= TEXT_WIDTH and name_size >= 0.1:
            name_size -= 0.01
        else:
            display.text(first_name, LEFT_PADDING, 5 + vertical_adjustment, TEXT_WIDTH, name_size)
            break

    # Draw the lastname, scaling it based on the available width
    display.set_pen(0)
    lastname_size = 3 * size_adjustment  # A sensible starting scale
    while True:
        lastname_length = display.measure_text(last_name, lastname_size)
        if lastname_length >= TEXT_WIDTH and lastname_size >= 0.1:
            lastname_size -= 0.01
        else:
            display.text(last_name, LEFT_PADDING, NAME_HEIGHT + LINE_SPACING + vertical_adjustment, TEXT_WIDTH, lastname_size)
            break

    # Draw the title and pronouns, aligned to the bottom & truncated to fit on one line
    display.set_pen(0)
    display.set_thickness(int(THICKNESSES[state["font_idx"]] / 2))

    # Fit against the column actually left over, measured in the font that is
    # selected right now. Both change as you cycle images and fonts.
    details_size = DETAILS_TEXT_SIZE * size_adjustment

    # Title
    title_line, title_size = fit_text(title, details_size, TEXT_WIDTH)
    display.text(title_line, LEFT_PADDING,
                 HEIGHT - (DETAILS_HEIGHT * 2) - LINE_SPACING - 2,
                 TEXT_WIDTH, title_size)

    # Show pronouns if given, otherwise show any handle or blank if neither
    second = pronouns if (pronouns and pronouns.strip() != "") else handle
    second_line, second_size = fit_text(second, details_size, TEXT_WIDTH)
    display.text(second_line, LEFT_PADDING, HEIGHT - DETAILS_HEIGHT,
                 TEXT_WIDTH, second_size)

    display.update()


# ------------------------------
#        Program setup
# ------------------------------

# Global variables
state = {
    "font_idx": 0,
    "slide_idx": 0
}
badger_os.state_load("badge++", state)

# Create a new Badger and set it to update NORMAL
display = badger2040.Badger2040()
display.led(128)
display.set_update_speed(badger2040.UPDATE_NORMAL)

jpeg = jpegdec.JPEG(display.display)

# Universe 2023 badges (RP2040) have no pngdec at all, while 2024 ones do.
# Detect it rather than making the user flip a flag per badge.
try:
    import pngdec
    png = pngdec.PNG(display.display)
    PNG_SUPPORTED = True
except ImportError:
    png = None
    PNG_SUPPORTED = False
    print("no pngdec on this badge; PNG images will be ignored")

SLIDES = discover_slides()
TOTAL_SLIDES = len(SLIDES)

# Avoid being in an invalid state if badges or images were removed.
if state["slide_idx"] >= TOTAL_SLIDES:
    state["slide_idx"] = 0

# ------------------------------
#       Main program loop
# ------------------------------

changed = False
draw_badge()

while True:
    # Sometimes a button press or hold will keep the system
    # powered *through* HALT, so latch the power back on.
    display.keepalive()

    # Step back through the badges and their images.
    if display.pressed(badger2040.BUTTON_DOWN):
        state["slide_idx"] = (state["slide_idx"] - 1) % TOTAL_SLIDES
        changed = True

    # Step forward through the badges and their images.
    if display.pressed(badger2040.BUTTON_UP):
        state["slide_idx"] = (state["slide_idx"] + 1) % TOTAL_SLIDES
        changed = True

    # Was the font requested to be changed?
    if display.pressed(badger2040.BUTTON_A):
        state["font_idx"] += 1
        if (state["font_idx"] >= len(FONTS)):
            state["font_idx"] = 0

        changed = True

    # Was the font requested to be changed?
    if display.pressed(badger2040.BUTTON_B):
        state["font_idx"] -= 1
        if (state["font_idx"] < 0):
            state["font_idx"] = len(FONTS) - 1

        changed = True

    if changed:
        draw_badge()
        badger_os.state_save("badge++", state)
        changed = False

    display.halt()
