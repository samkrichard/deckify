# Deckify

**Deckify** is a modular, open-source control and automation framework for Elgato StreamDeck devices, with powerful profile support and flexible integration starting with Spotify.

## Features

- Media control profile (Spotify):
  - Play/pause, next/previous track
  - Volume control via dial
  - Playlist browsing and selection via dial
  - Track browsing within playlists via dial
  - Liked Songs treated as a playlist (full support)
  - Track like/unlike with a single button press
  - Playlist hotkeys (assigned to specific buttons):
    - Tap to play the associated playlist
    - Long press to rebind the button to the currently playing playlist
  - Add-to-playlist mode:
    - Long press the like button to enter add mode
    - While in add mode, tap a playlist hotkey to add the current track to that playlist
    - Mode automatically exits after a short timeout
- Real-time Now Playing display with album art and metadata
- Dynamic button icons and toast notifications
- Configuration driven by JSON profile files
- Designed for easy expansion to additional profiles (system controls, OBS, etc.)

Built using:
- [Spotipy](https://github.com/plamere/spotipy)
- [python-elgato-streamdeck](https://github.com/abcminiuser/python-elgato-streamdeck)
- [Pillow](https://python-pillow.org)

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/Deckify.git
cd Deckify
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

Then start the app:

```bash
python deckify.py
# or, if your entrypoint is named differently:
python streamdeckd.py
```

---

## Spotify API Setup

To use the Spotify profile, create a Spotify Developer App:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in and click "Create an App"
3. Set any name/description
4. Add this Redirect URI:
   ```
   http://localhost:8888/callback
   ```
5. Copy your **Client ID** and **Client Secret**, and add them to your `.env` file

**Note:** Spotify Web API playback requires a Spotify Premium account.

---

## Requirements

- Python 3.8+
- Elgato StreamDeck or StreamDeck+ device connected via USB
- Spotify Premium account (for Spotify integration)
- Dependencies (from `requirements.txt`):
  - `spotipy>=2.25.1`
  - `pillow>=11.2.1`
  - `streamdeck>=0.9.6`
  - `python-dotenv>=1.1.0`

---

## Linux USB Access

To use the StreamDeck without root on Linux:

1. Create a udev rule:

   ```bash
   sudo nano /etc/udev/rules.d/99-streamdeck.rules
   ```

2. Paste:

   ```
   SUBSYSTEM=="usb", ATTR{idVendor}=="0fd9", MODE="0666", GROUP="plugdev"
   ```

3. Then run:

   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   sudo usermod -aG plugdev $USER
   ```

4. Log out and back in to apply group changes.

---

## Planned Features

- Profile switching via dial or touchscreen
- System control profile (volume, brightness, app launching)
- OBS and streaming platform integrations
- Plugin-style modular architecture for new integrations

---

## Credits and Attribution

- Icons provided by [Icons8](https://icons8.com), used under their free license with attribution.
- This project uses:
  - [Spotipy](https://github.com/plamere/spotipy)
  - [python-elgato-streamdeck](https://github.com/abcminiuser/python-elgato-streamdeck)
  - [Pillow](https://python-pillow.org)

---

## License

MIT License — see `LICENSE` for details.

---

> *Deckify is not affiliated with Elgato or Spotify. This project is unrelated to any card game or TCG software.*
