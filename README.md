# Smart Safety Camera (PPE Detection & Alert)

산업 현장에서 작업자의 헬멧(Helmet) / 조끼(Vest) 착용 여부를 실시간 탐지하여
미착용 시 현장 알림 + Web/App 알림까지 연동하는 Smart Safety System입니다.

---

## 프로젝트 요약

| 항목 | 내용 |
|---|---|
| 기간 / 인원 | 1달 / 3명 |
| 내 역할 | Detecting 펌웨어 구현(탐지 동작/연동 중심) |
| 플랫폼 | Raspberry Pi 5 + Raspberry Pi Camera v3 |
| 주요 기술 | YOLOv8, Python 3.11, OpenCV, GPIO, Ultralytics YOLO Framework |
| 알림/모니터링 | Web Alert(대시보드), App Alert(MIT App Inventor) |
| 상태 분류 | SAFE / WARNING / DANGER |

---

## What it does

- 카메라 영상에서 Helmet/Vest 착용 여부를 탐지
- 규칙 기반으로 상태를 판정하고(아래 규칙표), 미착용 시 알림을 발생
- 현장 상태 표시 + Web/App로 위험 상황을 전달

---

## 상태 판정 규칙 (SAFE / WARNING / DANGER)

| Helmet | Vest | Status |
|---|---|---|
| ON | ON | SAFE |
| OFF | ON | WARNING |
| ON | OFF | WARNING |
| OFF | OFF | DANGER |

---

## 주요 기능

- Real-time PPE Detection: Helmet/Vest 탐지
- Rule-based Decision: SAFE/WARNING/DANGER 상태 판정
- Alert Output
  - 현장 알림(LED/Alert)
  - Web Alert(대시보드)
  - App Alert(실시간 상태/알림, 로그 조회, CSV 로그 조회)

---

## Demo / Evidence

- PPT에 케이스별 결과 이미지가 포함되어 있음:
  - SAFE: Helmet ON + Vest ON
  - WARNING: Helmet OFF 또는 Vest OFF
  - DANGER: Helmet OFF + Vest OFF
- 프로젝트 작동 영상(슬라이드에 언급)

> (추가 예정) 시연 영상 링크 / 스크린샷 / 현장 알림 사진

---

## Technical Challenge

- Hailo NPU 적용을 고려했으나, HEF 출력 포맷 부재/호환 이슈로 최종 적용 실패
- 최종은 YOLO 기반(.pt)으로 동작

---

## Repository Guide

- `app/` : 실행/서비스
- `models/` : 모델(.pt 등)
- `data/` : 입력/샘플
- `logs/` : 로그/CSV


---

## References (근거/검증용)

- Capstone Final PPT (상태 규칙/결과/스택 근거): 첨부된 `smart_safety.pdf`
- 기술 스택/구성 근거(발표자료):
  - Raspberry Pi 5 / Raspberry Pi Camera v3
  - YOLOv8 / Python 3.11 / OpenCV / GPIO / Ultralytics
  - Web Alert / App Alert(MIT App Inventor)
