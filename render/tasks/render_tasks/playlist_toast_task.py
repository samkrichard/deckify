"""
playlist_toast_task.py - Task for displaying playlist related toasts.

Includes tasks for showing playlist names, add-to-playlist confirmation, and icons.
"""
import os
import time
from PIL import Image, ImageDraw, ImageOps

class PlaylistToastTask:
    """Toast for showing a playlist name with icon. If prefix is provided, it is shown before the name."""
    def __init__(self, screen, playlist_name, prefix=None, linger_duration=1.5):
        self.screen = screen
        self.playlist_name = playlist_name
        self.prefix = prefix
        self.linger_duration = linger_duration
        self.start_time = time.time()

    def expired(self, now):
        return now - self.start_time > self.linger_duration

    def render(self, now):
        width = self.screen.renderer.deck.TOUCHSCREEN_PIXEL_WIDTH
        height = self.screen.renderer.deck.TOUCHSCREEN_PIXEL_HEIGHT
        img = Image.new('RGB', (width, height), 'black')
        try:
            module_dir = os.path.dirname(__file__)
            icon_path = os.path.normpath(os.path.join(
                module_dir, os.pardir, os.pardir, os.pardir,
                'assets', 'playlist.png'
            ))
            icon = Image.open(icon_path).convert('RGBA')
            icon = ImageOps.fit(icon, (100, 100))
            img.paste(icon, (0, 0), icon)
        except Exception as e:
            print(f"[WARN] Failed to draw playlist icon: {e}")
        draw = ImageDraw.Draw(img)
        font = self.screen.renderer.font

        icon_w = 100
        pad = 10
        start_x = icon_w + pad
        max_text_w = width - start_x - pad

        text = f"{self.playlist_name}"
        if self.prefix:
            text = f"{self.prefix}: {text}"
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        if text_w > max_text_w:
            ellipsis = '...'
            while text and text_w > max_text_w:
                text = text[:-1]
                bbox = font.getbbox(text + ellipsis)
                text_w = bbox[2] - bbox[0]
            text = text + ellipsis
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = start_x + max((max_text_w - text_w) // 2, 0)
        y = max((height - text_h) // 2, 0)
        draw.text((x, y - bbox[1]), text, font=font, fill='white')
        return img

class PlaylistAddToastTask:
    """Toast for confirming a track has been added to a playlist."""
    def __init__(self, screen, track_name, playlist_name, linger_duration=1.5):
        self.screen = screen
        self.track_name = track_name
        self.playlist_name = playlist_name
        self.linger_duration = linger_duration
        self.start_time = time.time()

    def expired(self, now):
        return now - self.start_time > self.linger_duration

    def render(self, now):
        width = self.screen.renderer.deck.TOUCHSCREEN_PIXEL_WIDTH
        height = self.screen.renderer.deck.TOUCHSCREEN_PIXEL_HEIGHT
        from PIL import Image, ImageDraw

        img = Image.new('RGB', (width, height), 'black')
        try:
            module_dir = os.path.dirname(__file__)
            icon_path = os.path.normpath(os.path.join(
                module_dir, os.pardir, os.pardir, os.pardir,
                'assets', 'playlist_add.png'
            ))
            icon = Image.open(icon_path).convert('RGBA')
            icon = ImageOps.fit(icon, (100, 100))
            img.paste(icon, (0, 0), icon)
        except Exception as e:
            print(f"[WARN] Failed to draw playlist add icon: {e}")
        draw = ImageDraw.Draw(img)
        font = self.screen.renderer.font

        icon_w = 100
        pad = 10
        start_x = icon_w + pad
        max_text_w = width - start_x - pad

        text = f"Added {self.track_name} to {self.playlist_name}"
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        if text_w > max_text_w:
            ellipsis = "..."
            while text and text_w > max_text_w:
                text = text[:-1]
                bbox = font.getbbox(text + ellipsis)
                text_w = bbox[2] - bbox[0]
            text = text + ellipsis
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = start_x + max((max_text_w - text_w) // 2, 0)
        y = max((height - text_h) // 2, 0)
        draw.text((x, y - bbox[1]), text, font=font, fill='white')
        return img
