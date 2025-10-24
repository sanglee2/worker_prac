from celery import Celery

# Celery 애플리케이션 설정 및 라우팅
# - 브로커: Redis 0번 DB
# - 결과 백엔드: Redis 1번 DB
# - 큐 라우팅: STT 작업은 'stt', OCR 작업은 'ocr' 큐로 보냄

### 인스턴스화
celery_app = Celery(
    "contract_monitoring_demo",
    ###Celery가 메시지 주고받을 브로커(메시지 큐) 주소지정
    ## URI 형식
    ## redis:// -> 브로커로 redis사용 할 것임.
    ## redis:// '컴포즈에서 정의한 서비스명' DNS로 해석 / services.redis -> 도커네트워크 안 서비스명=호스트명
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

## 런타임 옵션변경
celery_app.conf.update(
    task_acks_late=True,                # 워커 비정상 종료 시 작업 재배달
    worker_prefetch_multiplier=1,       # 공정한 분배(작업 독점 방지)
    task_time_limit=300,                # 하드 타임아웃(초)
    task_soft_time_limit=240,           # 소프트 타임아웃(초)
)

# 작업 라우팅 규칙: 함수 이름 기준으로 큐를 분리
## 라우팅 테이블 설정
## 어떤 태스크가 어떤 큐로 들어갈지 결정
celery_app.conf.task_routes = {
    "tasks.transcribe_chunk": {"queue": "stt"},
    "tasks.run_ocr": {"queue": "ocr"},
}
