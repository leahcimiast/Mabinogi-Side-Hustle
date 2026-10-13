"""Standalone, left-panel-only storage debugging; never transfers items."""
from collections import Counter
from statistics import median
from dataclasses import dataclass, field
import re
from PIL import Image, ImageChops, ImageOps, ImageStat, ImageDraw, ImageFont
from . import capture
from .flow_vision import Vision
from .inventory_recognition import compact, line_text
from .name_candidates import distance
from .ocr_aliases import canonical_material


def requirements(entries, cycles):
    if type(cycles) is not int or not 1 <= cycles <= 6:
        raise ValueError('請選擇 1 至 6 個交付循環。')
    totals = Counter()
    for entry in entries:
        totals[entry.material] += entry.quantity * 3 * cycles
    return dict(totals)


@dataclass(frozen=True)
class StockCell:
    column: int
    y: int
    name: str | None
    count: int | None
    uncertain: bool = False


@dataclass
class StockResult:
    cells: dict = field(default_factory=dict)
    complete: bool = False
    note: str = '尚未完成掃描'
    finished_at: str = ''

    def add(self, cells, offset):
        for cell in cells:
            position = cell.y + offset
            nearby = [key for key in self.cells
                      if key[0] == cell.column and abs(key[1] - position) <= 8]
            if len(nearby) > 1:
                raise RuntimeError('堆疊位置配對不唯一；停止盤點。')
            key = nearby[0] if nearby else (cell.column, position)
            old = self.cells.get(key)
            # A later OCR miss/conflict must never erase a confirmed physical stack.
            if old is not None and old.name is not None and old.count is not None and not old.uncertain:
                continue
            self.cells[key] = cell

    def totals(self):
        totals = Counter()
        for cell in self.cells.values():
            if not cell.uncertain and cell.name is not None and cell.count is not None:
                totals[cell.name] += cell.count
        return totals

    def uncertain_materials(self, entries, cycles):
        """Keep confidence separate from the numeric, observed-stock shortage."""
        totals = self.totals()
        unidentified = any(cell.uncertain and cell.name is None for cell in self.cells.values())
        uncertain = {cell.name for cell in self.cells.values()
                     if cell.uncertain or cell.count is None}
        return {name for name, needed in requirements(entries, cycles).items()
                if totals[name] < needed and
                (not self.complete or unidentified or name in uncertain)}

    def rows(self, entries, cycles):
        totals = self.totals()
        return [(name, needed, totals[name], max(0, needed-totals[name]))
                for name, needed in requirements(entries, cycles).items()]


def panel(image):
    return image.crop((57, 275, 626, 950)).convert('RGB').resize((190, 675))


def displacement(before, after, direction):
    """Unique visual overlap supplies offset; identical OCR names never do."""
    a, b = panel(before), panel(after)
    def error(delta):
        n = abs(delta)
        first = a.crop((0, n if delta >= 0 else 0, 190, 675 if delta >= 0 else 675-n))
        second = b.crop((0, 0 if delta >= 0 else n, 190, 675-n if delta >= 0 else 675))
        delta = ImageChops.difference(first, second).convert('L')
        # Glow animation and the fading top edge affect only some cells. Compare
        # six columns separately; a majority must support the same displacement.
        scores = [ImageStat.Stat(delta.crop((x, 25, x+28, delta.height-15))).mean[0]
                  for x in (1,33,65,97,129,161)]
        return median(scores)
    candidates = [(error(n*-direction), n*-direction) for n in range(541)]
    best_error, best = min(candidates)
    if best == 0 and best_error < 1:
        # Still require visible content; a uniform/blank panel proves nothing.
        if max(ImageStat.Stat(a).stddev) > 8:
            return 0
    alternatives = [score for score, n in candidates if abs(n-best) > 8]
    if best_error > 12 or (alternatives and min(alternatives) < best_error+1.5):
        raise RuntimeError('捲動影像無法唯一對齊；未確認完整庫存，請重新盤點。')
    return best


def parse_count(words):
    text = compact(line_text(words))
    if re.fullmatch(r'[0-9]+', text) and int(text) > 0:
        return int(text)
    return None


