"""Conservative visual corroboration for truncated storage-count OCR."""
from PIL import Image


def digit_strip(raw, threshold):
    """Return a neutral-white, aligned digit strip and its component count.

    This is only a conflict fallback, not a general icon/text segmenter. Reject
    ambiguous shapes instead of trimming them into a plausible smaller number.
    """
    raw = raw.convert('RGB')
    pixels = raw.load()
    points = {(x, y) for y in range(raw.height) for x in range(raw.width)
              if min(pixels[x, y]) > threshold
              and max(pixels[x, y])-min(pixels[x, y]) < 20}
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
    components = [c for c in components if not (
        min(y for x,y in c) == 0
        and ((max(x for x,y in c)-min(x for x,y in c)+1 > 20
              and len(c) > 150 and max(y for x,y in c)+1 <= baseline-2)
             or (max(y for x,y in c)+1 < 8
                 and max(y for x,y in c)+1 <= baseline-8)))]
    # Keep every remaining meaningful component.
    if not 2 <= len(components) <= 6:
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
