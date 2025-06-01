import os
import signal
from dotenv import load_dotenv
from streamdeck.device_manager import StreamDeckDeviceManager
from actions.spotify_controller import SpotifyController


def main():
    load_dotenv()

    controller = SpotifyController()
    config_path = os.path.join("config", "profiles", "spotify_mode.json")

    deck_manager = StreamDeckDeviceManager(controller, config_path)
    deck_manager.initialize()

    print("[OK] Stream Deck Spotify profile loaded. Press Ctrl+C to exit.")

    # Wait here until a signal is caught; device manager handles shutdown
    signal.pause()


if __name__ == "__main__":
    main()
