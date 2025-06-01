import os
import time
import threading
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv()  # Load from .env

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-library-modify",
    "playlist-read-private",
    "user-library-read"
]

class SpotifyController:
    def __init__(self):
        self.sp = Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope=" ".join(SCOPES)
        ))

        # Volume control state
        self._volume_lock = threading.Lock()
        self._volume_delta = 0
        self._last_volume = None
        self._current_volume = None
        self._last_volume_change = 0
        self._toast_duration = 1.5  # Seconds to keep toast on screen
        self._scroll_offset = 0
        self._last_scroll_time = time.time()
        self._cached_art_url = None
        self._cached_art_image = None



        # Renderer will be injected externally (e.g., from StreamDeckDeviceManager)
        self._renderer = None

        # Start the volume worker thread
        t = threading.Thread(target=self._volume_worker, daemon=True)
        t.start()

    def play_pause(self):
        state = self.sp.current_playback()
        if state and state["is_playing"]:
            self.sp.pause_playback()
        else:
            self.sp.start_playback()

    def next_track(self):
        self.sp.next_track()

    def previous_track(self):
        self.sp.previous_track()

    def toggle_shuffle(self):
        current = self.sp.current_playback()
        if current:
            state = current.get("shuffle_state", False)
            self.sp.shuffle(not state)

    def toggle_repeat(self):
        current = self.sp.current_playback()
        if current:
            mode = current.get("repeat_state", "off")
            next_mode = {"off": "context", "context": "track", "track": "off"}[mode]
            self.sp.repeat(next_mode)

    def like_current_track(self):
        current = self.sp.current_playback()
        if current:
            track_id = current["item"]["id"]
            self.sp.current_user_saved_tracks_add([track_id])

    def play_playlist(self, uri):
        self.sp.start_playback(context_uri=uri)

    def now_playing_info(self):
        current = self.sp.current_playback()
        if not current or not current.get("item"):
            return None
        item = current["item"]
        return {
            "track": item["name"],
            "artist": ", ".join([a["name"] for a in item["artists"]]),
            "album": item["album"]["name"],
            "art_url": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
            "progress": current["progress_ms"],
            "duration": item["duration_ms"],
            "shuffle": current["shuffle_state"],
            "repeat": current["repeat_state"],
            "is_playing": current["is_playing"]
        }
    
    def get_playlist_icon_url(self, playlist_uri: str) -> str | None:
        try:
            playlist = self.sp.playlist(playlist_uri)
            if playlist:
                return playlist["images"][0]["url"] if playlist["images"] else None
            else:
                return None
        except Exception as e:
            print(f"[WARN] Failed to get icon for playlist {playlist_uri}: {e}")
            return None
        
    def play_liked_songs(self):
        try:
            liked = self.sp.current_user_saved_tracks(limit=50)
            items = liked.get("items", []) if liked else []

            uris = [item["track"]["uri"] for item in items if item.get("track") and item["track"].get("uri")]

            if not uris:
                print("[WARN] No liked songs available to play.")
                return

            self.sp.start_playback(uris=uris)

        except Exception as e:
            print(f"[ERROR] Failed to play liked songs: {e}")

    def volume_up(self):
        self._adjust_volume(5)

    def volume_down(self):
        self._adjust_volume(-5)

    def _adjust_volume(self, delta):
        with self._volume_lock:
            self._volume_delta += delta

    def _volume_worker(self):
        cooldown = 1.0  # Enforce at most one API call per second
        last_api_call = 0

        while True:
            time.sleep(0.3)  # Check ~3 times per second

            now = time.time()

            with self._volume_lock:
                delta = self._volume_delta
                self._volume_delta = 0

            if delta == 0:
                continue

            if now - last_api_call < cooldown:
                with self._volume_lock:
                    # Requeue the delta for next check
                    self._volume_delta += delta
                continue

            try:
                playback = self.sp.current_playback()
                if not playback:
                    print("[WARN] No active playback.")
                    continue

                device = playback.get("device", {})
                current = device.get("volume_percent")
                device_id = device.get("id")

                if current is None or device_id is None:
                    print("[WARN] Missing device or volume info.")
                    continue

                new_volume = max(0, min(current + delta, 100))

                if new_volume == current:
                    continue

                self.sp.volume(new_volume, device_id)

                self._current_volume = new_volume
                self._last_volume_change = time.time()
                self._last_volume = new_volume
                last_api_call = time.time()

                print(f"[OK] Volume set to {new_volume}%")

            except Exception as e:
                print(f"[ERROR] Volume update failed: {e}")
                if "rate" in str(e).lower():
                    print("[BACKOFF] Hit rate limit — delaying next attempt.")
                    last_api_call = time.time() + 2


    def toggle_mute(self):
        try:
            playback = self.sp.current_playback()
            if not playback:
                print("[WARN] No active playback.")
                return

            device = playback.get("device", {})
            current_volume = device.get("volume_percent")
            device_id = device.get("id")

            if device_id is None or current_volume is None:
                print("[WARN] Device ID or volume not available.")
                return

            if current_volume > 0:
                self._last_volume = current_volume
                self.sp.volume(0, device_id)
                print(f"[OK] Muted (saved volume: {self._last_volume}%)")
            else:
                restored = self._last_volume if self._last_volume is not None else 50
                self.sp.volume(restored, device_id)
                print(f"[OK] Unmuted to {restored}%")
                self._last_volume = None  # Clear after unmute

        except Exception as e:
            print(f"[ERROR] Failed to toggle mute: {e}")

    def render_volume_toast(self):
        if not self._renderer:
            return

        if time.time() - self._last_volume_change > self._toast_duration:
            return

        img = self._renderer.render_volume_toast_image(self._current_volume or 0)
        self._renderer.set_touchscreen_image(img)

    def render_now_playing(self):
        if not self._renderer:
            return

        info = self.now_playing_info()
        if not info:
            return

        now = time.time()
        delta = now - self._last_scroll_time
        self._scroll_offset += int(delta * 40)  # scroll speed
        self._last_scroll_time = now

        art_url = info.get("art_url")
        if art_url and art_url != self._cached_art_url:
            try:
                response = requests.get(art_url)
                response.raise_for_status()
                art = Image.open(BytesIO(response.content)).convert("RGB")
                self._cached_art_image = art
                self._cached_art_url = art_url
                print("[CACHE] New album art fetched")
            except Exception as e:
                print(f"[WARN] Failed to cache album art: {e}")
                self._cached_art_image = None


        img = self._renderer.render_now_playing_screen(info, scroll_offset=self._scroll_offset, art_image=self._cached_art_image)
        self._renderer.set_touchscreen_image(img)



    def render_touchscreen(self):
        if not self._renderer:
            return

        if time.time() - self._last_volume_change < self._toast_duration:
            self.render_volume_toast()
        else:
            self.render_now_playing()

