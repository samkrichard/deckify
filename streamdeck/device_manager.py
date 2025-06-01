from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeckPlus import DialEventType
from streamdeck.action_map import build_button_action_map, build_dial_action_map
from render.display import Renderer
import threading
import time
import signal

class StreamDeckDeviceManager:
    def __init__(self, controller, config_path):
        self.controller = controller
        self.config_path = config_path
        self.deck = None
        self.action_map = {}
        self.renderer = None
        self.running = True

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)


    def initialize(self):
        devices = DeviceManager().enumerate()
        if not devices:
            raise RuntimeError("No Stream Decks found")

        self.deck = devices[0]
        self.deck.open()
        self.deck.reset()

        self.deck.set_brightness(100)

        print(f"Opened Stream Deck: {self.deck.id()} ({self.deck.key_count()} keys)")

        self.renderer = Renderer(self.deck)
        self.action_map = build_button_action_map(
            self.config_path,
            self.controller,
            self.renderer
        )

        self.renderer = Renderer(self.deck)
        if hasattr(self.controller, '_renderer'):
            self.controller._renderer = self.renderer


        self.deck.set_key_callback(self._button_callback)

        self.dial_map = build_dial_action_map(self.config_path, self.controller)
        self.deck.set_dial_callback(self._dial_callback)

        # Start a background thread to keep the app alive
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

        t = threading.Thread(target=self._screen_update_loop, daemon=True)
        t.start()


    def _run_loop(self):
        while self.running:
            time.sleep(1)

    def _handle_exit(self, *args):
        print("\n[SHUTDOWN] Cleaning up Stream Deck")
        self.running = False
        if self.deck:
            try:
                self.deck.reset()
                self.deck.close()
            except Exception as e:
                print(f"[WARN] Failed to reset/close Stream Deck cleanly: {e}")
        exit(0)

    def _button_callback(self, deck, key, state):
        if state:  # Only handle press, not release
            print(f"Button {key} pressed")
            action = self.action_map.get(str(key))
            if action:
                try:
                    action()
                except Exception as e:
                    print(f"[ERROR] Failed to execute action for button {key}: {e}")

    def _dial_callback(self, deck, dial, event, value):
        try:
            if event == DialEventType.TURN:
                direction = "clockwise" if value > 0 else "counterclockwise"
                action_key = f"dial_{dial}_{direction}"
                action = self.dial_map.get(action_key)

                print(f"[DIAL] Turn: {action_key}")
                if action:
                    action()

            elif event == DialEventType.PUSH:
                if value:  # Pressed
                    action_key = f"dial_{dial}_push"
                    print(f"[DIAL] Push: {action_key}")
                    action = self.dial_map.get(action_key)
                    if action:
                        action()
                else:
                    print(f"[DIAL] Release: dial_{dial}_release")
                    # Optional: handle release actions if needed
                    # action = self.dial_map.get(f"dial_{dial}_release")
                    # if action:
                    #     action()

        except Exception as e:
            print(f"[ERROR] Exception in dial callback (dial {dial}, event {event}, value {value}): {e}")

    def _screen_update_loop(self):
        while self.running:
            time.sleep(0.2)
            if hasattr(self.controller, "render_touchscreen"):
                self.controller.render_touchscreen()



