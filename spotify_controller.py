import time
import threading
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from io import BytesIO
from render_tasks.now_playing_task import NowPlayingTask  # You’ll create this
from render_tasks.volume_toast_task import VolumeToastTask
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

        self._poll_interval = 1.0
        self._last_poll_time = 0.0

    def update(self, now):
        if now - self._last_poll_time < self._poll_interval:
            return
        self._last_poll_time = now

        try:
            info = self.now_playing_info()
            if not info:
                return

            track_id = info["track_id"]
            is_playing = info["is_playing"]

            if track_id != self._last_track_id or is_playing != self._last_playing_state:
                self._last_track_id = track_id
                self._last_playing_state = is_playing

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

    def get_playlist_icon_url(self, playlist_uri):
        """Fetch the playlist cover image URL for a given playlist URI."""
        playlist_id = playlist_uri.split(":")[-1] if ":" in playlist_uri else playlist_uri
        try:
            data = self.sp.playlist(playlist_id)
            images = data.get("images", [])
            return images[0]["url"] if images else None
        except Exception as e:
            print(f"[WARN] Failed to fetch playlist icon: {e}")
            return None

    def play_liked_songs(self):
        """Play the user's saved (liked) songs."""
        try:
            results = self.sp.current_user_saved_tracks(limit=50)
            uris = [item["track"]["uri"] for item in results.get("items", [])]
            if uris:
                self.sp.start_playback(uris=uris)
        except Exception as e:
            print(f"[ERROR] Failed to play liked songs: {e}")

    def play_playlist(self, playlist_uri):
        """Start playback of a given playlist URI."""
        try:
            self.sp.start_playback(context_uri=playlist_uri)
        except Exception as e:
            print(f"[ERROR] Failed to play playlist {playlist_uri}: {e}")

    def start_recommendations(self):
        """Start a recommendation-based play queue based on the current track."""
        try:
            info = self.now_playing_info()
            if not info:
                return
            recs = self.sp.recommendations(seed_tracks=[info["track_id"]], limit=20)
            uris = [t["uri"] for t in recs.get("tracks", [])]
            if uris:
                self.sp.start_playback(uris=uris)
        except Exception as e:
            print(f"[ERROR] Failed to start recommendations: {e}")

    def like_current_track(self):
        """Save the currently playing track to the user's 'Liked Songs'."""
        try:
            info = self.now_playing_info()
            if not info:
                return
            self.sp.current_user_saved_tracks_add([info["track_id"]])
        except Exception as e:
            print(f"[ERROR] Failed to like current track: {e}")

    def previous_track(self):
        """Skip to the previous track."""
        try:
            self.sp.previous_track()
        except Exception as e:
            print(f"[ERROR] Failed to go to previous track: {e}")

    def play_pause(self):
        """Toggle playback state (play or pause)."""
        try:
            playback = self.sp.current_playback()
            if playback and playback.get("is_playing"):
                self.sp.pause_playback()
            else:
                self.sp.start_playback()
        except Exception as e:
            print(f"[ERROR] Failed to toggle play/pause: {e}")

    def next_track(self):
        """Skip to the next track."""
        try:
            self.sp.next_track()
        except Exception as e:
            print(f"[ERROR] Failed to skip to next track: {e}")

    def toggle_shuffle(self):
        """Toggle shuffle state."""
        try:
            playback = self.sp.current_playback()
            shuffle_state = playback.get("shuffle_state", False) if playback else False
            self.sp.shuffle(not shuffle_state)
        except Exception as e:
            print(f"[ERROR] Failed to toggle shuffle: {e}")

    def volume_up(self):
        """Increase volume by 10% and show a toast."""
        try:
            playback = self.sp.current_playback()
            volume = playback.get("device", {}).get("volume_percent", 0) if playback else 0
            new_volume = min(volume + 10, 100)
            self.sp.volume(new_volume)
            self.screen.show_toast(VolumeToastTask(self.screen, new_volume))
        except Exception as e:
            print(f"[ERROR] Failed to increase volume: {e}")

    def volume_down(self):
        """Decrease volume by 10% and show a toast."""
        try:
            playback = self.sp.current_playback()
            volume = playback.get("device", {}).get("volume_percent", 0) if playback else 0
            new_volume = max(volume - 10, 0)
            self.sp.volume(new_volume)
            self.screen.show_toast(VolumeToastTask(self.screen, new_volume))
        except Exception as e:
            print(f"[ERROR] Failed to decrease volume: {e}")

    def toggle_mute(self):
        """Mute/unmute and show a toast of the current volume."""
        try:
            playback = self.sp.current_playback()
            volume = playback.get("device", {}).get("volume_percent", 0) if playback else 0
            if volume > 0:
                self._previous_volume = volume
                self.sp.volume(0)
                current = 0
            else:
                prev = getattr(self, "_previous_volume", 50)
                self.sp.volume(prev)
                current = prev
            self.screen.show_toast(VolumeToastTask(self.screen, current))
        except Exception as e:
            print(f"[ERROR] Failed to toggle mute: {e}")
