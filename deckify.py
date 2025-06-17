#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from controllers.app_controller import AppController

def main():
    # Load env vars (for Spotify credentials etc.)
    load_dotenv()

    # Path to your profile config (buttons, dials)
    config_path = os.path.join("config", "profiles", "spotify_mode.json")

    # Initialize and run the app
    app = AppController(config_path)
    app.run()

if __name__ == "__main__":
    main()

