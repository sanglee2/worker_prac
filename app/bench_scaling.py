import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class TaskResult:
    task_id: str
    kind: str
    created_at: float
    completed_at: float | None = None

    @property
    def latency(self) -> float | None:
        if self.completed_at is None:
            return None
        return self.completed_at - self.created_at


async def enqueue_task(client: httpx.AsyncClient, base_url: str, kind: str, idx: int) -> TaskResult:
    created_at = time.perf_counter()
    if kind == "stt":
        payload = {"audio_uri": f"gs://bucket/audio/user-{idx}.wav"}
        response = await client.post(f"{base_url}/enqueue/stt", json=payload)
    else:
        payload = {"doc_uri": f"gs://bucket/contracts/user-{idx}.pdf"}
        response = await client.post(f"{base_url}/enqueue/ocr", json=payload)

    response.raise_for_status()
    task_id = response.json()["task_id"]
    return TaskResult(task_id=task_id, kind=kind, created_at=created_at)


async def poll_results(
    client: httpx.AsyncClient,
    base_url: str,
    tasks: list[TaskResult],
    poll_interval: float,
    timeout_s: float,
) -> None:
    deadline = time.perf_counter() + timeout_s
    pending = {task.task_id: task for task in tasks}

    while pending:
        if time.perf_counter() > deadline:
            raise TimeoutError(f"Timeout while waiting for {len(pending)} tasks")

        for task_id, task in list(pending.items()):
            response = await client.get(f"{base_url}/result/{task_id}")
            response.raise_for_status()
            payload = response.json()
            if payload.get("ready"):
                task.completed_at = time.perf_counter()
                pending.pop(task_id)

        if pending:
            await asyncio.sleep(poll_interval)


def summarize(tasks: list[TaskResult]) -> dict:
    latencies = [task.latency for task in tasks if task.latency is not None]
    if not latencies:
        return {}

    latencies_sorted = sorted(latencies)
    p50 = latencies_sorted[int(0.50 * (len(latencies_sorted) - 1))]
    p95 = latencies_sorted[int(0.95 * (len(latencies_sorted) - 1))]
    return {
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "mean": statistics.mean(latencies),
        "p50": p50,
        "p95": p95,
    }


async def run_benchmark(args: argparse.Namespace) -> None:
    timeout_s = args.timeout
    poll_interval = args.poll_interval
    base_url = args.base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        tasks: list[TaskResult] = []
        user_tasks = []

        for user_index in range(args.users):
            for _ in range(args.stt_per_user):
                user_tasks.append(enqueue_task(client, base_url, "stt", user_index))
            for _ in range(args.ocr_per_user):
                user_tasks.append(enqueue_task(client, base_url, "ocr", user_index))

        tasks.extend(await asyncio.gather(*user_tasks))
        await poll_results(client, base_url, tasks, poll_interval=poll_interval, timeout_s=timeout_s)

    stt_tasks = [task for task in tasks if task.kind == "stt"]
    ocr_tasks = [task for task in tasks if task.kind == "ocr"]

    print("Benchmark summary")
    print(f"Total tasks: {len(tasks)} (stt={len(stt_tasks)}, ocr={len(ocr_tasks)})")
    print("\nSTT latency (s):")
    print(summarize(stt_tasks))
    print("\nOCR latency (s):")
    print(summarize(ocr_tasks))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-user scaling benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--stt-per-user", type=int, default=5)
    parser.add_argument("--ocr-per-user", type=int, default=2)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=300.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_benchmark(args))
