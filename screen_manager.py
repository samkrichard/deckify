import time
from display import Renderer  # Your existing PIL-based renderer

class ScreenManager:
    def __init__(self, deck):
        self.renderer = Renderer(deck)
        self.current_task = None
        self.toast_task = None
        self.last_render_time = 0

    def set_view(self, task):
        """Set the main screen content (e.g., now playing)."""
        self.current_task = task

    def show_toast(self, task):
        """Temporarily display a toast message (overrides current view)."""
        self.toast_task = task

    def update(self, now):
        img = None

        # Clean up expired toast
        if self.toast_task and self.toast_task.expired(now):
            self.toast_task = None

        if self.toast_task:
            img = self.toast_task.render(now)
        elif self.current_task:
            img = self.current_task.render(now)

        if img:
            self.renderer.set_touchscreen_image(img)
            self.last_render_time = now
