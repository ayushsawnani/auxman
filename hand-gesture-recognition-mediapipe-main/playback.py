import threading
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import webbrowser

from client_vars import SP_CLIENT_ID, SP_CLIENT_SECRET, SP_REDIRECT_URI, SP_SCOPES

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/exchange_token": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
        }
    },
    methods=["GET", "POST", "OPTIONS"],
    supports_credentials=True,
)

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
token_info = {}

# Step 1: React redirects user to Spotify login
# Step 2: React gets code, calls this endpoint


@app.route("/exchange_token", methods=["POST", "OPTIONS"])
def exchange_token():
    if request.method == "OPTIONS":
        print("✅ Preflight request handled")
        return "", 204  # No content, means preflight accepted

    global token_info
    code = request.json.get("code")  # type: ignore
    print("📥 Received code from React:", code)

    if not code:
        return jsonify({"error": "Missing code"}), 400

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SP_REDIRECT_URI,
            "client_id": SP_CLIENT_ID,
            "client_secret": SP_CLIENT_SECRET,
        },
    )

    if response.status_code != 200:
        print("❌ Token exchange failed")
        return (
            jsonify({"error": "Token exchange failed", "details": response.text}),
            400,
        )

    token_info = response.json()
    token_info["expires_at"] = int(time.time()) + token_info["expires_in"]

    print("✅ Access token acquired from React flow!")
    return jsonify({"success": True})


def get_valid_token():
    global token_info

    if token_info and time.time() > token_info["expires_at"] - 60:
        print("🔁 Refreshing token...")
        response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_info["refresh_token"],
                "client_id": SP_CLIENT_ID,
                "client_secret": SP_CLIENT_SECRET,
            },
        )
        new_token = response.json()
        token_info["access_token"] = new_token["access_token"]
        token_info["expires_in"] = new_token["expires_in"]
        token_info["expires_at"] = int(time.time()) + new_token["expires_in"]

    return token_info.get("access_token")


ACTIONS = {
    "p": ("pause", "PUT", "https://api.spotify.com/v1/me/player/pause"),
    "r": ("resume", "PUT", "https://api.spotify.com/v1/me/player/play"),
    "n": ("next", "POST", "https://api.spotify.com/v1/me/player/next"),
    "b": ("previous", "POST", "https://api.spotify.com/v1/me/player/previous"),
}


def control_spotify(action_key):
    action = ACTIONS.get(action_key)
    if not action:
        return

    name, method, url = action
    token = token_info.get("access_token")

    if not token:
        print("No valid Spotify token.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    response = getattr(requests, method.lower())(url, headers=headers)

    if response.status_code in [204, 202, 403]:
        print(f"🎵 Spotify: {name} successful")
    else:
        print(
            f"❌ Spotify API error for {name}: {response.status_code} {response.text}"
        )


def poll_gesture_api():
    try:
        res = requests.get("http://127.0.0.1:5001/gesture")
        if res.status_code == 200:
            data = res.json()
            gesture = data.get("gesture")
            hand = data.get("hand")
            print(f"🖐️ Detected: {gesture} ({hand})")

            if gesture == "Close" and hand == "Left":
                control_spotify("p")  # pause
            elif gesture == "Open" and hand == "Left":
                control_spotify("r")  # resume
            if gesture == "Swipe Right" and hand == "Left":
                control_spotify("n")  # next
            elif gesture == "Swipe Left" and hand == "Left":
                control_spotify("b")  # back
        else:
            print(f"Gesture API error: {res.status_code}")

        return gesture
    except Exception as e:
        print("Could not reach gesture API:", e)


if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(port=5000, debug=False)).start()

    print("🟢 Waiting for token from React frontend...")
    while not token_info:
        time.sleep(1)

    print("✅ Token ready. Now polling gesture API...")
    while True:
        poll_gesture_api()
        time.sleep(1)
