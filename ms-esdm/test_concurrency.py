import concurrent
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from services.esdm_auth import auto_login
from services.pipeline_id import run_pipeline

# === Configuration ===
CONCURRENCY_LEVELS = [1, 5, 30]  # number of concurrent runs
QUESTION = "Apakah daerah saya aman?"
GEO_LOCATION = (-6.2088, 106.8456)  # Jakarta
LOG_DIR = "concurrency_log"

os.makedirs(LOG_DIR, exist_ok=True)


def run_single_test():
    start = time.time()
    try:
        result = run_pipeline(QUESTION, geo_location=GEO_LOCATION)
        duration = round((time.time() - start) * 1000, 2)
        return {"status": "success", "duration_ms": duration, "result": result}

    except Exception as e:
        duration = round((time.time() - start) * 1000, 2)
        return {"status": "error", "duration_ms": duration, "error": str(e)}


def run_concurrency_test(concurrency: int):
    """Run tests concurrently and log results."""
    print(f"\n🚀 Running concurrency level: {concurrency}")
    start_total = time.time()
    results = []
    durations = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_single_test) for _ in range(concurrency)]
        for f in tqdm(as_completed(futures), total=concurrency, desc=f"Concurrency {concurrency}"):
            res = f.result()
            results.append(res)
            if "duration_ms" in res:
                durations.append(res["duration_ms"])

    end_total = time.time()
    total_time = round(end_total - start_total, 2)
    avg_time = round(sum(durations) / len(durations), 2) if durations else 0.0
    success = sum(1 for r in results if r["status"] == "success")
    fail = len(results) - success

    summary = {
        "concurrency_level": concurrency,
        "success": success,
        "fail": fail,
        "time_per_request_ms": durations,
        "total_time_s": total_time,
        "average_time_ms": avg_time,
    }

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = os.path.join(LOG_DIR, f"{timestamp}-concurrency-{concurrency}.json")
    with open(log_file, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)

    print(f"✅ Done — Success: {success}, Fail: {fail}, Avg: {avg_time} ms, Total: {total_time}s")
    print(f"📝 Detailed results saved to {log_file}")

    return summary


if __name__ == "__main__":
    all_summaries = {}
    auto_login()

    for level in CONCURRENCY_LEVELS:
        all_summaries[level] = run_concurrency_test(level)

    summary_file = os.path.join(LOG_DIR, f"summary_{time.strftime('%Y%m%d-%H%M%S')}.json")
    with open(summary_file, "w") as f:
        json.dump(all_summaries, f, indent=2, ensure_ascii=False)

    print("\n📊 All concurrency summaries saved to", summary_file)
