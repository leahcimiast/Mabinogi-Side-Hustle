"""Read-only screen evidence for the supported 1280x960 layout.
No stock quantities or scroll stack counts are read or inferred.
"""
from dataclasses import dataclass
import re
from PIL import Image,ImageOps
from .inventory_recognition import line_text

def compact(text):return "".join(text.split()).replace("：",":")

def tracker_identity(text):
    text=compact(text).lstrip('·•◆◇').rstrip('~～↗→,，')
    for prefix in ('取得','製作','尋找','得','取','製','作'):
        if text.startswith(prefix):return text[len(prefix):]
    return text

def is_report_text(text):
    text=compact(text)
    return '回報任務' in text or ('佈告欄' in text and '回報' in text)

@dataclass
class Label:
    text:str
    box:tuple
    @property
    def point(self):return ((self.box[0]+self.box[2])/2,(self.box[1]+self.box[3])/2)

def labels(words,region=(0,0,1280,960)):
    x1,y1,x2,y2=region
    words=[w for w in words if x1<=w['x'] and y1<=w['y'] and w['x']+w['w']<=x2 and w['y']+w['h']<=y2]
    rows=[]
    for w in sorted(words,key=lambda w:(w['y']+w['h']/2,w['x'])):
        cy=w['y']+w['h']/2
        row=next((r for r in rows if abs(r[0]['y']+r[0]['h']/2-cy)<max(6,w['h']*.5)),None)
        if row is None:rows.append([w])
        else:row.append(w)
    result=[]
    for row in rows:
        groups=[]
        for w in sorted(row,key=lambda w:w['x']):
            if not groups or w['x']-(groups[-1][-1]['x']+groups[-1][-1]['w'])>22:groups.append([w])
            else:groups[-1].append(w)
        for g in groups:
            result.append(Label(compact(''.join(w['text'] for w in g)),(min(w['x'] for w in g),min(w['y'] for w in g),max(w['x']+w['w'] for w in g),max(w['y']+w['h'] for w in g))))
    return result

