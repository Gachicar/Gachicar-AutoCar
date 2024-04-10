# Gachicar-AutoCar
- '가치카' 프로젝트 AI AutoCar 주행 코드
- 서버와의 소켓 통신으로 제어
- 소켓으로 목적지 전송 시 해당 목적지로 이동

## 🚗 라인트래킹
- line_tracking folder
- 데이터 수집 후 모델링
- 정해진 라인을 따라 주행
- `track_follow_model.pth`

## 🚗 장애물 회피
- collision_avoid folder
- 데이터 수집 후 모델링: free/blocked 로 나누어 train
- 장애물로 인해 시야가 가려졌을 때 장애물로 인식
- 장애물 인식 시 후진
- `collision_final.pth` : 파일 용량 초과로 업로드X

## 🚗 객체 인식
- object_detection folder
- 설정된 객체를 인식하면 정지 및 도착 알림
- `ssd mobilenet v2 coco.engine`
> [장소별 객체 설정]
> - 집: 의자
> - 회사: 사람
> - 학교: 우산
