# Build a WebP twin next to every shipped site JPEG.
#
#     python make_webp.py            # convert what is stale or missing
#     python make_webp.py --force    # re-encode everything
#
# PORTED 2026-09-01 from kiai-fire/make_webp.py, which is itself adapted from
# foothills-kitchen-bath/make_webp.py. Read those two before changing this one.
#
# WHAT THIS COPY DELIBERATELY DOES NOT CARRY, and why that matters:
#
#   MAX_WIDTH_BY_NAME IS EMPTY HERE, ON PURPOSE. In kiai-fire the per-file caps are
#   MEASURED: serve the folder, read getBoundingClientRect().width on every <img>
#   at 1440 and again at 390, take the larger, double it for a 2x display, never
#   exceed the natural width. Those numbers are facts about THAT page's layout and
#   copying them here would be a guess wearing a measurement's clothes. Until
#   somebody measures this site, only the blanket MAX_WIDTH ceiling applies, which
#   touches a photo only when it is larger than any layout could use.
#
#   Two traps to know before you fill the table in:
#     1. `naturalWidth` READS 0 for a lazy off-screen image in a plain Playwright
#        session, and 0 looks exactly like a broken file. Take the real size from
#        the width= attribute instead.
#     2. AN ENTRY IS KEYED BY FILENAME, so a later photo dropped into the same slot
#        silently inherits a cap measured on a picture it has nothing to do with.
#        Re-measure on any swap.
#
#   THE 1.15 HOST-INFLATION THRESHOLD IS ALSO NOT CARRIED. It is a measured fact
#   about Hostinger re-encoding twin-less JPEGs, and it only applies to a site
#   confirmed to be on that host. The conservative rule is used instead: keep a
#   twin only when it is genuinely smaller than the JPEG.
#
# Re-encoding drops EXIF, which is how the customer-photo GPS rule is met. Do NOT
# add exif=... to the save call to "preserve" anything.
import io, os, re, sys, glob
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(ROOT, "images")
QUALITY = 82
FORCE = "--force" in sys.argv

MAX_WIDTH = 1600            # blanket ceiling; nothing on a page needs more
MAX_WIDTH_BY_NAME = {}      # fill in ONLY from measured rendered widths

# Directories under images/ that never ship. Twins here would be unreachable.
SKIP_DIRS = ("source", "originals", "raw")

# A JPEG THAT CAN NEVER BE AN <img src> MUST NOT GET A TWIN. Social cards are
# referenced by og:image / twitter:image, never by an <img>, and scrapers are the
# one client class you cannot assume supports webp.
# THIS IS A REACHABILITY RULE, NOT A SIZE ONE.
NO_TWIN = ("og-card.jpg", "og.jpg", "og-image.jpg", "social-card.jpg")


def convert(jpg):
    webp = os.path.splitext(jpg)[0] + ".webp"
    if not FORCE and os.path.exists(webp) and os.path.getmtime(webp) >= os.path.getmtime(jpg):
        return "skip", 0, 0
    im = Image.open(jpg)
    cap = MAX_WIDTH_BY_NAME.get(os.path.basename(jpg), MAX_WIDTH)
    if im.width > cap:
        # Never upscale: a cap above the natural width is a no-op, not a stretch.
        im = im.resize((cap, round(im.height * cap / im.width)), Image.LANCZOS)
    im.convert("RGB").save(webp, "WEBP", quality=QUALITY, method=6)
    jn, wn = os.path.getsize(jpg), os.path.getsize(webp)
    if wn >= jn:
        # A "modern format" that ships MORE bytes is a pure regression and no
        # lighthouse score tells you. Leave no .webp behind.
        os.remove(webp)
        return "bigger", jn, jn
    return "ok", jn, wn


def referenced_by_html():
    """Basenames actually reachable from a page, as an <img src> or a <picture>.

    THE SHIPPABLE SET IS DERIVED FROM THE HTML, NOT FROM THE FOLDER. Measured
    2026-09-01 across ten repos: converting everything under images/ produced
    about 141 twins nothing could ever request, because a build keeps every crop
    it CONSIDERED. aarons-contracting had 56 JPEGs on disk and 9 on the page; its
    hero was referenced and the __portrait and __square crops of the same shot
    were not.

    DO NOT TEST THIS WITH A PLAIN `grep <basename> .`. A repo can carry an image
    MANIFEST (aarons-contracting has images/photos.json listing every candidate),
    so a bare filename search reports every crop as referenced and the zero you
    were looking for never appears. Match the markup, not the name.
    """
    names = set()
    pat = re.compile(r'(?:src|srcset)="[^"]*?/?([A-Za-z0-9_\-.]+\.jpg)"', re.I)
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        for f in files:
            if f.endswith((".html", ".htm")):
                try:
                    text = io.open(os.path.join(dirpath, f), encoding="utf-8").read()
                except Exception:
                    continue
                names.update(pat.findall(text))
    return names


def main():
    jpgs = sorted(glob.glob(os.path.join(IMAGES, "**", "*.jpg"), recursive=True))
    jpgs = [j for j in jpgs
            if not any(os.sep + d + os.sep in j for d in SKIP_DIRS)
            and os.path.basename(j) not in NO_TWIN]
    on_page = referenced_by_html()
    if on_page:
        skipped_unreachable = [j for j in jpgs if os.path.basename(j) not in on_page]
        jpgs = [j for j in jpgs if os.path.basename(j) in on_page]
        if skipped_unreachable:
            print("%d JPEGs on disk are on no page, so they get no twin"
                  % len(skipped_unreachable))
        # Sweep twins left behind by an earlier run or by a photo swap.
        for j in skipped_unreachable:
            orphan = os.path.splitext(j)[0] + ".webp"
            if os.path.exists(orphan):
                os.remove(orphan)
                print("  removed unreachable twin:", os.path.basename(orphan))
    else:
        print("WARNING: no <img src> JPEG found in any HTML here, so the "
              "reachability filter is OFF and every JPEG gets a twin. Check that "
              "this is really the site root before trusting the result.")
    if not jpgs:
        raise SystemExit("no shippable JPEGs under images/ - wrong directory?")
    tally = {"ok": 0, "skip": 0, "bigger": 0}
    saved = before = 0
    for j in jpgs:
        state, jn, wn = convert(j)
        tally[state] += 1
        if state == "ok":
            before += jn
            saved += jn - wn
    print("%d shippable JPEGs: %d converted, %d already current, %d discarded for being bigger"
          % (len(jpgs), tally["ok"], tally["skip"], tally["bigger"]))
    if before:
        print("converted set: %.2f MB -> %.2f MB, saved %.2f MB (%.1f%%)"
              % (before / 1048576.0, (before - saved) / 1048576.0,
                 saved / 1048576.0, 100.0 * saved / before))
    else:
        print("nothing converted this run")


if __name__ == "__main__":
    main()
