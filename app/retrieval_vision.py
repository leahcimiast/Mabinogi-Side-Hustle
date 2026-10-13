"""First-tab pixel readiness and verified list movement; no game input."""
from PIL import ImageChops,ImageStat
from .stock_controls import storage_kind,all_category


def ready(image):
    return storage_kind(image)=='shared' and all_category(image)


def stable(before,after):
    if not ready(before) or not ready(after):return False
    # Median columns tolerate local icon glow, but a whole-panel fade must settle.
    delta=ImageChops.difference(before.crop((57,275,626,950)).convert('RGB'),
                                after.crop((57,275,626,950)).convert('RGB'))
    scores=sorted(max(ImageStat.Stat(delta.crop((95*i,0,min(95*i+94,569),675))).mean)
                  for i in range(6))
    return scores[3]<=.8


def moved(before,after,direction):
    if not ready(before) or not ready(after):
        raise RuntimeError('保管箱仍在轉場或畫面不明；未確認捲動。')
    # Broad pixel changes alone are not evidence of vertical row movement.
    # Existing alignment rejects ambiguous motion rather than declaring an edge.
    from .stock_check import displacement
    return displacement(before,after,direction)!=0
