import time
import threading
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from io import BytesIO
from render_tasks.now_playing_task import NowPlayingTask  # You’ll create this
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-library-modify",
    "playlist-read-private",
    "user-library-read"
]

class SpotifyController:
    def __init__(self, screen_manager):
        self.screen = screen_manager

        self.sp = Spotify(auth_manager=SpotifyOAuth(scope=" ".join(SCOPES)))

        self._last_track_id = None
        self._last_playing_state = None

        self._cached_art_url = None
        self._cached_art_image = None

    def update(self, now):
        try:
            info = self.now_playing_info()
            if not info:
                return

            track_id = info["track_id"]
            is_playing = info["is_playing"]

            # Only update screen if track changed or state changed
            if track_id != self._last_track_id or is_playing != self._last_playing_state:
                self._last_track_id = track_id
                self._last_playing_state = is_playing

                # Refresh album art cache if needed
                art = self._get_album_art(info["art_url"])

                task = NowPlayingTask(info, art)
                self.screen.set_view(task)

        except Exception as e:
            print(f"[ERROR] Spotify update failed: {e}")

    def now_playing_info(self):
        playback = self.sp.current_playback()
        if not playback or not playback.get("item"):
            return None

        item = playback["item"]
        return {
            "track": item["name"],
            "artist": ", ".join([a["name"] for a in item["artists"]]),
            "album": item["album"]["name"],
            "track_id": item["id"],
            "art_url": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
            "progress": playback["progress_ms"],
            "duration": item["duration_ms"],
            "is_playing": playback["is_playing"]
        }

    def _get_album_art(self, url):
        if not url or url == self._cached_art_url:
            return self._cached_art_image

        try:
            response = requests.get(url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGB")
            self._cached_art_image = img
            self._cached_art_url = url
            print("[CACHE] New album art fetched")
            return img
        except Exception as e:
            print(f"[WARN] Failed to fetch album art: {e}")
            return None
