from PIL import Image, ImageDraw, ImageFont, ImageOps
import time

class NowPlayingTask:
    def __init__(self, info: dict, album_art):
        self.info = info
        self.album_art = album_art
        self.start_time = time.time()
        self.scroll_offset = 0
        self.last_scroll_time = time.time()
        self.artist_scroll_offset = 0
        self.last_artist_scroll_time = time.time()

    def expired(self, now):
        # Never expires — it's a persistent "view"
        return False

    def render(self, now):
        width, height = 800, 100
        img = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(img)

        self._draw_album_art(img)

        title = self.info.get("track", "Unknown Track")
        artist = self.info.get("artist", "Unknown Artist")
        progress, duration, pct = self._compute_progress(now)
        font, small_font = self._get_fonts()

        self._draw_title(img, title, font, now, width)
        self._draw_artist(img, artist, font, now, width)
        self._draw_progress_bar(draw, small_font, progress, duration, pct, width, height)

        return img

    def _draw_album_art(self, img):
        if not self.album_art:
            return
        try:
            art = ImageOps.fit(self.album_art, (100, 100))
            img.paste(art, (0, 0))
        except Exception as e:
            print(f"[WARN] Failed to draw album art: {e}")

    def _compute_progress(self, now):
        orig = self.info.get("progress", 0)
        duration = self.info.get("duration", 1)
        if self.info.get("is_playing", False):
            elapsed = orig + int((now - self.start_time) * 1000)
        else:
            elapsed = orig
        progress = min(elapsed, duration)
        pct = progress / duration if duration > 0 else 0.0
        return progress, duration, pct

    def _get_fonts(self):
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            small = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
            small = ImageFont.load_default()
        return font, small

    def _draw_title(self, img, title, font, now, width):
        spacing = 28
        text_x, text_y = 110, 20
        area = width - text_x - 20

        bbox = font.getbbox(title)
        title_w = bbox[2] - bbox[0]

        band = Image.new("RGB", (area, spacing), "black")
        band_draw = ImageDraw.Draw(band)

        if title_w > area:
            loop_w = title_w + 60
            delta = now - self.last_scroll_time
            self.scroll_offset += int(delta * 40)
            scroll_px = self.scroll_offset % loop_w
            x1, x2 = -scroll_px, -scroll_px + loop_w
            band_draw.text((x1, 0), title, font=font, fill="white")
            band_draw.text((x2, 0), title, font=font, fill="white")
            self.last_scroll_time = now
        else:
            band_draw.text((0, 0), title, font=font, fill="white")

        img.paste(band, (text_x, text_y))

    def _draw_artist(self, img, artist, font, now, width):
        spacing = 28
        text_x, text_y = 110, 20
        area = width - text_x - 20

        bbox = font.getbbox(artist)
        artist_w = bbox[2] - bbox[0]

        band = Image.new("RGB", (area, spacing), "black")
        band_draw = ImageDraw.Draw(band)

        if artist_w > area:
            loop_w = artist_w + 60
            delta = now - self.last_artist_scroll_time
            self.artist_scroll_offset += int(delta * 40)
            scroll_px = self.artist_scroll_offset % loop_w
            x1, x2 = -scroll_px, -scroll_px + loop_w
            band_draw.text((x1, 0), artist, font=font, fill="gray")
            band_draw.text((x2, 0), artist, font=font, fill="gray")
            self.last_artist_scroll_time = now
        else:
            band_draw.text((0, 0), artist, font=font, fill="gray")

        img.paste(band, (text_x, text_y + spacing))

    def _ms_to_minsec(self, ms):
        secs = ms // 1000
        return f"{secs // 60}:{secs % 60:02}"

    def _draw_progress_bar(self, draw, small_font, progress, duration, pct, width, height):
        elapsed_str = self._ms_to_minsec(progress)
        total_str = self._ms_to_minsec(duration)

        eb = small_font.getbbox(elapsed_str)
        tb = small_font.getbbox(total_str)
        ew, tw = eb[2] - eb[0], tb[2] - tb[0]

        pad = 10
        bar_x = 100 + pad + ew + pad
        bar_y = height - 18
        bar_h = 6
        bar_w = width - bar_x - tw - 2 * pad
        toff = 5

        draw.text((100 + pad, bar_y - toff), elapsed_str, font=small_font, fill="white")
        draw.text((bar_x + bar_w + pad, bar_y - toff), total_str, font=small_font, fill="white")

        radius = bar_h // 2
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=radius, fill="gray")
        fill_w = int(bar_w * pct)
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=radius, fill="white")
