# Deckify

**Deckify** is a modular, open-source control and automation framework for Elgato StreamDeck devices, written in Python and compatible with Windows, macOS, and Linux. It features powerful profile support and flexible integrations, starting with Spotify.

## Features

- Media control profile (Spotify):
  - Play/pause, next/previous track
  - Volume control via dial
  - Playlist browsing and selection via dial
  - Track browsing within playlists via dial
  - Liked Songs treated as a playlist
  - Track like/unlike with a single button press
  - Playlist hotkeys:
    - Tap to play the associated playlist
    - Long press to rebind the button to the currently playing playlist
  - Add-to-playlist mode:
    - Long press the like button to enter add mode
    - While in add mode, tap a playlist hotkey to add the current track to that playlist
    - Mode automatically exits after a short timeout
- Real-time Now Playing display with album art and metadata
- Dynamic button icons and toast notifications
- Configuration via JSON profile files
- Designed for easy expansion to additional profiles (system controls, etc.)

## Installation

```bash
git clone https://github.com/samkrichard/deckify.git
cd deckify
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the root directory:

```env
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

## Starting the App

With your virtual environment activated, you can start Deckify in either of these ways:

```bash
# Option 1 (standard Python):
python deckify.py

# Option 2 (if you've added a shebang and made the file executable):
./deckify.py
```

## Spotify API Setup

To use the Spotify profile, create a Spotify Developer App:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in and click "Create an App"
3. Add this Redirect URI:
   ```
   http://localhost:8888/callback
   ```
4. Copy your **Client ID** and **Client Secret** into your `.env` file

A Spotify Premium account is required for Web API playback.

## Requirements

- Python 3.8+
- Elgato StreamDeck or StreamDeck+ device (USB)
- Spotify Premium account (for Spotify integration)
- Dependencies (see `requirements.txt`):
  - `spotipy`
  - `pillow`
  - `streamdeck`
  - `python-dotenv`

## Linux USB Access

To use the StreamDeck without root on Linux, add a udev rule:

```bash
sudo nano /etc/udev/rules.d/99-streamdeck.rules
```

Paste:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="0fd9", MODE="0666", GROUP="plugdev"
```

Then run:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

Log out and back in to apply the group change.

## Planned Features

- Profile switching via dial or touchscreen
- System control profile (volume, brightness, app launching)
- Plugin-style modular architecture

## Credits and Attribution

- Icons provided by [Icons8](https://icons8.com) under their free license with attribution.
- This project uses:
  - [Spotipy](https://github.com/plamere/spotipy)
  - [python-elgato-streamdeck](https://github.com/abcminiuser/python-elgato-streamdeck)
  - [Pillow](https://python-pillow.org)

## License

MIT License — see `LICENSE` for details.
