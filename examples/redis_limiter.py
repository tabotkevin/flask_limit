from flask import Flask, jsonify

from flask_limit import RateLimiter

app = Flask(__name__)

app.config["RATELIMIT_LIMIT"] = 10
app.config["RATELIMIT_PERIOD"] = 60
app.config["RATELIMIT_KEY_PREFIX"] = "my_api"  # Groups keys in Redis cleanly
app.config["RATELIMIT_REDIS_URL"] = "redis://localhost:6379/0"

limiter = RateLimiter(app, limiter="redis")


@app.route("/api/data")
@limiter.rate_limit  # Uses 10 req / 60 sec
def get_data():
    return jsonify({"data": "Here is your Redis-protected data!"})


@app.route("/api/login")
@limiter.rate_limit(limit=3, period=300)  # Uses 3 req / 5 min
def login_attempt():
    return jsonify({"status": "Login processed"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
