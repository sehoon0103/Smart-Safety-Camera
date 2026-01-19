def iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2-x1)*max(0, y2-y1)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter + 1e-6
    return inter/ua

def clip_box(x1,y1,x2,y2,w,h):
    return [max(0,x1), max(0,y1), min(w-1,x2), min(h-1,y2)]

def head_region(person_box, ratio=0.28):
    x1,y1,x2,y2 = person_box; h = y2 - y1
    return [x1, y1, x2, y1 + int(h*ratio)]

def find_class_id(names, key):
    if names is None: return None
    if isinstance(names, dict): items = names.items()
    else: items = enumerate(names)
    k = key.lower()
    for i, n in items:
        if k in str(n).lower(): return int(i)
    return None