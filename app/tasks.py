import random
import time
from celery_app import celery_app

### 실제 Worker의 task들

def _sleep_random(min_s=0.5, max_s=2.0):
    # 처리 속도 차이를 체감하기 위한 의도적 지연 (큐 비우는 속도차이를)
    time.sleep(random.uniform(min_s, max_s))

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def transcribe_chunk(self, audio_uri: str) -> dict:
    """STT 시뮬레이션 작업.
    - 입력: 오디오 위치(URI)
    - 출력: 더미 전사 텍스트
    - 실패 확률: 5% (재시도 동작 확인용)
    """
    _sleep_random()
    if random.random() < 0.05:
        raise RuntimeError("Transient STT error (simulated)")
    text = f"[STT:{audio_uri.split('/')[-1]}] hello world (demo transcript)"
    return { "ok": True, "type": "stt", "audio": audio_uri, "text": text }

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def run_ocr(self, doc_uri: str, pages: list[int] | None = None) -> dict:
    """OCR 시뮬레이션 작업.
    - 입력: 문서 위치(URI), 선택적 페이지 목록
    - 출력: 더미 필드 추출 결과
    - 실패 확률: 5% (재시도 동작 확인용)
    """
    _sleep_random()
    if random.random() < 0.05:
        raise RuntimeError("Transient OCR error (simulated)")
    fields = { "임대인": "홍길동", "보증금": "10,000,000원" }
    return { "ok": True, "type": "ocr", "doc": doc_uri, "pages": pages, "fields": fields }
