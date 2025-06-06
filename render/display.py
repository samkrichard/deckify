import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import threading

class Renderer:
    def __init__(self, deck, button_size=(120, 120)):
        self.deck = deck
        self.button_size = button_size
        self._deck_lock = threading.Lock()
        self._last_key_images = {}
        try:
            self.font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        except Exception:
            self.font = ImageFont.load_default()

    def render_button(self, text=None, image=None, fg="white", bg="black"):
        """Creates a PIL image with either an icon or label (not both)."""
        base = Image.new("RGB", self.button_size, color=bg)

        if image:
            try:
                if image.startswith("http://") or image.startswith("https://"):
                    response = requests.get(image)
                    response.raise_for_status()
                    icon = Image.open(BytesIO(response.content)).convert("RGB")
                else:
                    icon = Image.open(image).convert("RGB")
                icon = icon.resize(self.button_size)
                base.paste(icon)
                return base  # Early return — no text if icon is used
            except Exception as e:
                print(f"[WARN] Failed to load image '{image}': {e}")

        # If no image, render text
        if text:
            draw = ImageDraw.Draw(base)
            try:
                bbox = self.font.getbbox(text)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (self.button_size[0] - w) // 2
                y = (self.button_size[1] - h) // 2 - bbox[1]
                draw.text((x, y), text, font=self.font, fill=fg)
            except Exception as e:
                print(f"[WARN] Failed to render text: {e}")

        return base
    
    def set_touchscreen_image(self, image: Image.Image):
        try:
            buf = BytesIO()
            image.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            # serialize all deck updates to avoid races/flicker
            with self._deck_lock:
                self.deck.set_touchscreen_image(img_bytes, 0, 0, 800, 100)
        except Exception as e:
            print(f"[WARN] Failed to push image to touchscreen: {e}")


    def update_button(self, key: int, text=None, image=None):
        """Renders and pushes JPEG image to the Stream Deck button."""
        try:
            img = self.render_button(text, image)
            buffer = BytesIO()
            img = img.resize(self.button_size)
            img.save(buffer, format="JPEG")
            jpeg_bytes = buffer.getvalue()

            # Avoid re-sending identical key images (reduces flicker on unchanged buttons)
            prev = self._last_key_images.get(key)
            if prev != jpeg_bytes:
                self._last_key_images[key] = jpeg_bytes
                with self._deck_lock:
                    self.deck.set_key_image(key, jpeg_bytes)
        except Exception as e:
            print(f"[WARN] Failed to render button {key}: {e}")

    def render_volume_toast_image(self, volume: int, width=800, height=100):
        margin = 20
        stroke_width = 2
        gap = 2
        outer_height = 40

        img = Image.new('RGB', (width, height), 'black')
        draw = ImageDraw.Draw(img)

        # Outer outline rectangle
        center_y = height // 2
        outer_rect = [
            margin,
            center_y - outer_height // 2,
            width - margin,
            center_y + outer_height // 2,
        ]
        draw.rounded_rectangle(outer_rect, radius=outer_height // 2, outline='white', width=stroke_width)

        # Inner fill bar with slight gap from outline
        inner_top = outer_rect[1] + stroke_width + gap
        inner_bottom = outer_rect[3] - stroke_width - gap
        max_fill_width = (outer_rect[2] - outer_rect[0]) - 2 * (stroke_width + gap)
        fill_width = int((volume / 100) * max_fill_width)
        inner_left = outer_rect[0] + stroke_width + gap
        inner_right = inner_left + fill_width
        inner_rect = [inner_left, inner_top, inner_right, inner_bottom]
        inner_radius = (inner_bottom - inner_top) // 2
        draw.rounded_rectangle(inner_rect, radius=inner_radius, fill='white')

        # Volume text
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()

        text = f"{volume}%"
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (width - text_width) // 2
        text_y = height // 2 - 40 - bbox[1]  # Adjust for font baseline

        draw.text((text_x, text_y), text, font=font, fill='white')

        return img
    
    def render_now_playing_screen(self, info: dict, width=800, height=100, scroll_offset=0, art_image=None):
        img = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(img)

        art_width = 100
        art_height = 100
        padding = 10


        # Album Art (uses preloaded cached image)
        if art_image:
            try:
                art = ImageOps.fit(art_image, (art_width, art_height))  # maintain aspect ratio
                img.paste(art, (0, 0))
            except Exception as e:
                print(f"[WARN] Failed to draw cached album art: {e}")

        # Track and artist text
        title = info.get("track", "Unknown Track")
        artist = info.get("artist", "Unknown Artist")

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()

        spacing = 28
        text_x = 110
        text_y = 20
        text_width_area = width - text_x - 20

        # Scrolling Title Text
        title_bbox = font.getbbox(title)
        title_width = title_bbox[2] - title_bbox[0]

        title_band = Image.new("RGB", (text_width_area, spacing), "black")
        title_draw = ImageDraw.Draw(title_band)

        if title_width > text_width_area:
            loop_width = title_width + 60  # space between loops
            scroll_px = scroll_offset % loop_width
            x1 = -scroll_px
            x2 = x1 + loop_width

            title_draw.text((x1, 0), title, font=font, fill="white")
            title_draw.text((x2, 0), title, font=font, fill="white")
        else:
            title_draw.text((0, 0), title, font=font, fill="white")

        img.paste(title_band, (text_x, text_y))

        # Static artist line
        draw.text((text_x, text_y + spacing), artist, font=font, fill="gray")

    
        # --- Progress Bar to the right of Album Art ---
        def ms_to_minsec(ms):
            seconds = ms // 1000
            return f"{seconds // 60}:{seconds % 60:02}"

        progress = info.get("progress", 0)
        duration = info.get("duration", 1)
        pct = min(progress / duration, 1.0)

        elapsed_str = ms_to_minsec(progress)
        total_str = ms_to_minsec(duration)

        font_size = 14
        try:
            time_font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            time_font = ImageFont.load_default()

        # Get width of timestamp text
        elapsed_bbox = time_font.getbbox(elapsed_str)
        total_bbox = time_font.getbbox(total_str)

        elapsed_w = elapsed_bbox[2] - elapsed_bbox[0]
        total_w = total_bbox[2] - total_bbox[0]

        # Bar layout
        bar_x = art_width + padding + elapsed_w + padding
        bar_y = height - 18  # aligned near bottom of screen
        bar_height = 6
        bar_width = width - bar_x - total_w - 2 * padding

        timestamp_offset_y = 5

        # Draw timestamps
        draw.text((art_width + padding, bar_y - timestamp_offset_y), elapsed_str, font=time_font, fill="white")
        draw.text((bar_x + bar_width + padding, bar_y - timestamp_offset_y), total_str, font=time_font, fill="white")

        # Draw progress bar
        bar_bg_box = [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height]
        draw.rounded_rectangle(bar_bg_box, radius=2, fill="gray")

        fill_width = int(bar_width * pct)
        if fill_width > 0:
            bar_fg_box = [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height]
            draw.rounded_rectangle(bar_fg_box, radius=2, fill="white")



        return img
