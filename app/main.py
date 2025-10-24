from fastapi import FastAPI, Body, Query
from celery.result import AsyncResult
from celery_app import celery_app
from tasks import transcribe_chunk, run_ocr

### 작업넣기, 결과조회

app = FastAPI(title="STT/OCR Worker Demo", version="1.0.0")

@app.get("/")
def root():
    return {
        "message": "STT/OCR Worker Demo",
        "endpoints": [
            "POST /enqueue/stt {audio_uri}",
            "POST /enqueue/ocr {doc_uri}",
            "POST /demo/burst?stt=N&ocr=M",
            "GET  /result/{task_id}",
        ],
    }

## stt 작업을 큐에 넣기.
@app.post("/enqueue/stt")
def enqueue_stt(audio_uri: str = Body(..., embed=True)):
    task = transcribe_chunk.delay(audio_uri)
    return {"queued": True, "queue": "stt", "task_id": task.id}

@app.post("/enqueue/ocr")
def enqueue_ocr(doc_uri: str = Body(..., embed=True)):
    task = run_ocr.delay(doc_uri)
    return {"queued": True, "queue": "ocr", "task_id": task.id}

@app.post("/demo/burst")
def demo_burst(stt: int = Query(10, ge=0, le=200), ocr: int = Query(10, ge=0, le=200)):
    stt_ids = [transcribe_chunk.delay(f"gs://bucket/audio/{i}.wav").id for i in range(stt)]
    ocr_ids = [run_ocr.delay(f"gs://bucket/contracts/{i}.pdf").id for i in range(ocr)]
    return {"queued": {"stt": len(stt_ids), "ocr": len(ocr_ids)}, "task_ids": stt_ids + ocr_ids}

### 테스크 상태 & 결과조회
@app.get("/result/{task_id}")
def get_result(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    payload = {"id": task_id, "ready": result.ready(), "status": result.status}
    if result.ready():
        payload["result"] = result.result
    return payload
