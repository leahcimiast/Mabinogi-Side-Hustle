"""Quest-list motion evidence excluding animated icons and stack counts."""
from PIL import Image,ImageChops,ImageFilter

def quest_list_moved(before,after):
    def sample(image):
        strips=Image.new('L',(500,200))
        for row in range(4):
            y=247+123*row
            strips.paste(image.crop((705,y,1205,y+50)).convert('L'),(0,row*50))
        return strips.resize((250,100)).filter(ImageFilter.GaussianBlur(.7))
    pixels=list(ImageChops.difference(sample(before),sample(after)).get_flattened_data())
    return sum(p>12 for p in pixels)/len(pixels)>.025 and sum(pixels)/len(pixels)>1.0