class Screen:
    def __init__(self,image,words):self.image=image;self.words=words
    def find(self,text,region=(0,0,1280,960),exact=False):
        key=compact(text)
        found=[x for x in labels(self.words,region) if (x.text==key if exact else key in x.text)]
        return found[0] if len(found)==1 else None
    def has(self,text,region=(0,0,1280,960)):return any(compact(text) in x.text for x in labels(self.words,region))
    def green(self,box):
        pixels=list(self.image.crop(box).convert('RGB').get_flattened_data())
        return sum(g>135 and g>r*1.25 and g>b*.95 for r,g,b in pixels)/len(pixels)>.45
    def shared(self):
        r,g,b=self.image.getpixel((200,45))[:3]
        return self.has('公用保管箱',(130,0,280,85)) and r>140 and 45<g<190 and b<100
    def quantity_dialog(self):return self.has('移至背包',(660,620,1260,955)) and self.has('最大',(1000,740,1250,840))
    def storage(self):return self.shared() and self.has('背包',(670,80,820,180)) and not self.quantity_dialog() and not self.has('獲得方法')
    def tooltip_titles(self):
        # An acquisition footer anchors an open tooltip, including food.
        footer=self.find('獲得方法',(80,120,660,950))
        if footer:
            headings=[title for title in labels(self.words,(80,120,660,780))
                      if abs(title.box[0]-footer.box[0])<=18
                      and title.box[3]<footer.box[1] and title.box[3]-title.box[1]>=18
                      and re.search(r'[A-Za-z\u3400-\u9fff]',title.text)]
            if headings:return [min(headings,key=lambda title:title.box[1])]
        # Retain category fallback when footer OCR is absent.
        return [title for title in labels(self.words,(80,120,660,780))
                if self.has('材料',(max(0,title.box[0]-10),title.box[3],min(1280,title.box[0]+200),min(960,title.box[3]+50)))]
    def item_title(self,name):
        found=[title for title in self.tooltip_titles() if title.text==compact(name)]
        return found[0] if len(found)==1 else None
    def submission(self):return self.has('傳達',(0,0,200,90)) and self.has('自動放入',(30,585,250,660))
    def autofill_enabled(self):
        return self.green((84,620,94,632))
    def submitted_ready(self):
        return self.submission() and self.green((160,545,500,570))
    def quest_identity_present(self,identity,region):
        # Exact item identity also applies to completion when the tracker lost its verb.
        return any(tracker_identity(title.text)==tracker_identity(identity)
                   for screen in getattr(self,'variants',[self]) for title in labels(screen.words,region))

    def completion(self,identity=None):
        # Only the post-submit runner uses this: a wide bottom confirmation button.
        image=self.image.convert('RGB');points=[]
        for y in range(840,950):
            for x in range(300,980):
                r,g,b=image.getpixel((x,y))
                if g>135 and g>r*1.25 and g>b*.95:points.append((x,y))
        if not points:return False
        left=min(x for x,y in points);right=max(x for x,y in points)
        top=min(y for x,y in points);bottom=max(y for x,y in points)
        width=right-left+1;height=bottom-top+1
        return (450<=width<=550 and 45<=height<=85
                and abs((left+right)/2-640)<=25 and 885<=(top+bottom)/2<=925
                and len(points)/(width*height)>.8)
    def tracker(self,material_or_tail):
        target=compact(material_or_tail);names=[]
        rows=labels(self.words,(900,180,1275,520))
        for title in rows:
            if tracker_identity(title.text)!=target:continue
            full=compact(title.text).lstrip('·•◆◇').startswith(('取得','製作','尋找'))
            # A missing action prefix is accepted only on a large title immediately
            # above its own report row, never on the smaller inventory-count line.
            anchored=title.box[3]-title.box[1]>=17 and any(
                is_report_text(row.text) and 8<=row.box[1]-title.box[3]<=55
                and abs(row.box[2]-title.box[2])<=80 for row in rows)
            if full or anchored:names.append(title)
        return names[0] if len(names)==1 else None
    def report(self):
        found=[row for row in labels(self.words,(900,180,1275,520)) if is_report_text(row.text)]
        return found[0] if len(found)==1 else None
    def world(self):return self.has('對周圍說話',(0,820,500,960))
    def dialogue(self):
        # Only a visible speech bubble with readable text permits a dialogue advance.
        pix=list(self.image.crop((350,20,850,175)).get_flattened_data())
        return sum(min(p[:3])>220 for p in pix)/len(pix)>.12 and bool(labels(self.words,(350,20,850,175)))

