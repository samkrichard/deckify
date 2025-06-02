from PIL import Image, ImageDraw, ImageFont, ImageOps
import time

class NowPlayingTask:
    def __init__(self, info: dict, album_art):
        self.info = info
        self.album_art = album_art
        self.start_time = time.time()
        self.scroll_offset = 0
        self.last_scroll_time = time.time()

    def expired(self, now):
        # Never expires — it's a persistent "view"
        return False

    def render(self, now):
        width, height = 800, 100
        img = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(img)

        # --- Album Art ---
        if self.album_art:
            try:
                art = ImageOps.fit(self.album_art, (100, 100))
                img.paste(art, (0, 0))
            except Exception as e:
                print(f"[WARN] Failed to draw album art: {e}")

        # --- Metadata ---
        title = self.info.get("track", "Unknown Track")
        artist = self.info.get("artist", "Unknown Artist")
        # Dynamic progress: advance elapsed time if playing, else static
        orig_progress = self.info.get("progress", 0)
        duration = self.info.get("duration", 1)
        if self.info.get("is_playing", False):
            elapsed = orig_progress + int((now - self.start_time) * 1000)
        else:
            elapsed = orig_progress
        progress = min(elapsed, duration)
        pct = progress / duration if duration > 0 else 0.0

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            small_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # --- Title Text (Scrolling) ---
        spacing = 28
        text_x = 110
        text_y = 20
        text_width_area = width - text_x - 20

        title_bbox = font.getbbox(title)
        title_width = title_bbox[2] - title_bbox[0]

        title_band = Image.new("RGB", (text_width_area, spacing), "black")
        title_draw = ImageDraw.Draw(title_band)

        if title_width > text_width_area:
            loop_width = title_width + 60
            delta = now - self.last_scroll_time
            self.scroll_offset += int(delta * 40)  # 40px/s scroll speed
            scroll_px = self.scroll_offset % loop_width
            x1 = -scroll_px
            x2 = x1 + loop_width

            title_draw.text((x1, 0), title, font=font, fill="white")
            title_draw.text((x2, 0), title, font=font, fill="white")
            self.last_scroll_time = now
        else:
            title_draw.text((0, 0), title, font=font, fill="white")

        img.paste(title_band, (text_x, text_y))

        # --- Artist Text ---
        draw.text((text_x, text_y + spacing), artist, font=font, fill="gray")

        # --- Progress Bar ---
        def ms_to_minsec(ms):
            seconds = ms // 1000
            return f"{seconds // 60}:{seconds % 60:02}"

        elapsed_str = ms_to_minsec(progress)
        total_str = ms_to_minsec(duration)

        elapsed_bbox = small_font.getbbox(elapsed_str)
        total_bbox = small_font.getbbox(total_str)

        elapsed_w = elapsed_bbox[2] - elapsed_bbox[0]
        total_w = total_bbox[2] - total_bbox[0]

        padding = 10
        bar_x = 100 + padding + elapsed_w + padding
        bar_y = height - 18
        bar_height = 6
        bar_width = width - bar_x - total_w - 2 * padding

        timestamp_offset_y = 5

        draw.text((100 + padding, bar_y - timestamp_offset_y), elapsed_str, font=small_font, fill="white")
        draw.text((bar_x + bar_width + padding, bar_y - timestamp_offset_y), total_str, font=small_font, fill="white")

        # Bar background
        radius = bar_height // 2
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], radius=radius, fill="gray")

        # Bar fill
        fill_width = int(bar_width * pct)
        if fill_width > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], radius=radius, fill="white")

        return img
