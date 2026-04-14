"""
Hospital Node — Metrics Server
Exposes these REAL metrics via Prometheus scraping:

  hospital_cpu_percent          - actual CPU usage of this container
  hospital_memory_percent       - actual memory usage
  hospital_avg_latency_ms       - average time to handle a request (ms)
  hospital_throughput_rps       - requests processed per second
  hospital_success_rate         - fraction of requests that succeeded (0–1)
  hospital_error_rate           - fraction that failed (0–1)
  hospital_request_total        - total requests handled
"""

import os, time, random, threading, psutil
from flask import Flask, Response, jsonify

app = Flask(__name__)

HOSPITAL_ID = os.environ.get("HOSPITAL_ID", "hospitalA")
PORT        = int(os.environ.get("PORT", 8000))

# WORKLOAD_INTENSITY controls how busy this node is (0.0=idle, 1.0=maxed)
# This makes each hospital genuinely different in performance
WORKLOAD = float(os.environ.get("WORKLOAD_INTENSITY", "0.3"))

# ── Shared metrics state ───────────────────────────────────────
state = {
    "total_requests":  0,
    "total_success":   0,
    "total_errors":    0,
    "total_latency_ms": 0.0,
    "window_requests": 0,   # requests in last 10s window
    "window_start":    time.time(),
}
lock = threading.Lock()


def process_one_request():
    """
    Simulates handling one patient data request.
    Does real CPU work. Returns (latency_ms, success).
    """
    start = time.time()

    # Real CPU work — intensity controls how long it takes
    work_ms = 10 + WORKLOAD * 90 + random.uniform(-5, 5)
    deadline = start + work_ms / 1000
    x = 0
    while time.time() < deadline:
        x += sum(i * i for i in range(300))

    # Random network jitter
    time.sleep(random.uniform(0, WORKLOAD * 0.03))

    latency_ms = (time.time() - start) * 1000

    # Higher workload = more failures
    success = random.random() > (WORKLOAD * 0.15)

    return latency_ms, success


def background_worker():
    """Continuously processes requests in the background."""
    while True:
        latency_ms, success = process_one_request()

        with lock:
            state["total_requests"]   += 1
            state["total_latency_ms"] += latency_ms
            state["window_requests"]  += 1
            if success:
                state["total_success"] += 1
            else:
                state["total_errors"]  += 1

        # Pace: process 1–5 requests per second depending on workload
        sleep_time = random.uniform(0.2, 0.8) / max(WORKLOAD, 0.1)
        time.sleep(min(sleep_time, 1.0))


# Start background worker thread
threading.Thread(target=background_worker, daemon=True).start()


# ── Computed metrics ───────────────────────────────────────────

def get_throughput_rps():
    """Requests processed per second over last 10s window."""
    with lock:
        elapsed = time.time() - state["window_start"]
        if elapsed < 1.0:
            return 0.0
        rps = state["window_requests"] / elapsed
        # Reset window every 10 seconds
        if elapsed >= 10.0:
            state["window_requests"] = 0
            state["window_start"]    = time.time()
        return round(rps, 3)

def get_avg_latency():
    with lock:
        n = state["total_requests"]
        return state["total_latency_ms"] / n if n > 0 else 0.0

def get_success_rate():
    with lock:
        n = state["total_requests"]
        return state["total_success"] / n if n > 0 else 1.0

def get_error_rate():
    with lock:
        n = state["total_requests"]
        return state["total_errors"] / n if n > 0 else 0.0


# ── Endpoints ──────────────────────────────────────────────────

@app.route("/metrics")
def prometheus_metrics():
    """
    Prometheus scrapes this every 10 seconds.
    Returns text in Prometheus exposition format.
    """
    cpu        = psutil.cpu_percent(interval=0.1)
    mem        = psutil.virtual_memory().percent
    latency    = get_avg_latency()
    throughput = get_throughput_rps()
    success    = get_success_rate()
    error      = get_error_rate()

    with lock:
        total_req = state["total_requests"]
        total_err = state["total_errors"]

    h = f'hospital="{HOSPITAL_ID}"'
    lines = [
        f'# HELP hospital_cpu_percent CPU usage %',
        f'# TYPE hospital_cpu_percent gauge',
        f'hospital_cpu_percent{{{h}}} {cpu:.2f}',

        f'# HELP hospital_memory_percent Memory usage %',
        f'# TYPE hospital_memory_percent gauge',
        f'hospital_memory_percent{{{h}}} {mem:.2f}',

        f'# HELP hospital_avg_latency_ms Avg request latency ms',
        f'# TYPE hospital_avg_latency_ms gauge',
        f'hospital_avg_latency_ms{{{h}}} {latency:.2f}',

        f'# HELP hospital_throughput_rps Requests per second',
        f'# TYPE hospital_throughput_rps gauge',
        f'hospital_throughput_rps{{{h}}} {throughput:.3f}',

        f'# HELP hospital_success_rate Success rate 0-1',
        f'# TYPE hospital_success_rate gauge',
        f'hospital_success_rate{{{h}}} {success:.4f}',

        f'# HELP hospital_error_rate Error rate 0-1',
        f'# TYPE hospital_error_rate gauge',
        f'hospital_error_rate{{{h}}} {error:.4f}',

        f'# HELP hospital_request_total Total requests processed',
        f'# TYPE hospital_request_total counter',
        f'hospital_request_total{{{h}}} {total_req}',

        f'# HELP hospital_error_total Total errors',
        f'# TYPE hospital_error_total counter',
        f'hospital_error_total{{{h}}} {total_err}',
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/metrics/json")
def json_metrics():
    """Human-readable JSON metrics — open in browser to check."""
    return jsonify({
        "hospital":      HOSPITAL_ID,
        "cpu_percent":   psutil.cpu_percent(interval=0.1),
        "memory_percent":psutil.virtual_memory().percent,
        "latency_ms":    round(get_avg_latency(), 2),
        "throughput_rps":round(get_throughput_rps(), 3),
        "success_rate":  round(get_success_rate(), 4),
        "error_rate":    round(get_error_rate(), 4),
        "total_requests":state["total_requests"],
        "workload":      WORKLOAD,
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "hospital": HOSPITAL_ID})


if __name__ == "__main__":
    print(f"[{HOSPITAL_ID}] Running on port {PORT}  workload={WORKLOAD}")
    app.run(host="0.0.0.0", port=PORT)