class MultiScreen(Screen):
    """Keep OCR variants separate so overlapping tokens never form invented text."""
    def __init__(self,image,word_sets):
        super().__init__(image,word_sets[0])
        self.variants=[Screen(image,words) for words in word_sets]
    def has(self,text,region=(0,0,1280,960)):
        return any(screen.has(text,region) for screen in self.variants)
    def find(self,text,region=(0,0,1280,960),exact=False):
        found=[]
        for screen in self.variants:
            for label in labels(screen.words,region):
                if not (label.text==compact(text) if exact else compact(text) in label.text):continue
                if not any(x.text==label.text and abs(x.point[0]-label.point[0])<20 and abs(x.point[1]-label.point[1])<15 for x in found):found.append(label)
        return found[0] if len(found)==1 else None
    def tracker(self,material_or_tail):
        found=[screen.tracker(material_or_tail) for screen in self.variants]
        found=[item for item in found if item is not None]
        if found:
            for screen in self.variants:
                for title in labels(screen.words,(900,180,1275,520)):
                    text=compact(title.text).lstrip('·•◆◇')
                    identity=tracker_identity(text)
                    # An isolated action is a split OCR fragment, not another item.
                    if identity and text.startswith(('取得','製作','尋找','得','取','製','作')) and any(abs(title.point[1]-item.point[1])<=18 and abs(title.box[2]-item.box[2])<=100 for item in found):
                        target=compact(material_or_tail)
                        # A visibly shorter prefix fragment cannot veto a complete
                        # exact reading on the same title. Never drop a literal +.
                        fragment=('+' not in target and len(identity)<len(target)
                                  and target.startswith(identity) and any(
                                      text[:2]==compact(item.text).lstrip('·•◆◇')[:2]
                                      and abs(title.box[0]-item.box[0])<=30
                                      and title.box[2]<=item.box[2]-8 for item in found))
                        if identity!=target and not fragment:
                            raise RuntimeError(f'多方法 OCR 的任務身份不一致：{title.text} / {material_or_tail}；停止交付。')
            actions={item.text[:2] for item in found if item.text.startswith(('取得','製作','尋找'))}
            if len(actions)>1:raise RuntimeError('多方法 OCR 的任務動作不一致；停止交付。')
        if len({tracker_identity(item.text) for item in found})>1 or any(abs(item.point[1]-found[0].point[1])>18 for item in found):raise RuntimeError('多方法 OCR 的任務身份或位置不一致；停止交付。')
        return found[0] if found else None
    def report(self):
        found=[item for screen in self.variants for item in labels(screen.words,(900,180,1275,520)) if is_report_text(item.text)]
        if any(abs(item.point[1]-found[0].point[1])>20 for item in found):
            raise RuntimeError('同時辨識到多個佈告欄回報位置；請只保留目前任務追蹤。')
        return found[0] if found else None
    def selected_tab(self,label):
        from .inventory_recognition import selected_tab
        return any(selected_tab(self.image,screen.words,label) for screen in self.variants)

