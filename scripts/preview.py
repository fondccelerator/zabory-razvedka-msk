# Уменьшенное превью полностраничного скрина частями для просмотра: preview.py <file> <y0> <y1> [width]
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
im = Image.open(sys.argv[1]); y0, y1 = int(sys.argv[2]), int(sys.argv[3]); w = int(sys.argv[4]) if len(sys.argv) > 4 else 480
crop = im.crop((0, y0, min(1440, im.width), min(y1, im.height)))
r = w / crop.width
crop = crop.resize((w, int(crop.height * r)))
out = '/tmp/claude-0/-home-claude/97f9dc36-7fb1-518c-96b3-65ea34b0a075/scratchpad/prev.jpg'
crop.convert('RGB').save(out, quality=70); print(out, crop.size)
