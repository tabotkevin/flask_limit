from flask import Flask, jsonify

from flask_limit import RateLimiter

app = Flask(__name__)

app.config["RATELIMIT_LIMIT"] = 5
app.config["RATELIMIT_PERIOD"] = 10  # 5 requests every 10 seconds

limiter = RateLimiter(app, limiter="memory")


@app.route("/")
@limiter.rate_limit  # Uses the app.config defaults (5 req / 10 sec)
def index():
    return jsonify({"message": "Welcome! You are using the Memory backend."})


@app.route("/strict")
@limiter.rate_limit(limit=2, period=60)  # Overrides config: 2 req / 60 sec
def strict_route():
    return jsonify({"message": "This route is strictly limited."})


@app.route("/unlimited")
def unlimited_route():
    # No decorator means no rate limit
    return jsonify({"message": "You can hit this route as fast as you want!"})


if __name__ == "__main__":
    # Run with a single process (memory backend doesn't share state across workers)
    app.run(debug=True, port=5001)
