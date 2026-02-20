import time
import yaml
import cv2
import requests
import csv
from datetime import datetime

from sensors import Camera, GPIOBoard
from infer_yolo import build_detector
from temporal_lstm import TemporalSmoother
from rules import HelmetJudge
from alerts import Notifier
from admit_bt import AdminNotifier


# ---------------------------------------
#   Flask 서버 주소
# ---------------------------------------
SERVER_IP = "localhost"
ALERT_URL = f"http://{SERVER_IP}:5000/alert"


def send_alert(alert_type):
    """Flask 서버로 상태 전송"""
    try:
        r = requests.post(ALERT_URL, json={"type": alert_type}, timeout=1)
        print("[ALERT] Sent:", alert_type, "Status:", r.status_code)
    except Exception as e:
        print("[ALERT] Failed:", e)


def get_class_name(names, cls_id):
    """YOLO 클래스 이름 얻기"""
    if isinstance(names, dict):
        return names.get(cls_id, "")
    return names[cls_id]


# ---------------------------------------
#   YOLO 기반 안전 판단
# ---------------------------------------
def analyze_safety(dets, names):

    helmet_on = False
    helmet_off = False
    vest_on = False

    for d in dets:
        name = get_class_name(names, d["cls"])

        if name == "head_helmet":
            helmet_on = True

        if name == "head_nohelmet":
            helmet_off = True

        if name == "vest":
            vest_on = True

    vest_off = not vest_on
    return helmet_on, helmet_off, vest_on, vest_off


# ---------------------------------------
#   CSV 파일 초기 생성
# ---------------------------------------
def init_csv():
    filename = "safety_log.csv"
    try:
        with open(filename, "x", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "helmet", "vest", "final"])
    except FileExistsError:
        pass  # 이미 있으면 생성 안 함


# ---------------------------------------
#   CSV에 로그 기록
# ---------------------------------------
def write_csv(helmet_on, vest_on, alert_type):
    filename = "safety_log.csv"

    helmet_text = "ON" if helmet_on else "OFF"
    vest_text = "ON" if vest_on else "OFF"

    # alert 타입을 웹 대시보드용으로 재정의
    if alert_type == "ok":
        final_text = "SAFE"
    elif alert_type in ["no_helmet", "no_vest"]:
        final_text = "WARNING"
    else:
        final_text = "DANGER"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([now, helmet_text, vest_text, final_text])

    print(f"[CSV] Saved: {now} | Helmet={helmet_text} | Vest={vest_text} | Final={final_text}")


# ---------------------------------------
#   메인 실행
# ---------------------------------------
def main():
    # 설정 파일 불러오기
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cam = Camera(cfg["camera"])
    gpio = GPIOBoard(cfg["gpio"])
    det = build_detector(cfg["inference"])
    names = det.names

    smooth = TemporalSmoother(window=cfg["logic"]["temporal_window"])
    judge = HelmetJudge(cfg["logic"])
    judge._ensure_ids(names)

    notifier = Notifier(gpio, cfg["gpio"])
    admin_notifier = AdminNotifier()

    draw = cfg["logic"]["draw_visual"]
    show = cfg["logic"]["show_window"]

    # CSV 초기화
    init_csv()

    last_alert = None
    last_time = 0
    SEND_INTERVAL = 2

    try:
        prev = time.time()

        while True:
            frame = cam.read()

            # FPS 계산
            now = time.time()
            fps = 1 / (now - prev)
            prev = now
            print("FPS=", fps)

            dets = det.infer(frame)

            unsafe_prob, overlay = judge.evaluate(frame, dets, draw=draw)
            smooth.push(unsafe_prob)
            smooth_val = smooth.decision()

            # YOLO 분석
            helmet_on, helmet_off, vest_on, vest_off = analyze_safety(dets, names)

            print(f"[STATE] helmet_on={helmet_on}, helmet_off={helmet_off}, vest_on={vest_on}, vest_off={vest_off}")

            # ---------------------------------------
            #   App Inventor와 동일 alert 규칙
            # ---------------------------------------
            if helmet_on and vest_on:
                alert = "ok"
            elif helmet_off and vest_off:
                alert = "no_both"
            elif helmet_off:
                alert = "no_helmet"
            else:
                alert = "no_vest"

            # Flask에 전송
            if alert != last_alert or now - last_time > SEND_INTERVAL:
                send_alert(alert)
                last_alert = alert
                last_time = now

            # GPIO & 블루투스 알림
            notifier.alert(alert != "ok")
            admin_notifier.send_state(alert != "ok")

            # CSV 저장
            write_csv(helmet_on, vest_on, alert)

            # 디버그 HUD 표시
            if draw:
                hud = overlay if overlay is not None else frame
                cv2.putText(hud, f"Alert:{alert} Helmet:{helmet_on} Vest:{vest_on}",
                            (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 0) if alert == "ok" else (0, 165, 255), 2)

            # 카메라 출력
            if show:
                cv2.imshow("smart_safety", overlay if overlay is not None else frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

    finally:
        notifier.alert(False)
        cam.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()