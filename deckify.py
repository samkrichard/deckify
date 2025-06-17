#!/usr/bin/env python3
"""
Entry point for Deckify application.

Loads environment variables, sets up profile configuration,
and starts the AppController.
"""
import os
from dotenv import load_dotenv
from controllers.app_controller import AppController

def main():
    """Load environment, configure the profile, and run the Deckify app."""
    load_dotenv()

    config_path = os.path.join("config", "profiles", "spotify_mode.json")
    app = AppController(config_path)
    app.run()

if __name__ == "__main__":
    main()

