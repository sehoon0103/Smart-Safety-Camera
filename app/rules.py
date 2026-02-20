# rules.py  (Helmet + No-Helmet + Vest 지원, 단순화 버전)

import cv2
from utils import find_class_id, head_region, iou


class HelmetJudge:
    """
    dets 리스트와 frame을 받아서
    - helmet / no-helmet / vest 박스를 그려주고
    - unsafe 확률(0.0 ~ 1.0)을 리턴하는 규칙 엔진.
    """

    def __init__(self, logic_cfg):
        # config.yaml에서 가져오는 값들
        self.min_px = logic_cfg.get("min_person_size_px", 0)
        self.head_ratio = logic_cfg.get("head_ratio", 0.28)
        self.helmet_head_iou = logic_cfg.get("helmet_head_iou", 0.10)
        self.helmet_min_conf = logic_cfg.get("helmet_min_conf", 0.35)

        # Vest 판정용 파라미터
        self.vest_torso_top = logic_cfg.get("vest_torso_top_ratio", 0.18)
        self.vest_torso_bottom = logic_cfg.get("vest_torso_bottom_ratio", 0.98)
        self.vest_torso_iou = logic_cfg.get("vest_torso_iou", 0.02)

        # NO-VEST 표시용 영역(상체 구간만)
        self.vest_draw_top = logic_cfg.get("vest_draw_top_ratio", 0.25)
        self.vest_draw_bottom = logic_cfg.get("vest_draw_bottom_ratio", 0.75)

        # 프레임 단위 vest 상태 히스토리
        self.vest_min_frames = logic_cfg.get("vest_min_frames", 2)
        self.vest_state = None          # True: vest 있음, False: no-vest
        self.vest_state_frames = 0

        # PPE confidence 하한
        self.min_ppe_conf = logic_cfg.get("min_ppe_conf", 0.05)

        # class id들 (초기에는 None, main에서 _ensure_ids 한 번 호출)
        self.person_id = None
        self.helmet_id = None
        self.no_helmet_id = None
        self.vest_id = None

    # ------------------------------------------------------------------
    #  내부 유틸
    # ------------------------------------------------------------------
    def _ensure_ids(self, names):
        """
        모델 class 이름 배열(names)을 보고
        person / helmet / no-helmet / vest 의 id를 한 번만 찾아둔다.
        main()에서 judge._ensure_ids(det.names) 로 한 번 호출해주는 구조.
        """
        if names is None:
            print("[HJ] WARNING: detector.names is None")
            return

        # person
        if self.person_id is None:
            self.person_id = find_class_id(names, "person")

        # helmet
        if self.helmet_id is None:
            for key in ["head_helmet", "helmet", "hardhat"]:
                cid = find_class_id(names, key)
                if cid is not None:
                    self.helmet_id = cid
                    break

        # no-helmet
        if self.no_helmet_id is None:
            for key in ["head_nohelmet", "head_nohelm", "no-helmet", "nohelmet", "NO-Hardhat"]:
                cid = find_class_id(names, key)
                if cid is not None:
                    self.no_helmet_id = cid
                    break

        # vest
        if self.vest_id is None:
            for key in ["vest", "safety_vest", "Safety Vest"]:
                cid = find_class_id(names, key)
                if cid is not None:
                    self.vest_id = cid
                    break

        print(
            f"[HJ] class ids -> person={self.person_id}, "
            f"helmet={self.helmet_id}, no_helmet={self.no_helmet_id}, vest={self.vest_id}"
        )

    # ------------------------------------------------------------------
    #  메인 평가 함수
    # ------------------------------------------------------------------
    def evaluate(self, frame, dets, draw=False):
        H, W, _ = frame.shape
        overlay = frame.copy() if draw else None

        helmet_cnt = 0
        no_helmet_cnt = 0
        vest_cnt = 0
        no_vest_cnt = 0

        persons = []
        helmet_boxes = []
        no_helmet_boxes = []

        if self.person_id is not None:
            for d in dets:
                if d.get("cls") != self.person_id:
                    continue
                box = d.get("box")
                if not box or len(box) != 4:
                    continue
                px1, py1, px2, py2 = map(int, box)
                if px2 <= px1 or py2 <= py1:
                    continue

                area = (px2 - px1) * (py2 - py1)
                if self.min_px > 0 and area < self.min_px:
                    continue  # 너무 작은 사람 박스는 무시

                ph = py2 - py1
                if ph <= 0:
                    continue

                # 다리 쪽(하단) 너무 많이 포함되면 아래 15% 잘라냄
                crop_bottom = int(ph * 0.15)
                py2_adj = py2 - crop_bottom

                # head / NO-VEST 박스가 머리까지 침범하는 걸 조금 줄이기 위해
                # 위쪽 5%도 살짝 잘라서 순수 상체 비율을 키움
                crop_top = int(ph * 0.05)
                py1_adj = py1 + crop_top

                # 안전하게 화면 밖 안 나가게 클리핑
                py1_adj = max(0, py1_adj)
                py2_adj = min(H - 1, py2_adj)
                if py2_adj <= py1_adj:
                    continue

                persons.append((px1, py1_adj, px2, py2_adj))

        vest_boxes = []

        # 1) dets를 class별로 분리
        for d in dets:
            cls_id = d.get("cls")
            conf = float(d.get("conf", 0.0))
            box = d.get("box")
            if box is None or len(box) != 4:
                continue

            x1, y1, x2, y2 = map(int, box)
            pw = x2 - x1
            ph = y2 - y1
            if pw <= 0 or ph <= 0:
                continue

            # helmet / no-helmet / vest 는 min_ppe_conf로 필터
            if conf < self.min_ppe_conf:
                continue

            if self.helmet_id is not None and cls_id == self.helmet_id:
                helmet_boxes.append((x1, y1, x2, y2, conf))
            elif self.no_helmet_id is not None and cls_id == self.no_helmet_id:
                no_helmet_boxes.append((x1, y1, x2, y2, conf))
            elif self.vest_id is not None and cls_id == self.vest_id:
                vest_boxes.append((x1, y1, x2, y2, conf))

        # 2) helmet / no-helmet 판정
        if persons and (helmet_boxes or no_helmet_boxes):
            for (px1, py1, px2, py2) in persons:
                head_box = head_region((px1, py1, px2, py2), ratio=self.head_ratio)

                # helmet
                has_helmet = False
                for (hx1, hy1, hx2, hy2, hconf) in helmet_boxes:
                    if hconf < self.helmet_min_conf:
                        continue
                    if iou(head_box, (hx1, hy1, hx2, hy2)) >= self.helmet_head_iou:
                        has_helmet = True
                        if draw and overlay is not None:
                            cv2.rectangle(
                                overlay, (hx1, hy1), (hx2, hy2), (0, 255, 0), 2
                            )
                            cv2.putText(
                                overlay,
                                "HELMET",
                                (hx1, max(0, hy1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 0),
                                2,
                            )
                        break

                if has_helmet:
                    helmet_cnt += 1
                else:
                    # no-helmet 여부 확인
                    matched_no_helmet = False
                    for (nx1, ny1, nx2, ny2, nconf) in no_helmet_boxes:
                        if iou(head_box, (nx1, ny1, nx2, ny2)) >= self.helmet_head_iou:
                            matched_no_helmet = True
                            if draw and overlay is not None:
                                cv2.rectangle(
                                    overlay, (nx1, ny1), (nx2, ny2), (0, 0, 255), 2
                                )
                                cv2.putText(
                                    overlay,
                                    "NO-HELMET",
                                    (nx1, max(0, ny1 - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6,
                                    (0, 0, 255),
                                    2,
                                )
                            break

                    if matched_no_helmet:
                        no_helmet_cnt += 1

        # 3) person별 vest / no-vest 판정
        if persons:
            for (px1, py1, px2, py2) in persons:
                ph = py2 - py1
                if ph <= 0:
                    continue

                # torso 영역 정의 (사람 박스 내 비율)
                ty1 = int(py1 + ph * self.vest_torso_top)
                ty2 = int(py1 + ph * self.vest_torso_bottom)
                torso_box = (px1, ty1, px2, ty2)

                has_vest = False
                tx1, ty1, tx2, ty2 = torso_box

                for (vx1, vy1, vx2, vy2, vconf) in vest_boxes:
                    cx = (vx1 + vx2) // 2
                    cy = (vy1 + vy2) // 2

                    # 중심점이 torso 안에 들어오거나
                    center_in_torso = (tx1 <= cx <= tx2) and (ty1 <= cy <= ty2)

                    # IoU가 vest_torso_iou 이상이면
                    overlap_iou = iou(torso_box, (vx1, vy1, vx2, vy2))

                    if center_in_torso or overlap_iou >= self.vest_torso_iou:
                        has_vest = True
                        if draw and overlay is not None:
                            cv2.rectangle(
                                overlay, (vx1, vy1), (vx2, vy2), (0, 255, 255), 2
                            )
                            cv2.putText(
                                overlay,
                                "VEST",
                                (vx1, max(0, vy1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 255),
                                2,
                            )
                        break

                if has_vest:
                    vest_cnt += 1
                else:
                    no_vest_cnt += 1

                    if draw and overlay is not None:
                        # NO-VEST 표시용 상체 박스
                        start_ratio = max(self.vest_draw_top, self.head_ratio)
                        dy1 = int(py1 + ph * start_ratio)
                        dy2 = int(py1 + ph * self.vest_draw_bottom)
                        cv2.rectangle(
                            overlay,
                            (px1, dy1),
                            (px2, dy2),
                            (0, 0, 255),
                            2,
                        )
                        cv2.putText(
                            overlay,
                            "NO-VEST",
                            (px1, max(0, dy1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2,
                        )

        # 4) 프레임 기반 vest 상태 히스토리 적용
        frame_vest_safe = (vest_cnt > 0 and no_vest_cnt == 0)
        frame_no_vest_only = (no_vest_cnt > 0 and vest_cnt == 0)

        if frame_vest_safe or frame_no_vest_only:
            cur = frame_vest_safe  # True면 vest 있음, False면 no-vest
            if self.vest_state is None or self.vest_state == cur:
                self.vest_state_frames += 1
            else:
                self.vest_state_frames = 1

            if self.vest_state_frames >= self.vest_min_frames:
                self.vest_state = cur

        if self.vest_state is not None:
            vest_safe = self.vest_state
        else:
            vest_safe = frame_vest_safe

        # 최종 helmet / vest 안전 여부
        helmet_safe = (helmet_cnt > 0 and no_helmet_cnt == 0)

        if helmet_safe and vest_safe:
            unsafe_prob = 0.0
        else:
            unsafe_prob = 1.0

        # 디버그 출력
        print(
            f"[HJ] dets={len(dets)}, helmet={helmet_cnt}, "
            f"no_helmet={no_helmet_cnt}, vest={vest_cnt}, no_vest={no_vest_cnt}, "
            f"vest_safe={vest_safe}, unsafe_prob={unsafe_prob:.2f}"
        )

        return unsafe_prob, overlay
