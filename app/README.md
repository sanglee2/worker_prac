# STT/OCR Workers Demo (Celery + Redis + FastAPI + Docker Compose)

두 개의 큐(`stt`, `ocr`)와 각각의 워커를 분리해 **역할별 오토스케일**을 체험하는 최소 예제입니다.

## 빠른 실행

```bash
# 1) 프로젝트 루트에서
docker compose up -d --build

# 2) 상태/모니터링
# Flower 대시보드: http://localhost:5555
# FastAPI 문서:    http://localhost:8000/docs

# 3) 작업 넣기
curl -X POST http://localhost:8000/enqueue/stt -H "Content-Type: application/json" -d '{"audio_uri":"gs://bucket/audio/a.wav"}'
curl -X POST http://localhost:8000/enqueue/ocr -H "Content-Type: application/json" -d '{"doc_uri":"gs://bucket/contracts/lease.pdf"}'

# 4) 버스트(몰아넣기) - STT 25개, OCR 5개
curl -X POST "http://localhost:8000/demo/burst?stt=25&ocr=5"

# 5) 결과 조회
curl http://localhost:8000/result/<TASK_ID>
```

## 오토스케일(수량 조절) 예시

```bash
# 처음엔 1개씩
docker compose up -d --scale worker_stt=1 --scale worker_ocr=1

# STT 요청이 몰릴 때: STT 워커만 증설
docker compose up -d --scale worker_stt=4 --scale worker_ocr=1

# OCR이 바쁠 때: OCR 워커만 증설
docker compose up -d --scale worker_stt=1 --scale worker_ocr=3
```

> 핵심: **큐 이름을 분리(-Q stt / -Q ocr)** 했기 때문에, 각 워커 서비스의 **복제 수(Replica)**를 독립적으로 조절할 수 있습니다.

## 코드 핵심

- `celery_app.py` : 브로커/백엔드, 라우팅(작업→큐) 설정
- `tasks.py`      : STT/OCR 작업(더미 구현, 실패 5% 시뮬레이션)
- `main.py`       : 큐에 작업 넣는 REST API + 결과 조회
- `docker-compose.yml` : `worker_stt`, `worker_ocr` 두 서비스로 분리

## 관찰 포인트

1. **Flower**에서 `Queues` 탭을 보고, `stt`와 `ocr` 큐 길이가 다르게 변하는지 확인
2. 같은 양을 넣어도 **워커 복제 수**가 많은 쪽이 더 빨리 비워지는지 관찰
3. 실패(5%)가 발생하면 Celery의 **재시도/백오프**가 동작하는 로그 확인

## 멱등성(Idempotency)와 실서비스 팁

- 워커 시스템은 일반적으로 **at-least-once** 전달이므로, 작업은 **멱등성**을 확보하세요.
  - 동일 파일/청크의 해시(sha256)로 `idempotency_key`를 두고, 결과는 **업서트** 방식으로 저장.
- 긴 오디오/PDF는 **청크**로 잘라 여러 작업으로 나누고, 완료 후 **집계** 단계로 합치기.
- 외부 API 호출에는 **타임아웃** / **재시도 백오프** / **회로차단기**(circuit breaker) 권장.
