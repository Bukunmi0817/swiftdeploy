import os
import time
import random
from flask import Flask, jsonify, request, make_response
from datetime import datetime, timezone

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


def make_response_with_mode(data, status=200):
    """
    This helper function creates a response and adds
    the X-Mode: canary header if we are in canary mode.
    We use it on every endpoint so we don't repeat ourselves.
    """
    response = make_response(jsonify(data), status)
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


@app.route("/")
def home():
    data = {
        "message": "Welcome to SwiftDeploy",
        "mode": MODE,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return make_response_with_mode(data)


@app.route("/healthz")
def health():
    uptime = int(time.time() - START_TIME)
    data = {
        "status": "healthy",
        "uptime": uptime
    }
    return make_response_with_mode(data)


@app.route("/chaos", methods=["POST"])
def chaos():
    # Only available in canary mode
    if MODE != "canary":
        return make_response_with_mode(
            {"error": "chaos endpoint only available in canary mode"}, 
            403
        )

    # Read the JSON body from the request
    data = request.get_json()
    if not data:
        return make_response_with_mode({"error": "request body required"}, 400)

    chaos_mode = data.get("mode")

    if chaos_mode == "slow":
        # Store slow mode - requests will sleep for duration seconds
        duration = data.get("duration", 1)
        chaos_state["mode"] = "slow"
        chaos_state["duration"] = duration
        return make_response_with_mode({
            "message": f"chaos activated: slow mode for {duration}s"
        })

    elif chaos_mode == "error":
        # Store error mode - percentage of requests will return 500
        rate = data.get("rate", 0.5)
        chaos_state["mode"] = "error"
        chaos_state["rate"] = rate
        return make_response_with_mode({
            "message": f"chaos activated: error mode at {rate} rate"
        })

    elif chaos_mode == "recover":
        # Clear all chaos state
        chaos_state["mode"] = None
        chaos_state["duration"] = None
        chaos_state["rate"] = None
        return make_response_with_mode({
            "message": "chaos recovered: back to normal"
        })

    else:
        return make_response_with_mode({"error": "unknown chaos mode"}, 400)


@app.before_request
def apply_chaos():
    """
    This runs before every request.
    If chaos is active, it applies the chaos effect.
    """
    if chaos_state["mode"] == "slow":
        time.sleep(chaos_state["duration"])
    elif chaos_state["mode"] == "error":
        if random.random() < chaos_state["rate"]:
            return make_response_with_mode(
                {"error": "chaos error", "code": 500}, 
                500
            )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)