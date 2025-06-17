"""
spotify_controller.py - SpotifyController module for Deckify

Handles communication with the Spotify Web API, background polling,
and mapping user interactions to Spotify playback and playlist operations.
"""
import time
import threading
import json
import requests
import logging
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from io import BytesIO
from render.tasks.render_tasks.now_playing_task import NowPlayingTask
from render.tasks.render_tasks.volume_toast_task import VolumeToastTask
from render.tasks.render_tasks.track_toast_task import TrackToastTask
from render.tasks.render_tasks.playlist_toast_task import PlaylistToastTask, PlaylistAddToastTask

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-library-modify",
    "playlist-read-private",
    "playlist-modify-private",
    "user-library-read",
]

class SpotifyController:
    def __init__(self, screen_manager, config_path):
        self.screen = screen_manager
        self.config_path = config_path

        # suppress spotipy.client HTTPError logs; we handle errors gracefully
        logging.getLogger('spotipy.client').setLevel(logging.CRITICAL)

        # Try to access the renderer if available from the screen manager
        self.renderer = getattr(screen_manager, 'renderer', None)

        self.sp = Spotify(auth_manager=SpotifyOAuth(scope=" ".join(SCOPES)))
        # Dynamic playlist hotkey mapping: key -> playlist URI
        self._playlist_hotkeys = {}
        # Playlist browsing state
        self._playlist_uri = None
        self._playlist_tracks = []
        self._playlist_track_index = 0
        # User playlist browsing state (for dial-based playlist selection)
        self._user_playlists = []
        self._user_playlist_index = 0
        # Playlist-add (track to playlist) mode state
        self._playlist_add_mode = False
        self._playlist_add_start_time = 0.0
        self._playlist_add_timeout = 5.0
        self._like_button_key = None
        self._like_button_add_icon = None
        self._like_button_remove_icon = None
        self._like_button_mode_icon = None

        self._last_track_id = None
        self._last_playing_state = None
        self._last_shuffle_state = None
        self._last_repeat_state = None

        self._cached_art_url = None
        self._cached_art_image = None

        self._poll_interval = 2.0
        self._last_poll_time = 0.0

        # Start background polling thread to avoid blocking the UI/render loop
        self._stop_event = threading.Event()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _id_from_uri(self, uri):
        """Extract the ID portion from a Spotify URI or return it unchanged."""
        return uri.split(':')[-1] if uri and ':' in uri else uri

    def _fetch_playlist_name(self, playlist_uri):
        """Return the playlist name for a given URI, falling back to ID on error."""
        playlist_id = self._id_from_uri(playlist_uri)
        try:
            data = self.sp.playlist(playlist_id)
            return data.get('name', playlist_id)
        except Exception:
            return playlist_id

    def update(self, now, force=False):
        """
        Poll Spotify state and update the Now Playing view.
        If force is True, ignore the regular poll interval and update immediately.
        """
        # Exit playlist-add mode on timeout if user did not select a hotkey
        if self._playlist_add_mode and (now - self._playlist_add_start_time) > self._playlist_add_timeout:
            try:
                self._exit_playlist_add_mode()
            except Exception:
                pass
        if not force and now - self._last_poll_time < self._poll_interval:
            return
        self._last_poll_time = now

        try:
            info = self.now_playing_info()
            if not info:
                return

            track_id = info["track_id"]
            is_playing = info["is_playing"]
            shuffle_state = info.get("shuffle_state", False)
            repeat_state = info.get("repeat_state", "off")

            if (track_id != self._last_track_id or is_playing != self._last_playing_state
                    or shuffle_state != self._last_shuffle_state
                    or repeat_state != self._last_repeat_state):
                self._last_track_id = track_id
                self._last_playing_state = is_playing
                self._last_shuffle_state = shuffle_state
                self._last_repeat_state = repeat_state

                art = self._get_album_art(info["art_url"])

                task = NowPlayingTask(info, art)
                self.screen.set_view(task)
            else:
                task = self.screen.current_task
                if isinstance(task, NowPlayingTask):
                    expected = task.info.get("progress", 0) + int((now - task.start_time) * 1000)
                    actual = info.get("progress", 0)
                    if abs(actual - expected) > 500:
                        art = self._get_album_art(info["art_url"])
                        task = NowPlayingTask(info, art)
                        self.screen.set_view(task)

            # --- Play/Pause icon toggle logic ---
            renderer = self.renderer or getattr(self.screen, 'renderer', None)
            if renderer:
                icon = "./assets/pause.png" if is_playing else "./assets/play.png"
                try:
                    renderer.update_button(5, image=icon)
                except Exception as e:
                    print(f"[WARN] Failed to update play/pause button icon: {e}")
                try:
                    if not self._playlist_add_mode:
                        contains = self.sp.current_user_saved_tracks_contains([track_id])
                        is_liked = bool(contains[0]) if contains else False
                        like_icon = "./assets/remove.png" if is_liked else "./assets/add.png"
                        renderer.update_button(7, image=like_icon)
                except Exception as e:
                    print(f"[WARN] Failed to update like button icon: {e}")
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
            "is_playing": playback["is_playing"],
            "shuffle_state": playback.get("shuffle_state", False),
            "repeat_state": playback.get("repeat_state", "off"),
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

    def _poll_loop(self):
        """Background loop to poll Spotify at regular intervals."""
        while not self._stop_event.is_set():
            now = time.time()
            try:
                self.update(now)
            except Exception as e:
                print(f"[ERROR] Spotify polling loop failed: {e}")
            time.sleep(self._poll_interval)

    def shutdown(self):
        """Stop the background polling thread."""
        self._stop_event.set()
        self._poll_thread.join()

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
            self.screen.show_toast(
                PlaylistToastTask(
                    self.screen,
                    self._fetch_playlist_name(playlist_uri),
                    prefix="Now Playing playlist",
                )
            )
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

    def is_current_track_liked(self):
        """Return True if the currently playing track is in the user's saved tracks."""
        try:
            info = self.now_playing_info()
            if not info:
                return False
            contains = self.sp.current_user_saved_tracks_contains([info["track_id"]])
            return bool(contains[0]) if contains else False
        except Exception as e:
            print(f"[WARN] Failed to check liked status: {e}")
            return False

    def like_current_track(self, button_key, add_icon, remove_icon):
        """Toggle the current track's liked state and update the button icon."""
        try:
            info = self.now_playing_info()
            if not info:
                return
            track_id = info["track_id"]
            contains = self.sp.current_user_saved_tracks_contains([track_id])
            is_liked = bool(contains[0]) if contains else False
            if is_liked:
                self.sp.current_user_saved_tracks_delete([track_id])
                new_icon = add_icon
            else:
                self.sp.current_user_saved_tracks_add([track_id])
                new_icon = remove_icon
            self.screen.renderer.update_button(button_key, image=new_icon)
        except Exception as e:
            print(f"[ERROR] Failed to toggle like for current track: {e}")

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

    def toggle_repeat(self):
        """Cycle repeat state: off -> context (all) -> track (one) -> off."""
        try:
            playback = self.sp.current_playback()
            state = playback.get("repeat_state", "off") if playback else "off"
            if state == "off":
                new_state = "context"
            elif state == "context":
                new_state = "track"
            else:
                new_state = "off"
            self.sp.repeat(new_state)
        except Exception as e:
            print(f"[ERROR] Failed to cycle repeat state: {e}")


    def volume_up(self):
        """Increase volume by 10% and show a toast."""
        try:
            playback = self.sp.current_playback()
            volume = playback.get("device", {}).get("volume_percent", 0) if playback else 0
            new_volume = min(volume + 10, 100)
            self.sp.volume(new_volume)
            self.screen.show_toast(VolumeToastTask(self.screen, volume, new_volume))
        except Exception as e:
            print(f"[ERROR] Failed to increase volume: {e}")

    def volume_down(self):
        """Decrease volume by 10% and show a toast."""
        try:
            playback = self.sp.current_playback()
            volume = playback.get("device", {}).get("volume_percent", 0) if playback else 0
            new_volume = max(volume - 10, 0)
            self.sp.volume(new_volume)
            self.screen.show_toast(VolumeToastTask(self.screen, volume, new_volume))
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
            self.screen.show_toast(VolumeToastTask(self.screen, volume, current))
        except Exception as e:
            print(f"[ERROR] Failed to toggle mute: {e}")

    def seek(self, position_ms):
        """Seek to a specified position (milliseconds) in the current track."""
        try:
            self.sp.seek_track(position_ms)
        except Exception as e:
            print(f"[ERROR] Failed to seek to position {position_ms}: {e}")

    def _ensure_playlist_tracks(self):
        """Load and cache tracks from the current playlist context."""
        # Determine current playlist URI from playback context
        try:
            playback = self.sp.current_playback()
            context = playback.get('context') if playback else None
            playlist_uri = context.get('uri') if context else None
        except Exception as e:
            print(f"[WARN] Failed to get playback context for playlist: {e}")
            # clear stale playlist data
            self._playlist_uri = None
            self._playlist_tracks = []
            self._playlist_track_index = 0
            return

        # Skip if no playlist or already attempted this playlist
        if not playlist_uri or playlist_uri == self._playlist_uri:
            return

        playlist_id = playlist_uri.split(":")[-1] if ":" in playlist_uri else playlist_uri
        tracks = []
        offset = 0
        limit = 100
        # Fetch items in pages; break on errors or end of items
        while True:
            try:
                resp = self.sp.playlist_items(
                    playlist_id,
                    offset=offset,
                    fields='items.track.name,items.track.artists.name,items.track.uri',
                    limit=limit
                )
            except Exception as e:
                print(f"[WARN] Failed to fetch items for playlist {playlist_uri}: {e}")
                # inform user this playlist cannot be browsed
                playlist_name = playlist_id
                try:
                    data = self.sp.playlist(playlist_id)
                    playlist_name = data.get('name', playlist_name)
                except Exception:
                    pass
                self.screen.show_toast(
                    PlaylistToastTask(
                        self.screen,
                        playlist_name,
                        prefix="Playlist not browsable"
                    )
                )
                break

            items = resp.get('items', [])
            for item in items:
                track = item.get('track')
                if not track:
                    continue
                name = track.get('name')
                artists = ', '.join([a.get('name') for a in track.get('artists', [])])
                uri = track.get('uri')
                tracks.append({'name': name, 'artists': artists, 'uri': uri})
            if len(items) < limit:
                break
            offset += limit

        # Update cached playlist data (even if tracks list is empty)
        self._playlist_uri = playlist_uri
        self._playlist_tracks = tracks
        # start dial selection on the currently playing track if found
        idx = 0
        try:
            info = self.now_playing_info()
            if info and info.get('track_id'):
                tid = info['track_id']
                for i, t in enumerate(tracks):
                    if t.get('uri', '').split(':')[-1] == tid:
                        idx = i
                        break
        except Exception:
            pass
        self._playlist_track_index = idx

    def select_next_track(self):
        """Scroll to the next track in the playlist and show toast."""
        self._ensure_playlist_tracks()
        if not self._playlist_tracks:
            self.screen.show_toast(
                PlaylistToastTask(
                    self.screen,
                    self._fetch_playlist_name(self._playlist_uri),
                    prefix="Playlist not browsable",
                )
            )
            return
        self._playlist_track_index = (self._playlist_track_index + 1) % len(self._playlist_tracks)
        track = self._playlist_tracks[self._playlist_track_index]
        self.screen.show_toast(TrackToastTask(self.screen, track['name'], track['artists']))

    def select_prev_track(self):
        """Scroll to the previous track in the playlist and show toast."""
        self._ensure_playlist_tracks()
        if not self._playlist_tracks:
            self.screen.show_toast(
                PlaylistToastTask(
                    self.screen,
                    self._fetch_playlist_name(self._playlist_uri),
                    prefix="Playlist not browsable",
                )
            )
            return
        self._playlist_track_index = (self._playlist_track_index - 1) % len(self._playlist_tracks)
        track = self._playlist_tracks[self._playlist_track_index]
        self.screen.show_toast(TrackToastTask(self.screen, track['name'], track['artists']))

    def confirm_selected_track(self):
        """Start playback of the currently selected track in the playlist."""
        self._ensure_playlist_tracks()
        if not self._playlist_tracks:
            return
        track = self._playlist_tracks[self._playlist_track_index]
        try:
            playback = self.sp.current_playback()
            context = playback.get('context') if playback else None
            if context and context.get('uri') and 'playlist' in context.get('uri'):
                self.sp.start_playback(context_uri=context['uri'], offset={'uri': track['uri']})
            else:
                self.sp.start_playback(uris=[track['uri']])
        except Exception as e:
            print(f"[ERROR] Failed to set selected track '{track['name']}': {e}")

    # --- User playlist browsing via dial ---
    def _ensure_user_playlists(self):
        """Load and cache all of the user's playlists."""
        try:
            playlists = []
            offset = 0
            limit = 50
            while True:
                resp = self.sp.current_user_playlists(limit=limit, offset=offset)
                items = resp.get('items', [])
                for p in items:
                    playlists.append({
                        'name': p.get('name'),
                        'uri': p.get('uri'),
                        'icon': (p.get('images') or [{}])[0].get('url')
                    })
                if len(items) < limit:
                    break
                offset += limit
            self._user_playlists = playlists
        except Exception as e:
            print(f"[WARN] Failed to fetch user playlists: {e}")
            self._user_playlists = []
        finally:
            # reset index if out of range
            if not self._user_playlists:
                self._user_playlist_index = 0
            else:
                self._user_playlist_index %= len(self._user_playlists)

    def select_next_playlist(self):
        """Cycle to the next playlist in the user's library and show toast."""
        self._ensure_user_playlists()
        if not self._user_playlists:
            return
        self._user_playlist_index = (self._user_playlist_index + 1) % len(self._user_playlists)
        pl = self._user_playlists[self._user_playlist_index]
        self.screen.show_toast(PlaylistToastTask(self.screen, pl['name']))

    def select_prev_playlist(self):
        """Cycle to the previous playlist in the user's library and show toast."""
        self._ensure_user_playlists()
        if not self._user_playlists:
            return
        self._user_playlist_index = (self._user_playlist_index - 1) % len(self._user_playlists)
        pl = self._user_playlists[self._user_playlist_index]
        self.screen.show_toast(PlaylistToastTask(self.screen, pl['name']))

    def confirm_selected_playlist(self):
        """Start playback of the currently selected playlist from the user's library."""
        self._ensure_user_playlists()
        if not self._user_playlists:
            return
        pl = self._user_playlists[self._user_playlist_index]
        try:
            self.sp.start_playback(context_uri=pl['uri'])
            self.screen.show_toast(
                PlaylistToastTask(self.screen, pl['name'], prefix="Now Playing playlist")
            )
        except Exception as e:
            print(f"[ERROR] Failed to play selected playlist {pl['uri']}: {e}")

    # --- Dynamic playlist hotkey management ---
    def register_playlist_hotkey(self, key, playlist_uri):
        """Register a playlist URI to a hotkey button."""
        self._playlist_hotkeys[key] = playlist_uri

    def link_playlist_hotkey(self, key):
        """Link the current playback context (playlist) to the given hotkey."""
        info = self.now_playing_info()
        if not info:
            return
        playback = self.sp.current_playback()
        playlist_uri = playback.get("context", {}).get("uri") if playback else None
        if not playlist_uri:
            return

        self._playlist_hotkeys[key] = playlist_uri
        icon_url = self.get_playlist_icon_url(playlist_uri)
        if self.renderer:
            try:
                self.renderer.update_button(
                    key, image=icon_url or "./assets/playlist.png"
                )
            except Exception as e:
                print(f"[WARN] Failed to update playlist hotkey icon for button {key}: {e}")

        # Persist updated playlist URI in config for next sessions
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            btn = config.get("buttons", {}).get(str(key))
            if btn:
                btn["args"] = [playlist_uri]
                with open(self.config_path, "w") as f:
                    json.dump(config, f, indent=2)
            else:
                print(f"[WARN] Cannot persist playlist hotkey: button {key} not found in config")
        except Exception as e:
            print(f"[ERROR] Failed to update playlist hotkey in config: {e}")

        # Confirmation toast for linked playlist
        try:
            self.screen.show_toast(
                PlaylistToastTask(
                    self.screen,
                    self._fetch_playlist_name(playlist_uri),
                    prefix="Linked playlist",
                )
            )
        except Exception as e:
            print(f"[WARN] Failed to show link confirmation toast: {e}")

    def playlist_hotkey(self, key):
        """Handle press of a playlist hotkey: play or add track depending on mode."""
        playlist_uri = self._playlist_hotkeys.get(key)
        if not playlist_uri:
            return
        if self._playlist_add_mode:
            info = self.now_playing_info()
            if not info:
                return
            try:
                self.sp.playlist_add_items(self._id_from_uri(playlist_uri), [info["track_id"]])
                self.screen.show_toast(
                    PlaylistAddToastTask(
                        self.screen,
                        info["track"],
                        self._fetch_playlist_name(playlist_uri),
                    )
                )
            except Exception as e:
                print(f"[ERROR] Failed to add track to playlist: {e}")
        else:
            try:
                self.sp.start_playback(context_uri=playlist_uri)
                self.screen.show_toast(
                    PlaylistToastTask(
                        self.screen,
                        self._fetch_playlist_name(playlist_uri),
                        prefix="Now Playing playlist",
                    )
                )
            except Exception as e:
                print(f"[ERROR] Failed to play playlist {playlist_uri}: {e}")

    def enter_playlist_add_mode(self, button_key, add_icon, remove_icon, mode_icon, timeout=None):
        """Enable playlist-add mode on like button long-press."""
        if self._playlist_add_mode:
            return
        self._playlist_add_mode = True
        self._playlist_add_start_time = time.time()
        if timeout is not None:
            self._playlist_add_timeout = timeout
        self._like_button_key = button_key
        self._like_button_add_icon = add_icon
        self._like_button_remove_icon = remove_icon
        self._like_button_mode_icon = mode_icon
        if self.renderer:
            try:
                self.renderer.update_button(button_key, image=mode_icon)
            except Exception as e:
                print(f"[WARN] Failed to render playlist-add mode icon for button {button_key}: {e}")

    def _exit_playlist_add_mode(self):
        """Disable playlist-add mode and restore like button icon."""
        if not self._playlist_add_mode:
            return
        self._playlist_add_mode = False
        key = self._like_button_key
        if key is not None and self.renderer:
            try:
                liked = self.is_current_track_liked()
                icon = self._like_button_remove_icon if liked else self._like_button_add_icon
                self.renderer.update_button(key, image=icon)
            except Exception as e:
                print(f"[WARN] Failed to restore like button icon for button {key}: {e}")
        # reset mode state
        self._like_button_key = None
        self._like_button_add_icon = None
        self._like_button_remove_icon = None
        self._like_button_mode_icon = None

