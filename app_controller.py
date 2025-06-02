import time
from device_manager import StreamDeckDeviceManager
from spotify_controller import SpotifyController
from screen_manager import ScreenManager  # You'll build this


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
        self.device_manager.initialize(self.config_path, self.spotify, self.screen)

        # Future controllers could go here:
        # self.chat = ChatController(self.screen)
        # self.volume = VolumeController(...)

        self._tick_rate = 1 / 60  # 60 FPS render loop

    def run(self):
        print("[APP] Main loop started.")
        try:
            while True:
                now = time.time()

                # Update logical systems
                self.spotify.update(now)
                # self.chat.update(now)

                # Handle device input (you could move polling logic here)
                self.device_manager.update(now)

                # Run render pipeline
                self.screen.update(now)

                time.sleep(self._tick_rate)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        print("[APP] Shutting down.")
        self.device_manager.shutdown()
