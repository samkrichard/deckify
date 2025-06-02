import time
from streamdeck.device_manager import StreamDeckDeviceManager
from controllers.spotify_controller import SpotifyController
from render.screen_manager import ScreenManager  # You'll build this


class AppController:
    def __init__(self, config_path):
        self.config_path = config_path
        self.deck = None

        # Init hardware manager first
        self.device_manager = StreamDeckDeviceManager()

        # Init the screen manager with the device reference
        self.screen = ScreenManager(self.device_manager.deck)

        # Init controller(s)
        self.spotify = SpotifyController(self.screen)

        # Register controller actions to buttons/dials
        self.device_manager.initialize(self.config_path, self.spotify, self.screen.renderer)

        # Future controllers could go here:
        # self.chat = ChatController(self.screen)
        # self.volume = VolumeController(...)

        self._tick_rate = 1 / 5  # 5 FPS render loop (200ms per frame)

    def run(self):
        print("[APP] Main loop started.")
        try:
            next_tick = time.time()
            while True:
                now = time.time()

                # Handle device input (polling moved off the UI thread)
                self.device_manager.update(now)

                # Run render pipeline
                self.screen.update(now)

                # Frame-lock to a steady tick rate
                next_tick += self._tick_rate
                sleep_for = next_tick - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        print("[APP] Shutting down.")
        # Stop background polling thread
        self.spotify.shutdown()
        self.device_manager.shutdown()