class StockVision:
    def __init__(self, vision, entries, log=lambda message: None):
        self.log = log
        self.vision = vision
        self.names = set(requirements(entries, 1))

    @staticmethod
    def iron_icon(image, box):
        """Corroborate an iron-name candidate using its blue icon, above digits."""
        x, y, right, _ = box
        icon = image.crop((x+12, y-65, right-12, y-31)).convert('RGB')
        pixels = list(icon.get_flattened_data())
        blue = [p for p in pixels if p[2] > 65 and p[2] > p[0]*1.35
                and p[2] > p[1]*1.08]
        dark = sum(p[0] < 65 and p[1] < 150 for p in blue)
        return len(blue) >= len(pixels)*.10 and dark >= len(pixels)*.04

    def resolve_name(self, readings):
        # Specific full-label OCR confusions reproduced from storage screenshots.
        # Only the shared reviewed spellings apply; grade/plus markers stay distinct.
        readings = readings | {canonical_material(text) for text in readings}
        exact = readings & self.names
        conflict = len(exact) > 1 or any(
            other != name and (other == name+'+' or other+'+' == name
                or (name == '羊毛' and other.endswith('羊毛'))
                or (name == '馬鈴薯' and ('烤' in other or '整' in other)))
            for name in exact for other in readings)
        if conflict:
            return None
        if len(exact) == 1:
            return next(iter(exact))
        candidates = set()
        for text in readings:
            ranked = []
            for target in self.names:
                if target == '羊毛' or text.count('+') != target.count('+'):
                    continue
                if target.startswith('高級') and not ('高' in text or '級' in text):
                    continue
                if target == '鐵礦石' and not text.startswith('鐵'):
                    continue
                # Do not turn a cooked potato or grade-prefixed material into raw stock.
                if target == '馬鈴薯' and any('烤' in raw or '整' in raw for raw in readings):
                    continue
                score = 1-distance(text,target)/max(len(text),len(target))
                if score >= .66:
                    ranked.append((score,target))
            ranked.sort(reverse=True)
            if ranked and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.08):
                candidates.add(ranked[0][1])
        if len(candidates)!=1:
            return None
        candidate=next(iter(candidates))
        if any(raw==candidate+'+' or raw+'+'==candidate for raw in readings):
            return None
        return candidate

    def cells(self, image, check=lambda: None, locked=None):
        locked = locked or {}
        # Existing read-only name helpers crop x=57..626; never call observe_storage.
        found = self.vision.storage_names(image)
        found += self.vision.storage_names_retry(image)
        check()
        boxes = getattr(self.vision, '_storage_boxes', [])
        if not boxes:
            raise RuntimeError('無法定位保管箱格位；不將未辨識畫面視為空庫存。')
        # Retry isolated name crops only for cells lacking a unique identity.
        retry = []
        for box in boxes:
            x,y,right,bottom = box
            if any(col==round((x-57)/95) and abs(position-y)<=8 for col,position in locked):
                continue
            readings = {label.text for label in found
                        if abs(label.box[0]-x)<5 and abs(label.box[1]-(y-65))<5}
            if not self.resolve_name(readings) and not readings & self.names:
                retry.append(box)
        from .flow_vision import Label
        for start in range(0,len(retry),6):
            group = retry[start:start+6]
            crops = []
            for x,y,right,bottom in group:
                raw = image.crop((max(0,x-3),y-5,min(639,right+2),bottom+5))
                crops.extend([ImageOps.expand(im.resize((im.width*3,im.height*3)),20,'white')
                              for im in (raw,ImageOps.autocontrast(raw.convert('L')))])
            for i,words in enumerate(self.vision.session.recognize_many(crops)):
                text=compact(line_text(words))
                if re.fullmatch(r'[\u3400-\u9fff+]+',text):
                    x,y,right,bottom=group[i//2]
                    found.append(Label(text,(x,y-65,right,bottom-35)))
            check()
        # Short labels can lose a character at 3x; retry the same cell at 2x.
        short_retry=[]
        for box in retry:
            x,y,right,bottom=box
            readings={label.text for label in found
                      if abs(label.box[0]-x)<5 and abs(label.box[1]-(y-65))<5}
            if not self.resolve_name(readings) and any(0<len(text)<=2 for text in readings):
                short_retry.append(box)
        for start in range(0,len(short_retry),6):
            group=short_retry[start:start+6];crops=[]
            for box in group:
                raw=image.crop(box)
                crops.extend(ImageOps.expand(im.resize((im.width*2,im.height*2)),20,'white')
                             for im in (raw,ImageOps.autocontrast(raw.convert('L'))))
            for i,words in enumerate(self.vision.session.recognize_many(crops)):
                text=compact(line_text(words))
                if re.fullmatch(r'[\u3400-\u9fff+]+',text):
                    x,y,right,bottom=group[i//2]
                    found.append(Label(text,(x,y-65,right,bottom-35)))
            check()
        cells, targets = [], []
        for box in boxes:
            x, y, right, bottom = box
            if y-65 < 270 or bottom > 955: continue
            readings = {label.text for label in found
                        if abs(label.box[0]-x) < 5 and abs(label.box[1]-(y-65)) < 5}
            exact = readings & self.names
            conflict = len(exact) > 1 or any(
                other != name and (other == name+'+' or other+'+' == name
                    or (name == '羊毛' and other.endswith('羊毛')))
                for name in exact for other in readings)
            prior = next((cell for (column,position),cell in locked.items()
                          if column==round((x-57)/95) and abs(position-y)<=8),None)
            if prior is not None:
                cells.append(StockCell(prior.column,y,prior.name,prior.count,False))
                continue
            name = self.resolve_name(readings)
            if name == '鐵礦石' and not self.iron_icon(image, box):
                self.log('鐵礦石圖示未通過深藍色核對；保留待核。')
                cells.append(StockCell(round((x-57)/95), y, name, None, True))
                continue
            if name and not conflict:
                if name not in readings:
                    self.log('品名比對：'+'／'.join(sorted(readings))+' → '+name)
                targets.append((len(cells), (x+25, y-40, right, y-5)))
                cells.append(StockCell(round((x-57)/95), y, name, None, True))
            else:
                icon = image.crop((x+12, y-65, right-12, y-12)).convert('RGB')
                occupied = sum(max(p)-min(p) > 28 or min(p) > 100
                               for p in icon.get_flattened_data()) > 40
                possible = any(text not in self.names and
                               1-distance(text, target)/max(len(text), len(target)) >= .66
                               for text in readings for target in self.names)
                # Known grade/plus items remain distinct, not fuzzy substitutions.
                distinct = bool(readings) and all(text in ('高級羊毛','級羊毛') or
                            any(text == target+'+' or text+'+' == target for target in self.names)
                            for text in readings)
                uncertain = conflict or (possible and not distinct) or (not readings and occupied)
                cells.append(StockCell(round((x-57)/95), y, None, None, uncertain))
        for start in range(0, len(targets), 2):
            group = targets[start:start+2]
            crops = []
            for _, box in group:
                gray = image.crop(box).convert('L')
                for threshold in (150, 185, 215):
                    digit = ImageOps.invert(gray.point(lambda p: 255 if p > threshold else 0))
                    canvas = Image.new('RGB', (420, 172), 'white')
                    ImageDraw.Draw(canvas).text((8, 53), 'Qty', font=ImageFont.load_default(size=34), fill='black')
                    canvas.paste(digit.resize((digit.width*4, digit.height*4)), (120, 16))
                    crops.append(ImageOps.expand(digit.resize((digit.width*4, digit.height*4)),16,'white'))
                    crops.append(canvas)
                # Raw/gray retain thin digits that thresholding can erase (e.g. 77).
                for raw in (image.crop(box), ImageOps.autocontrast(image.crop(box).convert('L'))):
                    crops.append(ImageOps.expand(raw.resize((raw.width*3,raw.height*3)),16,'white'))
            results = []
            for batch_start in range(0,len(crops),12):
                results.extend(self.vision.session.recognize_many(crops[batch_start:batch_start+12]))
                check()
            for index, (slot, _) in enumerate(group):
                values = []
                for method, words in enumerate(results[index*8:index*8+8]):
                    left = 120 if method < 6 and method % 2 else 16
                    width,height = (207,105) if method>=6 else (276,140)
                    values.append(parse_count([w for w in words if w['x'] >= left and w['y'] >= 16
                                  and w['h'] >= 12 and w['x']+w['w'] <= left+width and w['y']+w['h'] <= 16+height]))
                votes = Counter(value for value in values if value is not None)
                ranked = votes.most_common()
                count = (ranked[0][0] if ranked and ranked[0][1]>=2
                         and (len(ranked)==1 or ranked[0][1]>ranked[1][1]) else None)
                cell = cells[slot]
                # Correlated missing-leading-digit errors must not win a vote.
                if any(a != b and str(a).endswith(str(b)) for a in votes for b in votes):
                    count = self.retry_conflicting_count(image, group[index][1], check, votes)
                    if count is not None:
                        self.log(f'數量字形核對：{cell.name} × {count}（原讀值 {values}）')
                if count is None and len(votes) <= 1:
                    if not votes:
                        count = self.retry_missing_count(image, group[index][1], check)
                    if count is None:
                        count = self.retry_neutral_count(image, group[index][1], check,
                                                         next(iter(votes), None))
                    if count is not None:
                        self.log(f'數量局部補讀：{cell.name} × {count}')
                if count is None:
                    count = self.retry_digit_count(image, group[index][1], check, votes)
                    if count is not None:
                        self.log(f'數量完整字形補讀：{cell.name} × {count}')
                if count is None:
                    self.log(f'數量待核：{cell.name}，各方法讀值 {values}')
                cells[slot] = StockCell(cell.column, cell.y, cell.name, count, count is None)
        return cells


    def retry_digit_count(self, image, box, check, votes):
        """Corroborate complete glyphs at two positions and two thresholds."""
        from .stock_digits import digit_strip
        values = list(votes)
        if len(values) > 1 and not all(
                str(max(values, key=lambda n: len(str(n)))).endswith(str(n))
                for n in values):
            return None
        left, top, right, bottom = box
        confirmed = []
        for offset in (0, -4):
            check()
            if top+offset < 275 or bottom+offset > min(955, image.height):
                return None
            raw = image.crop((left, top+offset, right, bottom+offset))
            strips = [digit_strip(raw, threshold) for threshold in (160, 180)]
            if any(strip is None for strip in strips):
                return None
            first, second = strips
            if (first[1] != second[1]
                    or any(abs(a-b)>2 for a,b in zip(first[2],second[2]))
                    or (values and first[1] != max(len(str(n)) for n in values))):
                return None
            crops = []
            for strip, _, _ in strips:
                for label, scale in (('N',4), ('N',6), ('Qty',2), ('Qty',4)):
                    digits = strip.resize((strip.width*scale, strip.height*scale),
                                          Image.Resampling.NEAREST)
                    canvas = Image.new('RGB', (max(400,144+digits.width),
                                              max(200,32+digits.height)), 'white')
                    ImageDraw.Draw(canvas).text((20,16+4*scale), label,
                        font=ImageFont.load_default(size=14*scale), fill='black')
                    canvas.paste(digits, (120,16))
                    crops.append(canvas)
            results = self.vision.session.recognize_many(crops)
            check()
            readings = [parse_count([w for w in words if w['x'] >= 120
                                    and w['y'] >= 16]) for words in results]
            observed = [n for n in readings if n is not None]
            if (len(observed) < 3 or len(set(observed)) != 1
                    or not any(n is not None for n in readings[:4])
                    or not any(n is not None for n in readings[4:])
                    or len(str(observed[0])) != first[1]
                    or (values and observed[0] not in values)):
                return None
            confirmed.append(observed[0])
        return confirmed[0] if len(set(confirmed)) == 1 else None

    def retry_conflicting_count(self, image, box, check, votes):
        """Resolve suffix conflicts only with full digit-shape and OCR agreement."""
        from .stock_digits import digit_strip
        values = sorted(votes, key=lambda value: len(str(value)))
        if not 2 <= len(values) <= 4 or not any(
                a != b and str(a).endswith(str(b)) for a in values for b in values):
            return None
        check()
        raw = image.crop(box)
        strips = [digit_strip(raw, threshold) for threshold in (160, 180)]
        if any(strip is None for strip in strips):
            return None
        first, second = strips
        if (first[1] != second[1] or first[1] != len(str(values[-1]))
                or any(abs(a-b)>2 for a,b in zip(first[2],second[2]))):
            return None
        crops = [ImageOps.expand(strip.resize((strip.width*scale,strip.height*scale)),
                                 24, 'white')
                 for strip, _, _ in strips for scale in (4,6)]
        results = self.vision.session.recognize_many(crops)
        check()
        readings = [parse_count(words) for words in results]
        # Both masks must read, with at least three supporting reads and no
        # conflicting numeric read. They must corroborate an original candidate and the
        # number of complete connected glyphs; never simply choose the maximum.
        observed = [reading for reading in readings if reading is not None]
        value = observed[0] if observed else None
        if (value in votes and len(str(value)) == first[1]
                and len(observed) >= 3 and any(v is not None for v in readings[:2])
                and any(v is not None for v in readings[2:])
                and all(reading == value for reading in observed)):
            return value
        return None


    def retry_neutral_count(self, image, box, check, expected=None):
        """Remove colored icon pixels without trimming possible leading digits."""
        left, top, right, bottom = box
        candidates = []
        observations = []
        for offset in (-16, -12, -8, -4, 0, 4):
            check()
            if top+offset < 275 or bottom+offset > min(955, image.height):
                continue
            raw = image.crop((left, top+offset, right, bottom+offset)).convert('RGB')
            crops = []
            for spread in (20, 40):
                mask = Image.new('L', raw.size)
                mask.putdata([0 if min(pixel)>150 and max(pixel)-min(pixel)<spread else 255
                              for pixel in raw.get_flattened_data()])
                digits = mask.resize((raw.width*4, raw.height*4))
                canvas = Image.new('RGB', (420, 172), 'white')
                ImageDraw.Draw(canvas).text((8, 53), 'Qty', font=ImageFont.load_default(size=34), fill='black')
                canvas.paste(digits, (120, 16))
                crops.extend([ImageOps.expand(digits, 16, 'white'), canvas])
            results = self.vision.session.recognize_many(crops)
            check()
            votes = Counter()
            for method, words in enumerate(results):
                x = 120 if method % 2 else 16
                value = parse_count([w for w in words if w['x']>=x and w['y']>=16
                                    and w['h']>=12 and w['x']+w['w']<=x+raw.width*4
                                    and w['y']+w['h']<=16+raw.height*4])
                if value is not None:
                    votes[value] += 1
            # Every numeric reading must agree, including any original weak vote.
            observations.append(f'{offset:+d}px={dict(votes)}')
            if not votes:
                continue
            if len(votes)!=1 or (expected is not None and next(iter(votes))!=expected):
                self.log('數量去色補讀衝突：'+'；'.join(observations))
                return None
            if next(iter(votes.values()))>=2:
                candidates.append(next(iter(votes)))
            # Even a single conflicting numeric reading must not be discarded.
            expected = next(iter(votes))
        self.log('數量去色補讀：'+'；'.join(observations))
        return candidates[0] if len(candidates)>=2 else None

    def retry_missing_count(self, image, box, check):
        """Recover an empty count crop only when two nearby positions agree."""
        left, top, right, bottom = box
        candidates = []
        for offset in (-12, -24, 12):
            check()
            if top+offset < 275 or bottom+offset > min(955,image.height):
                continue
            raw = image.crop((left,top+offset,right,bottom+offset))
            gray = raw.convert('L')
            crops = []
            for threshold in (150,185,215):
                digit = ImageOps.invert(gray.point(lambda p:255 if p>threshold else 0))
                canvas = Image.new('RGB',(420,172),'white')
                ImageDraw.Draw(canvas).text((8,53),'Qty',font=ImageFont.load_default(size=34),fill='black')
                canvas.paste(digit.resize((digit.width*4,digit.height*4)),(120,16))
                crops.extend([ImageOps.expand(digit.resize((digit.width*4,digit.height*4)),16,'white'),canvas])
            crops.extend(ImageOps.expand(im.resize((im.width*3,im.height*3)),16,'white')
                         for im in (raw,ImageOps.autocontrast(gray)))
            results = self.vision.session.recognize_many(crops)
            check()
            votes = Counter()
            for method, words in enumerate(results):
                x = 120 if method < 6 and method % 2 else 16
                width,height = (207,105) if method>=6 else (276,140)
                value = parse_count([w for w in words if w['x']>=x and w['y']>=16
                                    and w['h']>=12 and w['x']+w['w']<=x+width
                                    and w['y']+w['h']<=16+height])
                if value is not None:votes[value]+=1
            ranked = votes.most_common()
            if any(a != b and str(a).endswith(str(b)) for a in votes for b in votes):
                value = self.retry_conflicting_count(
                    image, (left,top+offset,right,bottom+offset), check, votes)
                if value is None:
                    return None
                candidates.append(value)
            elif ranked and ranked[0][1]>=2 and (len(ranked)==1 or ranked[0][1]>ranked[1][1]):
                candidates.append(ranked[0][0])
            elif votes:
                return None  # A conflicting nearby crop is not evidence of recovery.
        return candidates[0] if len(candidates)>=2 and len(set(candidates))==1 else None


class StockScanner:
    """Separate from Runner and Journal; checked filter controls, never transfers."""
    def __init__(self, window, safety, session, entries, progress=lambda message: None,
                 publish=lambda result: None):
        self.window, self.safety = window, safety
        self.vision = Vision(session)
        self.reader = StockVision(self.vision, entries, log=progress)
        self.progress, self.publish = progress, publish
        self.result = StockResult()

    def check(self):
        self.safety.check(self.window)

    def rest(self, seconds):
        if self.safety.cancelled.wait(seconds):
            raise RuntimeError('盤點已暫停')
        self.check()

    def snapshot(self):
        self.check()
        image = capture.capture(self.window)
        self.check()
        return image

    def screen(self):
        from .stock_controls import storage_kind, all_category
        image = self.snapshot()
        if storage_kind(image) != 'shared':
            raise RuntimeError('請開啟公用保管箱，並關閉物品提示及數量視窗。')
        if not all_category(image):
            raise RuntimeError('盤點需要保管箱的「全部」分類。')
        return image

    def prepare(self):
        from .stock_controls import (storage_kind, all_category, filter_open,
                                     rarity_selected, only_general, search_empty, RARITIES)

        def click(x, y):
            self.safety.click(self.window, x, y)
            self.rest(.3)
            # Move the cursor off chips before examining their outlines.
            self.safety.scroll(self.window, 650, 65, 0)
            self.rest(.15)

        def wait_for(predicate, message):
            for _ in range(8):
                image = self.snapshot()
                if predicate(image):
                    return image
                self.rest(.2)
            raise RuntimeError(message)

        self.progress('盤點：確認公用保管箱，設定僅顯示一般稀有度')
        image = self.snapshot()
        kind = storage_kind(image)
        if kind is None:
            raise RuntimeError('無法確認保管箱畫面；請關閉其他視窗並開啟保管箱。')
        if kind == 'normal':
            click(198, 39)
            image = wait_for(lambda im: storage_kind(im) == 'shared', '切換公用保管箱未確認；已停止。')
        if not all_category(image):
            click(76, 96)
            image = wait_for(lambda im: storage_kind(im) == 'shared' and all_category(im),
                             '切換全部分類未確認；已停止。')
        click(55, 153)
        image = wait_for(filter_open, '搜尋篩選視窗未開啟；已停止。')
        click(960, 182)
        self.safety.key(self.window, 0x41, control=True)
        self.rest(.15)
        self.safety.key(self.window, 0x08)
        self.rest(.2)
        image = self.snapshot()
        for index, (x, y) in enumerate(RARITIES):
            wanted = index == 0
            if rarity_selected(image, index) != wanted:
                click(x, y)
                image = wait_for(lambda im: filter_open(im) and rarity_selected(im, index) == wanted,
                                 '稀有度切換結果未確認；已停止。')
        if not only_general(image):
            raise RuntimeError('無法確認僅選取一般稀有度；已停止。')
        # Blur the text field before Space so it activates Apply instead of typing.
        click(960, 560)
        image = self.snapshot()
        if not only_general(image):
            raise RuntimeError('套用前稀有度狀態變更；已停止。')
        if not search_empty(image):
            raise RuntimeError('無法確認搜尋文字已清空；已停止，請清除搜尋後重試。')
        self.safety.key(self.window, 0x20)
        self.rest(.35)
        wait_for(lambda im: storage_kind(im) == 'shared' and all_category(im),
                 '篩選套用後未回到公用保管箱；已停止。')
        return self.screen()

    def move(self, before, direction, notches=4, read_controls=True):
        for x, y in ((350, 550), (540, 660)):
            # The game may clamp one large wheel delta to one short movement.
            # Dispatch paced wheel events instead of multiplying a single delta.
            for _ in range(notches):
                self.safety.scroll(self.window, x, y, direction)
                self.rest(.08)
            self.rest(.35)
            self.safety.scroll(self.window, 80, 140, 0)
            self.rest(.15)
            if read_controls:
                after = self.screen()
            else:
                # Buffer pixels while scrolling; OCR waits for measured row movement.
                self.check()
                after = capture.capture(self.window)
                self.check()
                header_delta = ImageChops.difference(
                    before.crop((35,0,285,180)), after.crop((35,0,285,180)))
                if max(ImageStat.Stat(header_delta).mean)>3:
                    raise RuntimeError('盤點捲動期間保管箱控制區變更；已停止。')
            delta = displacement(before, after, direction)
            if delta: return after, delta
        return after, 0

    def boundary(self, image, direction):
        # A validated list that cannot move either way fits on one page.
        # Larger lists still verify movement away from the edge and back.
        away, delta = self.move(image, -direction, notches=1)
        if not delta:
            self.progress('盤點：清單上下皆無位移，按單頁清單完成盤點。')
            return self.screen()
        returned, reverse = self.move(away, direction, notches=1)
        if abs(reverse+delta) > 2 or displacement(image, returned, direction) != 0:
            raise RuntimeError('清單邊界返回核對失敗；盤點未完成。')
        final, delta = self.move(returned, direction, notches=1)
        if delta:
            raise RuntimeError('清單仍可捲動，尚未確認邊界；請重新盤點。')
        return final

    def scroll_batch(self, before, direction):
        """Reach the safe 540 px overlap limit before OCR; retain overlapping pixel frames."""
        frames=[];offset=0;image=before;at_end=False
        target_pixels=540;notches=4
        for _ in range(24):
            after,delta=self.move(image,direction,notches=notches,read_controls=False)
            if not delta:
                at_end=True
                break
            offset+=delta;frames.append((after,offset));image=after
            # Use observed wheel response to reduce stop/capture cycles. Limit each
            # burst to about 300 px, preserving alignment and emergency checks.
            pixels_per_notch=abs(delta)/notches
            remaining=max(1,target_pixels-abs(offset))
            notches=max(1,min(16,int(min(300,remaining)/pixels_per_notch)))
            self.progress(f"盤點捲動中：實測 {abs(offset)}/{target_pixels} px（尚未做物品 OCR）")
            if abs(offset)>=target_pixels or (abs(offset)>=492 and remaining<pixels_per_notch):
                break
        else:
            raise RuntimeError('盤點捲動多次仍未移動 540 px；已停止，保留已確認數量。')
        # Keep the furthest frame still overlapping the preceding retained page.
        # Pixel capture/alignment is cheap; discard redundant frames before OCR.
        kept=[];anchor=0;previous=None
        for frame in frames:
            if abs(frame[1]-anchor)>540:
                if previous is None or previous[1]==anchor:
                    raise RuntimeError('盤點捲動跨距過大；尚未確認中間物品。')
                kept.append(previous);anchor=previous[1]
            previous=frame
        if previous is not None and (not kept or kept[-1][1]!=previous[1]):
            kept.append(previous)
        self.progress(f'盤點捲動批次：位移 {abs(offset)} px；'
                      +('捲動暫無位移，待核對邊界，' if at_end else f'目標 {target_pixels} px（約 4.4 列），')
                      +f'接著辨識 {len(kept)} 張必要畫面。')
        return kept,at_end

    def scan_page(self,image,offset,page):
        self.check()
        self.progress(f'盤點：第 {page} 次掃描公用保管箱')
        locked = {(col,y-offset):cell for (col,y),cell in self.result.cells.items()
                  if cell.name is not None and cell.count is not None and not cell.uncertain}
        self.result.add(self.reader.cells(image, self.check, locked=locked), offset)
        self.progress('已保留堆疊：'+ '、'.join(
            f'{cell.name} × {cell.count}' for cell in self.result.cells.values()
            if cell.name is not None and cell.count is not None and not cell.uncertain))
        self.publish(self.result)

    def run(self):
        try:
            self.progress('盤點：檢查公用保管箱並回到清單頂端')
            image = self.prepare()
            for _ in range(300):
                frames,at_end=self.scroll_batch(image,1)
                if frames:image=frames[-1][0]
                if at_end:
                    image = self.boundary(image, 1)
                    break
            else:
                raise RuntimeError('回頂超過安全上限；尚未確認清單頂端。')
            offset=0;page=1
            self.scan_page(image,offset,page)
            for _ in range(500):
                frames,at_end=self.scroll_batch(image,-1)
                base=offset
                # 540 measured pixels (or the boundary) precede these OCR calls.
                for after,delta in frames:
                    page+=1;offset=base+delta
                    self.scan_page(after,offset,page)
                    image=after
                if at_end:
                    self.boundary(image, -1)
                    self.check()
                    self.result.complete = True
                    self.result.note = '已由頂端掃描到底；數量不明的素材仍須核對。'
                    break
            else:
                raise RuntimeError('掃描超過安全上限；尚未確認清單底端。')
        except Exception as error:
            self.result.note = '盤點未完成：' + str(error)
            raise
        finally:
            self.publish(self.result)
        return self.result
