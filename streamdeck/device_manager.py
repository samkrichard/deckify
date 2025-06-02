from StreamDeck.DeviceManager import DeviceManager as HardwareDeviceManager
from StreamDeck.Devices.StreamDeckPlus import DialEventType
from actions.action_map import build_button_action_map, build_dial_action_map

class StreamDeckDeviceManager:
    def __init__(self):
        self.deck = None
        self.button_action_map = {}
        self.dial_action_map = {}

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

        self.button_action_map = build_button_action_map(
            config_path, controller, renderer
        )
        self.dial_action_map = build_dial_action_map(
            config_path, controller
        )

        self.deck.set_key_callback(self._button_callback)
        self.deck.set_dial_callback(self._dial_callback)

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

