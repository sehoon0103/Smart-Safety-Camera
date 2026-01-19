import os, cv2
from typing import List, Dict

def _hailo_available():
    try:
        import hailo_rt
        return True
    except Exception:
        return False


class BaseDetector:
    names = None
    def infer(self, frame_bgr) -> List[Dict]:
        raise NotImplementedError


class HailoDetector(BaseDetector):
    def __init__(self, hef_path, conf, iou):
        import hailo_rt  # 실제 환경에 맞게 수정 필요
        self.conf, self.iou = conf, iou
        self.rt = hailo_rt.HailoRT()
        self.net = self.rt.load_hef(hef_path)
        self.names = getattr(self.net, "get_labels", lambda: None)()

    def infer(self, frame_bgr):
        inp = cv2.resize(frame_bgr, (640, 640))
        outs = self.net.infer(inp)      # 실제 SDK에 맞게 파싱 필요
        dets = []
        for d in (outs or []):
            dets.append({
                "cls": int(d.get("cls", -1)),
                "conf": float(d.get("conf", 0.0)),
                "box":  d.get("bbox", [0, 0, 0, 0])
            })
        return dets


class CpuYOLODetector(BaseDetector):
    def __init__(self, weight, conf, iou):
        from ultralytics import YOLO
        self.model = YOLO(weight)
        self.conf, self.iou = conf, iou
        self.names = self.model.names

    def infer(self, frame_bgr):
        r = self.model.predict(
            source=frame_bgr,
            imgsz=768,
            conf=self.conf,
            iou=self.iou,
            verbose=False
        )[0]

        # 필요 없으면 아래 good_frame/bad_frame 저장 부분은 지워도 됨
        if r.boxes and len(r.boxes) > 0:
            cv2.imwrite("good_frame.jpg", frame_bgr)
        else:
            cv2.imwrite("bad_frame.jpg", frame_bgr)

        dets: List[Dict] = []

        if r.boxes:
            for b in r.boxes:
                x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
                dets.append({
                    "cls": int(b.cls[0].item()),
                    "conf": float(b.conf[0].item()),
                    "box": [x1, y1, x2, y2]
                })
        return dets


def build_detector(cfg):
    hef = cfg.get("hailo_hef_path", "")
    conf = cfg.get("conf_thres", 0.6)
    iou  = cfg.get("iou_thres", 0.5)

    if hef and os.path.isfile(hef) and _hailo_available():
        try:
            return HailoDetector(hef, conf, iou)
        except Exception as e:
            print(f"[WARN] Hailo 실패 → CPU 폴백: {e}")

    return CpuYOLODetector(cfg.get("cpu_model_weight", "yolov8n.pt"), conf, iou)
