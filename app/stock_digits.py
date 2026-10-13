"""Conservative visual corroboration for truncated storage-count OCR."""
from PIL import Image, ImageChops


def white_mask(raw, threshold, spread=20):
    """White pixels on black; use Pillow operations instead of Python RGB loops.

    A None spread preserves the quantity field's existing brightness-only rule.
    """
    red, green, blue = raw.convert('RGB').split()
    darkest = ImageChops.darker(ImageChops.darker(red,green),blue)
    bright = darkest.point(lambda value: 255 if value > threshold else 0)
    if spread is None:
        return bright
    lightest = ImageChops.lighter(ImageChops.lighter(red,green),blue)
    neutral = ImageChops.subtract(lightest,darkest).point(
        lambda value: 255 if value < spread else 0)
    return ImageChops.multiply(bright,neutral)


def digit_strip(raw, threshold, *, allow_single=False):
    """Return a neutral-white, aligned digit strip and its component count.

    This is count evidence only, not a general icon/text segmenter. Reject
    ambiguous shapes instead of trimming them into a plausible smaller number.
    """
    pixels = white_mask(raw,threshold).load()
    points = {(x, y) for y in range(raw.height) for x in range(raw.width)
              if pixels[x, y]}
    components = []
    while points:
        seed = points.pop()
        pending, component = [seed], [seed]
        while pending:
            x, y = pending.pop()
            for point in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
                if point in points:
                    points.remove(point)
                    pending.append(point)
                    component.append(point)
        if len(component) >= 6:
            components.append(component)
    # A wide icon highlight touching the crop's top edge can sit above digits
    # (e.g. a fried egg). Exclude only shapes too wide to be one glyph and
    # ending well above the complete number baseline. Keep small components,
    # including thin leading ones, so none can silently disappear.
    baseline = max((max(y for x,y in c)+1 for c in components), default=0)
    highlights = [c for c in components if (
        min(y for x,y in c) == 0
        and ((max(x for x,y in c)-min(x for x,y in c)+1 > 20
              and len(c) > 150 and max(y for x,y in c)+1 <= baseline-2)
             or (max(y for x,y in c)+1 < 8
                 and max(y for x,y in c)+1 <= baseline-8)))]
    # A bottle highlight can leave a short detached fleck inside its footprint.
    # Exclude only flecks too short to be a digit and well above the baseline;
    # unrelated noise and every complete leading glyph still cause rejection.
    components = [c for c in components if c not in highlights and not (
        max(y for x,y in c)-min(y for x,y in c)+1 <= 8
        and max(y for x,y in c)+1 <= baseline-6
        and any(min(x for x,y in h)-2 <= min(x for x,y in c)
                and max(x for x,y in c) <= max(x for x,y in h)+2
                for h in highlights))]
    # Keep every remaining meaningful component.
    if not (1 if allow_single else 2) <= len(components) <= 6:
        return None
    boxes = [(min(x for x,y in c), min(y for x,y in c),
              max(x for x,y in c)+1, max(y for x,y in c)+1) for c in components]
    boxes.sort()
    if any(not (2 <= r-l <= 20 and 8 <= b-t <= 24) for l,t,r,b in boxes):
        return None
    if (max(b for l,t,r,b in boxes)-min(b for l,t,r,b in boxes) > 2
            or max(t for l,t,r,b in boxes)-min(t for l,t,r,b in boxes) > 2
            or any(not 0 <= second[0]-first[2] <= 5
                   for first, second in zip(boxes, boxes[1:]))):
        return None
    left, top = min(b[0] for b in boxes), min(b[1] for b in boxes)
    right, bottom = max(b[2] for b in boxes), max(b[3] for b in boxes)
    if left <= 0 or top <= 0 or right >= raw.width or bottom >= raw.height:
        return None  # Clipped digits cannot corroborate their complete count.
    strip = Image.new('L', (right-left+8, bottom-top+8), 'white')
    for component in components:
        for x,y in component:
            strip.putpixel((x-left+4,y-top+4), 0)
    return strip, len(components), (left,top,right,bottom)


def single_digit_strips(image, box):
    """Four corroborating masks, or None; never trim a possible leading digit.

    Shift downward to avoid introducing more icon pixels above a short count.
    Both crops must retain the whole glyph, at the same absolute coordinates.
    """
    left, top, right, bottom = box
    if left < 0 or top < 0 or right > image.width or bottom+4 > image.height:
        return None
    strips = []
    bounds = []
    for offset in (0, 4):
        raw = image.crop((left, top+offset, right, bottom+offset))
        for threshold in (160, 180):
            evidence = digit_strip(raw, threshold, allow_single=True)
            if evidence is None or evidence[1] != 1:
                return None
            strip, _, (x, y, r, b) = evidence
            strips.append(strip)
            bounds.append((x, y+offset, r, b+offset))
    if any(any(abs(a-b) > 2 for a,b in zip(bounds[0],other)) for other in bounds[1:]):
        return None
    return strips