class Vision:
    def __init__(self,session):self.session=session
    def observe(self,image):
        if image.size!=(1280,960):raise RuntimeError('Unsupported game area')
        gray=ImageOps.autocontrast(image.convert('L'))
        variants=[(image,1),(image,2),(gray,2),(ImageOps.invert(gray),2),(ImageOps.invert(gray.point(lambda p:255 if p>120 else 0)),2)]
        results=self.session.recognize_many([im.resize((1280*scale,960*scale)) for im,scale in variants])
        mapped=[[dict(text=w['text'],x=w['x']/scale,y=w['y']/scale,w=w['w']/scale,h=w['h']/scale) for w in words] for (_,scale),words in zip(variants,results)]
        return MultiScreen(image,mapped)
    def observe_tracker(self,image,include_world=False):
        regions=[(640,0,1280,480)]
        if include_world:regions.append((0,880,310,950))
        result=self._observe_regions(image,regions,variant_count=2)
        # Retry only unread small controls, never the entire game screen.
        retry=[]
        if result.report() is None:retry.append((1000,220,1275,380))
        if include_world and not result.world():retry.append((0,820,500,960))
        if retry:
            recovered=self._observe_regions(image,retry)
            result=MultiScreen(image,[s.words for s in result.variants+recovered.variants])
        return result

    def observe_dialogue(self,image):
        return self._observe_regions(image,[(350,20,850,175)],variant_count=2)

    def observe_submission_controls(self,image):
        return self._observe_regions(image,[(0,0,320,140),(30,585,250,660),(350,20,850,175)])

    def _observe_regions(self,image,regions,variant_count=5):
        if image.size!=(1280,960):raise RuntimeError('Unsupported game area')
        inputs=[];spec=[]
        for box in regions:
            raw=image.crop(box);gray=ImageOps.autocontrast(raw.convert('L'))
            variants=[(raw,1),(raw,2),(gray,2),(ImageOps.invert(gray),2),
                      (ImageOps.invert(gray.point(lambda p:255 if p>120 else 0)),2)]
            for index,(variant,scale) in enumerate(variants[:variant_count]):
                inputs.append(ImageOps.expand(variant.resize((raw.width*scale,raw.height*scale)),20,'white'))
                spec.append((box,index,scale))
        sets=[[] for _ in range(variant_count)];results=[]
        for start in range(0,len(inputs),12):
            results.extend(self.session.recognize_many(inputs[start:start+12],timeout=5))
        for words,(box,index,scale) in zip(results,spec):
            sets[index].extend(dict(text=w['text'],x=box[0]+(w['x']-20)/scale,y=box[1]+(w['y']-20)/scale,w=w['w']/scale,h=w['h']/scale)
                for w in words if w['x']>=20 and w['y']>=20
                and w['x']+w['w']<=20+(box[2]-box[0])*scale
                and w['y']+w['h']<=20+(box[3]-box[1])*scale)
        return MultiScreen(image,sets)

    def observe_inventory_controls(self,image,category_only=False):
        """Read small controls only; native scale recovers white selected tabs."""
        if image.size!=(1280,960):raise RuntimeError('Unsupported game area')
        regions=[(910,900,1000,945)] if category_only else [(700,95,1260,175),(910,900,1000,945)]
        inputs=[];spec=[]
        for box in regions:
            raw=image.crop(box);gray=ImageOps.autocontrast(raw.convert('L'))
            variants=[(raw,1),(raw,2),(gray,2),(ImageOps.invert(gray),2),
                      (ImageOps.invert(gray.point(lambda p:255 if p>120 else 0)),2)]
            for variant,scale in variants:
                inputs.append(ImageOps.expand(variant.resize((variant.width*scale,variant.height*scale)),20,'white'))
                spec.append((box,scale))
        sets=[]
        for words,(box,scale) in zip(self.session.recognize_many(inputs,timeout=5),spec):
            sets.append([dict(text=w['text'],x=box[0]+(w['x']-20)/scale,y=box[1]+(w['y']-20)/scale,w=w['w']/scale,h=w['h']/scale)
                         for w in words if w['x']>=20 and w['y']>=20
                         and w['x']+w['w']<=20+(box[2]-box[0])*scale
                         and w['y']+w['h']<=20+(box[3]-box[1])*scale])
        return MultiScreen(image,sets)

    def quest_use_button(self,image):
        """Fixed-position enabled control after selecting a known scroll; no OCR."""
        if image.size!=(1280,960):raise RuntimeError('Unsupported game area')
        screen=Screen(image,[]);button=(695,875,790,920)
        if (screen.green(button) and not screen.green((660,885,675,910))
                and not screen.green((810,885,825,910))):return Label('使用',button)
        return None

    def transfer_confirmation_ready(self,image):
        """Enabled fixed-position button in an already verified quantity dialog."""
        if image.size!=(1280,960):raise RuntimeError('Unsupported game area')
        return Screen(image,[]).green((900,885,1020,920))

    def transfer_prompt_ready(self,image):
        # This central button opens the quantity dialog; it is not the right-side
        # confirmation button. OCR only this small region while animation settles.
        box=(540,835,730,940)
        if not Screen(image,[]).green((565,875,700,915)):return False
        raw=image.crop(box);gray=ImageOps.autocontrast(raw.convert('L'))
        variants=[(raw,1),(raw,2),(gray,2),(ImageOps.invert(gray),2),
                  (ImageOps.invert(gray.point(lambda p:255 if p>120 else 0)),2)]
        results=self.session.recognize_many([im.resize((im.width*scale,im.height*scale)) for im,scale in variants])
        for (_,scale),words in zip(variants,results):
            mapped=[dict(text=w['text'],x=box[0]+w['x']/scale,y=box[1]+w['y']/scale,w=w['w']/scale,h=w['h']/scale) for w in words]
            if Screen(image,mapped).has('移至背包',box):return True
        return False

    def observe_storage(self,image):
        # OCR only storage controls and the selected-item tooltip. Keep all five
        # methods and original pixels for colour evidence; ignore icon counts.
        if image.size!=(1280,960):raise RuntimeError('Unsupported game area')
        regions=[(130,0,280,85),(670,80,820,180),(80,120,660,950),(660,620,1260,955)]
        atlas=Image.new('RGB',(620,1400));slots=[];top=10
        for box in regions:
            crop=image.crop(box);atlas.paste(crop,(10,top));slots.append((box,10,top));top+=crop.height+10
        gray=ImageOps.autocontrast(atlas.convert('L'))
        variants=[(atlas,1),(atlas,2),(gray,2),(ImageOps.invert(gray),2),(ImageOps.invert(gray.point(lambda p:255 if p>120 else 0)),2)]
        results=self.session.recognize_many([im.resize((im.width*scale,im.height*scale)) for im,scale in variants]);sets=[]
        for (_,scale),words in zip(variants,results):
            mapped=[]
            for box,x,y in slots:
                for w in words:
                    wx,wy,ww,wh=(w[k]/scale for k in ('x','y','w','h'))
                    if x<=wx and y<=wy and wx+ww<=x+box[2]-box[0] and wy+wh<=y+box[3]-box[1]:
                        mapped.append(dict(text=w['text'],x=box[0]+wx-x,y=box[1]+wy-y,w=ww,h=wh))
            sets.append(mapped)
        return MultiScreen(image,sets)

    def storage_names(self,image,mode="inverted"):
        # Locate the repeating gray name rows after scrolling, rather than assuming
        # the original top-of-list row offset. White icon counts are excluded.
        if getattr(self,'_geometry_image',None) is image:
            tops=self._geometry_tops
        else:
            pixels=image.convert('RGB').load()
            rows=[sum(1 for x in range(57,626) if 90<min(pixels[x,y])<210 and max(pixels[x,y])-min(pixels[x,y])<22) for y in range(280,955)]
            scores=[sum(sum(rows[y:y+18]) for y in range(phase,len(rows)-18,123)) for phase in range(123)]
            phase=max(range(123),key=lambda i:scores[i])
            if scores[phase]<100:
                self._storage_boxes=[]
                return []
            tops=[y for y in range(280+phase-5,955,123) if y>=330 and y+30<=955]
            self._geometry_image=image;self._geometry_tops=tops
        atlas=Image.new('RGB',(2400,max(180,len(tops)*180)),'white');boxes=[]
        for row,y in enumerate(tops):
            for col in range(6):
                x=57+95*col;box=(x,y,x+94,y+30)
                raw=image.crop(box)
                if mode=='color':crop=raw
                elif mode=='gray':crop=ImageOps.autocontrast(raw.convert('L'))
                elif mode=='threshold':crop=ImageOps.invert(raw.convert('L').point(lambda p:255 if p>110 else 0))
                elif mode=='wide':crop=ImageOps.autocontrast(ImageOps.invert(image.crop((x,y-7,x+94,y+37)).convert('L')))
                else:crop=ImageOps.autocontrast(ImageOps.invert(raw.convert('L')))
                crop=crop.resize((376,120))
                atlas.paste(crop,(col*400+10,row*180+10));boxes.append(box)
        scale=.5 if mode in ('color','wide') else 1
        source=atlas.resize((int(atlas.width*scale),int(atlas.height*scale))) if scale!=1 else atlas
        self._storage_boxes=boxes
        words=self.session.recognize_many([source])[0]
        if scale!=1:words=[dict(text=w['text'],x=w['x']/scale,y=w['y']/scale,w=w['w']/scale,h=w['h']/scale) for w in words]
        found=[]
        for i,box in enumerate(boxes):
            row,col=divmod(i,6);x=col*400+10;y=row*180+10
            local=[w for w in words if x<=w['x'] and y<=w['y'] and w['x']+w['w']<=x+376 and w['y']+w['h']<=y+120]
            text=compact(line_text(local))
            if re.fullmatch(r'[\u3400-\u9fff+]+',text):
                found.append(Label(text,(box[0],box[1]-65,box[2],box[3]-35)))
        return found
    def storage_names_retry(self,image):
        found=[]
        for mode in ('color','gray','threshold','wide'):
            for label in self.storage_names(image,mode):
                if not any(x.text==label.text and abs(x.point[0]-label.point[0])<30 and abs(x.point[1]-label.point[1])<30 for x in found):found.append(label)
        # Short labels can be completely omitted inside a large atlas even at
        # another scale. Retry only unread cells as isolated 2x crops.
        missing=[box for box in getattr(self,'_storage_boxes',[])
                 if not any(abs(x.box[0]-box[0])<5 and abs(x.box[1]-(box[1]-65))<5 for x in found)]
        for start in range(0,len(missing),12):
            boxes=missing[start:start+12]
            images=[ImageOps.expand(ImageOps.autocontrast(ImageOps.invert(image.crop(box).convert('L'))).resize((188,60)),20,'white') for box in boxes]
            for box,words in zip(boxes,self.session.recognize_many(images)):
                text=compact(line_text([w for w in words if w['x']>=20 and w['y']>=20 and w['x']+w['w']<=208 and w['y']+w['h']<=80]))
                if re.fullmatch(r'[\u3400-\u9fff+]+',text):found.append(Label(text,(box[0],box[1]-65,box[2],box[3]-35)))
        return found

    def tooltip_retry(self,image):
        box=(80,120,660,950);raw=image.crop(box);gray=ImageOps.autocontrast(raw.convert('L'))
        variants=[(raw,3),(gray,2),(ImageOps.invert(gray),3),
                  (ImageOps.invert(gray.point(lambda p:255 if p>120 else 0)),3)]
        images=[im.resize((im.width*scale,im.height*scale)) for im,scale in variants]
        results=self.session.recognize_many(images);found=[]
        for (_,scale),words in zip(variants,results):
            mapped=[dict(text=w['text'],x=box[0]+w['x']/scale,y=box[1]+w['y']/scale,w=w['w']/scale,h=w['h']/scale) for w in words]
            for title in Screen(image,mapped).tooltip_titles():
                if not any(x.text==title.text and abs(x.point[1]-title.point[1])<30 for x in found):found.append(title)
        return found

    def entered_quantity(self,image):
        value=self._quantity_at_threshold(image,170)
        if value is not None:return value
        values=[self._quantity_at_threshold(image,threshold) for threshold in (140,200)]
        known={value for value in values if value is not None}
        return known.pop() if len(known)==1 else None

    def _quantity_at_threshold(self,image,threshold):
        # Read back only the number typed by this app, never the available stock.
        box=(925,765,998,810)
        crop=image.crop(box).convert('RGB')
        mask=Image.new('L',crop.size)
        mask.putdata([255 if min(p)>threshold else 0 for p in crop.get_flattened_data()])
        bounds=mask.getbbox()
        if bounds is None:return None
        digit=ImageOps.invert(mask.crop(bounds))
        digit=digit.resize((round(digit.width*48/digit.height),48))
        canvas=Image.new('RGB',(300,110),'white');canvas.paste(digit,(120,30))
        from PIL import ImageDraw,ImageFont
        import os
        font=ImageFont.truetype(os.path.join(os.environ.get('WINDIR','C:/Windows'),'Fonts/arial.ttf'),48)
        ImageDraw.Draw(canvas).text((10,20),'Qty',font=font,fill='black')
        words=self.session.recognize_many([canvas])[0]
        values=[w['text'] for w in words if w['x']>=110 and re.fullmatch('[0-9]+',w['text'])]
        return int(values[0]) if len(values)==1 else None
