"""Fixed 1280 x 960 storage controls; no control-label OCR or game input here."""

RARITIES = ((758, 298), (849, 298), (939, 298), (1030, 298),
            (1121, 298), (758, 358), (849, 358))

# 122 x 12 binary silhouette of the game's generic empty-search placeholder
# 「請輸入要搜尋的道具名稱」, calibrated from the supplied 1280 x 960 UI.
# Contains only this public UI label, no inventory or personal screenshot data.
PLACEHOLDER_ROWS = (
    '0000000000000000000000000000000', '0c4108180ff89e1fc120490fe07077c',
    '01f3b61c0160a53fe33c7f8c30fe274', '1ff1ff0607f9ff1fe7e61f8ff304254',
    '0ffbf8060d68ad1fc4e25f8ff07877c', '0df3fe0607f8ff1da4961f8ff0702f4',
    '0df3fe090ff9de1da796d98ff1fe7fc', '1ff3fe098730b33de4947f9ff1826f4',
    '13f3be1087609e3fe4847f8e60826fe', '1333ab2043f89f0846a47f8c30fe284',
    '0c3032400e09a101c3989f90107e21c', '0000000000000000000000000000000')


def search_empty(image):
    """Positive placeholder-shape evidence, not merely absence of white text.

    Entered text/clear failures, blank fields and focused selections fail closed.
    This is fixed UI template matching, never OCR.
    """
    if not filter_open(image):
        return False
    # Typed text and a clear-X occupy the wider field; placeholder is muted gray.
    if fraction(image, (774, 169, 1198, 196),
                lambda r, g, b: min(r, g, b) > 170) > .003:
        return False
    reference = [bit == '1' for row in PLACEHOLDER_ROWS
                 for bit in format(int(row, 16), '0122b')]
    for dy in (-2, 0, 2):
        for dx in (-4, -2, 0, 2, 4):
            crop = image.crop((774+dx,169+dy,1018+dx,193+dy)).convert('L').resize((122,12))
            observed = [value > 68 for value in crop.get_flattened_data()]
            intersection = sum(a and b for a,b in zip(reference, observed))
            union = sum(a or b for a,b in zip(reference, observed))
            if union and intersection / union >= .70:
                return True
    return False


def fraction(image, box, predicate):
    pixels = image.crop(box).convert('RGB').get_flattened_data()
    return sum(predicate(*pixel) for pixel in pixels) / len(pixels)


def green(r, g, b):
    return g > 110 and g > r * 1.4 and g > b * 1.1


def orange(r, g, b):
    return r > 160 and 50 < g < 150 and b < 100 and r > g * 1.4


def yellow(r, g, b):
    return r > 160 and g > 130 and b < 130 and abs(r-g) < 100


def neutral_bright(r, g, b):
    return min(r, g, b) > 165 and max(r, g, b)-min(r, g, b) < 50


def storage_kind(image):
    """Require both storage panels and live top controls, excluding dim overlays."""
    if image.size != (1280, 960):
        return None
    if fraction(image, (1125, 20, 1170, 55), green) < .55:
        return None
    if fraction(image, (42, 135, 73, 171), green) < .08:
        return None
    left = fraction(image, (45, 390, 57, 880),
                    lambda r, g, b: 25 < r < 80 and 25 < g < 80 and 35 < b < 95)
    right = fraction(image, (680, 390, 695, 880),
                     lambda r, g, b: 10 < r < 45 and 15 < g < 55 and 20 < b < 65)
    if min(left, right) < .8:
        return None
    if fraction(image, (155, 24, 235, 52), orange) > .55:
        return 'shared'
    if fraction(image, (42, 24, 115, 52), yellow) > .55:
        return 'normal'
    return None


def all_category(image):
    return fraction(image, (48, 81, 100, 111), orange) > .55


def filter_open(image):
    if image.size != (1280, 960):
        return False
    return (fraction(image, (1000, 881, 1195, 922), green) > .7
            and fraction(image, (700, 510, 720, 840),
                         lambda r, g, b: 20 < r < 50 and 25 < g < 60 and 30 < b < 75) > .9
            and fraction(image, (800, 159, 1170, 167),
                         lambda r, g, b: 10 < r < 40 and 15 < g < 50 and 20 < b < 60) > .8)


def rarity_selected(image, index):
    """Read the white outline above/below the text, never the chip's fill color.

    Partial outlines are uncertain (including a cursor obscuring one edge).
    """
    if not filter_open(image):
        raise RuntimeError('無法確認稀有度篩選視窗；已停止。')
    x, y = RARITIES[index]
    top = fraction(image, (x-15, y-23, x+15, y-16), neutral_bright)
    bottom = fraction(image, (x-15, y+17, x+15, y+24), neutral_bright)
    if min(top, bottom) > .18:
        return True
    if max(top, bottom) < .05:
        return False
    raise RuntimeError('稀有度勾選外框不明確；已停止，請關閉篩選後重試。')


def only_general(image):
    return tuple(rarity_selected(image, i) for i in range(len(RARITIES))) == (True, False, False, False, False, False, False)
