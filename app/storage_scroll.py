"""Paced storage scrolling with image-motion checks, independent of OCR text."""
from PIL import ImageChops,ImageFilter

REGION=(55,275,625,935)

def panel_moved(before,after):
    def sample(image):return image.crop(REGION).convert('L').resize((114,132)).filter(ImageFilter.GaussianBlur(.7))
    delta=ImageChops.difference(sample(before),sample(after))
    pixels=list(delta.get_flattened_data())
    # Ignore isolated cursor/highlight/noise pixels; compare the actual content area.
    return sum(p>15 for p in pixels)/len(pixels)>.025 and sum(pixels)/len(pixels)>1.8

def scroll_page(before,wheel,pause,read,direction=-1,log=lambda message:None):
    if direction not in (-1,1):raise ValueError('Invalid scroll direction')
    for attempt,point in enumerate(((350,550),(540,660)),1):
        wheel(*point,0);pause(.25)
        for _ in range(15):
            wheel(*point,direction);pause(.08)
        wheel(80,140,0);pause(.65)
        after=read()
        if panel_moved(before,after):
            log(f'捲動生效：第 {attempt} 次嘗試，素材區有位移。')
            return after,True
        log(f'捲動未見位移：第 {attempt}/2 次；'+('更換游標位置重試。' if attempt==1 else '停止捲動檢查。'))
    return after,False
