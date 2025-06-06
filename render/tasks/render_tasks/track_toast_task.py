import time

class TrackToastTask:
    """Toast for showing the currently selected track (track name and artist)."""
    def __init__(self, screen, track_name, artist_name, linger_duration=1.5):
        self.screen = screen
        self.track_name = track_name
        self.artist_name = artist_name
        self.start_time = time.time()
        self.linger_duration = linger_duration

    def expired(self, now):
        return now - self.start_time > self.linger_duration

    def render(self, now):
        width = self.screen.renderer.deck.TOUCHSCREEN_PIXEL_WIDTH
        height = self.screen.renderer.deck.TOUCHSCREEN_PIXEL_HEIGHT
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (width, height), 'black')
        draw = ImageDraw.Draw(img)
        font = self.screen.renderer.font

        text = f"{self.track_name} - {self.artist_name}"
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