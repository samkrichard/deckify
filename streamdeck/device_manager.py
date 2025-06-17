"""
device_manager.py - Stream Deck hardware manager for Deckify.

Handles device initialization, input callbacks, and dispatching
button and dial events to controller actions.
"""
from StreamDeck.DeviceManager import DeviceManager as HardwareDeviceManager
from StreamDeck.Devices.StreamDeckPlus import DialEventType
from actions.action_map import build_button_action_map, build_dial_action_map
from StreamDeck.Devices.StreamDeck import TouchscreenEventType
import time
import threading
from render.tasks.render_tasks.now_playing_task import NowPlayingTask

class StreamDeckDeviceManager:
    """Manage Stream Deck hardware, including button and dial event callbacks."""
    def __init__(self):
        self.deck = None
        # short press action map: key -> callable()
        self.button_action_map = {}
        # long press action map: key -> (callable, args, timeout)
        self.button_long_action_map = {}
        self.dial_action_map = {}
        # track press timestamps for long-press detection
        self._press_times = {}
        # timers for firing long-press actions immediately on timeout
        self._long_press_timers = {}
        self.controller = None

    def initialize(self, config_path, controller, renderer):
        devices = HardwareDeviceManager().enumerate()
        if not devices:
            raise RuntimeError("No Stream Decks found")

        self.deck = devices[0]
        self.deck.open()
        self.deck.reset()
        self.deck.set_brightness(100)

        print(f"[OK] Connected to Stream Deck: {self.deck.id()} ({self.deck.key_count()} keys)")

        if renderer:
            renderer.deck = self.deck

        self.controller = controller
        self.button_action_map, self.button_long_action_map = build_button_action_map(
            config_path, controller, renderer
        )
        self.dial_action_map = build_dial_action_map(
            config_path, controller
        )

        self.deck.set_key_callback(self._button_callback)
        self.deck.set_dial_callback(self._dial_callback)
        # Handle touchscreen taps for scrubbing on now playing screen
        try:
            self.deck.set_touchscreen_callback(self._touchscreen_callback)
        except Exception:
            pass

    def update(self, now):
        # Reserved for future polling or input state checking
        pass

    def shutdown(self):
        print("[DEVICE] Shutting down Stream Deck.")
        if self.deck:
            try:
                self.deck.reset()
                self.deck.close()
            except Exception as e:
                print(f"[WARN] Failed to cleanly close Stream Deck: {e}")

    def _force_update(self):
        """Force an immediate update of controller state and touchscreen rendering."""
        now = time.time()
        # Refresh controller state; defer actual screen redraw to main render loop
        self.controller.update(now, force=True)

    def _button_callback(self, deck, key, state):
        """
        Handle short and long press events. State True=press, False=release.
        """
        # Press or release while in playlist-add mode: press adds track, release exits mode (no playback)
        if hasattr(self.controller, '_playlist_add_mode') and getattr(self.controller, '_playlist_add_mode', False) \
               and hasattr(self.controller, '_playlist_hotkeys') and key in self.controller._playlist_hotkeys:
            if state:
                try:
                    self.controller.playlist_hotkey(key)
                except Exception as e:
                    print(f"[ERROR] Playlist add {key} action failed: {e}")
            else:
                try:
                    self.controller._exit_playlist_add_mode()
                except Exception:
                    pass
            self._force_update()
            return
        # Long-press mapping takes priority
        long_entry = self.button_long_action_map.get(key)
        if long_entry:
            method_long, args_long, timeout = long_entry
            if state:
                # on press: schedule long action to fire after timeout
                self._press_times[key] = time.time()
                def _fire():
                    # only fire long action if still pressed after timeout
                    if key in self._press_times:
                        try:
                            method_long(*args_long)
                        except Exception as e:
                            print(f"[ERROR] Button {key} long action failed: {e}")
                        self._force_update()
                t = threading.Timer(timeout, _fire)
                t.daemon = True
                t.start()
                self._long_press_timers[key] = (t, timeout)
            else:
                # on release: cancel pending timer, then decide short vs long by elapsed
                press_time = self._press_times.pop(key, None)
                timer_entry = self._long_press_timers.pop(key, None)
                if timer_entry:
                    timer, _ = timer_entry
                    timer.cancel()
                # short if released before timeout, otherwise long already fired
                if press_time is not None:
                    elapsed = time.time() - press_time
                    if elapsed < timer_entry[1]:
                        # short release: dynamic playlist or fallback action
                        if hasattr(self.controller, '_playlist_hotkeys') and key in self.controller._playlist_hotkeys:
                            try:
                                self.controller.playlist_hotkey(key)
                            except Exception as e:
                                print(f"[ERROR] Playlist hotkey {key} action failed: {e}")
                        else:
                            short_action = self.button_action_map.get(key)
                            if short_action:
                                try:
                                    short_action()
                                except Exception as e:
                                    print(f"[ERROR] Button {key} short action failed: {e}")
                self._force_update()
            return

        # Short-press dynamic playlist hotkey always overrides static mapping
        if state and hasattr(self.controller, '_playlist_hotkeys') \
               and key in self.controller._playlist_hotkeys:
            try:
                self.controller.playlist_hotkey(key)
            except Exception as e:
                print(f"[ERROR] Playlist hotkey {key} action failed: {e}")
            self._force_update()
            return

        # No long action configured: fallback to short-press only
        if state:
            action = self.button_action_map.get(key)
            if action:
                try:
                    action()
                except Exception as e:
                    print(f"[ERROR] Button {key} action failed: {e}")
            self._force_update()

    def _dial_callback(self, deck, dial, event, value):
        try:
            if event == DialEventType.TURN:
                direction = "clockwise" if value > 0 else "counterclockwise"
                key = f"dial_{dial}_{direction}"
            elif event == DialEventType.PUSH:
                key = f"dial_{dial}_push" if value else f"dial_{dial}_release"
            else:
                return

            action = self.dial_action_map.get(key)
            if action:
                action()
                self._force_update()
        except Exception as e:
            print(f"[ERROR] Dial event ({key}) failed: {e}")

    def _touchscreen_callback(self, deck, event_type, value):
        # Single-tap scrubbing for now playing progress bar
        if event_type != TouchscreenEventType.SHORT:
            return
        task = self.controller.screen.current_task
        if not isinstance(task, NowPlayingTask):
            return
        x = value.get('x')
        y = value.get('y')

        if x is None or y is None:
            return
        width = deck.TOUCHSCREEN_PIXEL_WIDTH
        height = deck.TOUCHSCREEN_PIXEL_HEIGHT
        action = task.handle_touch(x, y, width, height, time.time())
        if not action:
            return
        act = action.get("action")
        try:
            if act == "toggle_shuffle":
                self.controller.toggle_shuffle()
            elif act == "toggle_repeat":
                self.controller.toggle_repeat()
            elif act == "seek":
                self.controller.seek(action.get("position", 0))
        except Exception as e:
            print(f"[ERROR] Touch action '{act}' failed: {e}")
        self._force_update()

