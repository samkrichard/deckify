from StreamDeck.DeviceManager import DeviceManager as HardwareDeviceManager
from StreamDeck.Devices.StreamDeckPlus import DialEventType
from actions.action_map import build_button_action_map, build_dial_action_map
from StreamDeck.Devices.StreamDeck import TouchscreenEventType
import time
from render.tasks.render_tasks.now_playing_task import NowPlayingTask

class StreamDeckDeviceManager:
    def __init__(self):
        self.deck = None
        self.button_action_map = {}
        self.dial_action_map = {}
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
        self.button_action_map = build_button_action_map(
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

    def _button_callback(self, deck, key, state):
        if state:  # Only on press
            action = self.button_action_map.get(key)
            if action:
                try:
                    action()
                except Exception as e:
                    print(f"[ERROR] Button {key} action failed: {e}")
            self.controller.update(time.time(), force=True)

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

        print(f'Touch at x: {x}, y: {y}')

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
        self.controller.update(time.time(), force=True)

