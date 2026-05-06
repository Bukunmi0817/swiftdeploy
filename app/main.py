import os
import time
import random
from flask import Flask, jsonify, request, make_response
from datetime import datetime, timezone
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Read environment variables once at startup
MODE = os.environ.get("MODE", "stable")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
APP_PORT = int(os.environ.get("APP_PORT", 3000))

# Record when app started so we can calculate uptime
START_TIME = time.time()

# Store current chaos state in memory
chaos_state = {"mode": None, "duration": None, "rate": None}

# Create the Flask app
app = Flask(__name__)

# ─── PROMETHEUS METRICS ───────────────────────────────────
# Counter - total requests by method, path, status code
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"]
)

# Histogram - request duration in seconds
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Gauge - app uptime in seconds
UPTIME_GAUGE = Gauge(
    "app_uptime_seconds",
    "Application uptime in seconds"
)

# Gauge - current mode (0=stable, 1=canary)
MODE_GAUGE = Gauge(
    "app_mode",
    "Current deployment mode (0=stable, 1=canary)"
)

# Gauge - chaos state (0=none, 1=slow, 2=error)
CHAOS_GAUGE = Gauge(
    "chaos_active",
    "Current chaos state (0=none, 1=slow, 2=error)"
)

# Set initial gauge values
MODE_GAUGE.set(1 if MODE == "canary" else 0)
CHAOS_GAUGE.set(0)


def make_response_with_mode(data, status=200):
    """
    Helper function that creates a response and adds
    the X-Mode: canary header if we are in canary mode.
    """
    response = make_response(jsonify(data), status)
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


@app.before_request
def apply_chaos():
    """
    Runs before every request.
    If chaos is active, applies the chaos effect.
    Excludes /metrics and /healthz from chaos effects.
    """
    if request.path in ["/metrics", "/healthz"]:
        return
    if chaos_state["mode"] == "slow":
        time.sleep(chaos_state["duration"])
    elif chaos_state["mode"] == "error":
        if random.random() < chaos_state["rate"]:
            return make_response_with_mode(
                {"error": "chaos error", "code": 500},
                500
            )


@app.after_request
def record_metrics(response):
    """
    Runs after every request.
    Records request count and duration metrics.
    """
    # Update uptime gauge
    UPTIME_GAUGE.set(int(time.time() - START_TIME))

    # Record request count with labels
    REQUEST_COUNT.labels(
        method=request.method,
        path=request.path,
        status_code=str(response.status_code)
    ).inc()

    return response


@app.route("/")
def home():
    start = time.time()
    data = {
        "message": "Welcome to SwiftDeploy",
        "mode": MODE,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    response = make_response_with_mode(data)
    REQUEST_DURATION.labels(method="GET", path="/").observe(time.time() - start)
    return response


@app.route("/healthz")
def health():
    start = time.time()
    uptime = int(time.time() - START_TIME)
    data = {
        "status": "healthy",
        "uptime": uptime
    }
    response = make_response_with_mode(data)
    REQUEST_DURATION.labels(method="GET", path="/healthz").observe(time.time() - start)
    return response


@app.route("/metrics")
def metrics():
    """
    Exposes all metrics in Prometheus text format.
    This is what swiftdeploy status and pre-promote scrape.
    """
    UPTIME_GAUGE.set(int(time.time() - START_TIME))
    MODE_GAUGE.set(1 if MODE == "canary" else 0)
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/chaos", methods=["POST"])
def chaos():
    # Only available in canary mode
    if MODE != "canary":
        return make_response_with_mode(
            {"error": "chaos endpoint only available in canary mode"},
            403
        )

    data = request.get_json()
    if not data:
        return make_response_with_mode({"error": "request body required"}, 400)

    chaos_mode = data.get("mode")

    if chaos_mode == "slow":
        duration = data.get("duration", 1)
        chaos_state["mode"] = "slow"
        chaos_state["duration"] = duration
        CHAOS_GAUGE.set(1)
        return make_response_with_mode({
            "message": f"chaos activated: slow mode for {duration}s"
        })

    elif chaos_mode == "error":
        rate = data.get("rate", 0.5)
        chaos_state["mode"] = "error"
        chaos_state["rate"] = rate
        CHAOS_GAUGE.set(2)
        return make_response_with_mode({
            "message": f"chaos activated: error mode at {rate} rate"
        })

    elif chaos_mode == "recover":
        chaos_state["mode"] = None
        chaos_state["duration"] = None
        chaos_state["rate"] = None
        CHAOS_GAUGE.set(0)
        return make_response_with_mode({
            "message": "chaos recovered: back to normal"
        })

    else:
        return make_response_with_mode({"error": "unknown chaos mode"}, 400)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)
