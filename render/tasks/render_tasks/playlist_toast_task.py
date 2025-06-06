import time

class PlaylistToastTask:
    """Toast for showing the current playlist name."""
    def __init__(self, screen, playlist_name, linger_duration=1.5):
        self.screen = screen
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
        draw = ImageDraw.Draw(img)
        font = self.screen.renderer.font

        text = f"{self.playlist_name}"
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        max_width = width
        if text_width > max_width:
            ellipsis = "..."
            while text and text_width > max_width:
                text = text[:-1]
                bbox = font.getbbox(text + ellipsis)
                text_width = bbox[2] - bbox[0]
            text = text + ellipsis
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = max((width - text_width) // 2, 0)
        y = max((height - text_height) // 2, 0)
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
        draw = ImageDraw.Draw(img)
        font = self.screen.renderer.font

        text = f"Added {self.track_name} to {self.playlist_name}"
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        max_width = width
        if text_width > max_width:
            ellipsis = "..."
            while text and text_width > max_width:
                text = text[:-1]
                bbox = font.getbbox(text + ellipsis)
                text_width = bbox[2] - bbox[0]
            text = text + ellipsis
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = max((width - text_width) // 2, 0)
        y = max((height - text_height) // 2, 0)
        draw.text((x, y - bbox[1]), text, font=font, fill='white')
        return img