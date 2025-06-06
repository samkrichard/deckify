import time
import asyncio
from render.display import Renderer  # Your existing PIL-based renderer
from collections import deque

class ScreenManager:
    def __init__(self, deck):
        self.renderer = Renderer(deck)
        self.current_task = None
        self.toast_task = None
        self._toast_queue = deque()
        self.last_render_time = 0

    def set_view(self, task):
        """Set the main screen content (e.g., now playing)."""
        self.current_task = task

    def show_toast(self, task):
        """Temporarily display one or more toast messages (overrides current view). If given an iterable of tasks, show them sequentially."""
        if isinstance(task, (list, tuple, deque)):
            self._toast_queue = deque(task)
            self.toast_task = self._toast_queue.popleft()
        else:
            self._toast_queue.clear()
            self.toast_task = task

    def update(self, now):
        """Synchronous update (legacy) — use update_async for non-blocking rendering."""
        img = None

        # Clean up expired toast
        if self.toast_task and self.toast_task.expired(now):
            if self._toast_queue:
                self.toast_task = self._toast_queue.popleft()
            else:
                self.toast_task = None

        if self.toast_task:
            img = self.toast_task.render(now)
        elif self.current_task:
            img = self.current_task.render(now)

        if img:
            self.renderer.set_touchscreen_image(img)
            self.last_render_time = now

    async def update_async(self, now):
        """Asynchronous update — schedule rendering and deck I/O off the main loop."""
        # Clean up expired toast
        if self.toast_task and self.toast_task.expired(now):
            if self._toast_queue:
                self.toast_task = self._toast_queue.popleft()
            else:
                self.toast_task = None

        # Determine which task to render
        task = self.toast_task or self.current_task
        if not task:
            return

        # If no render in flight, schedule a new one
        render_task = getattr(self, '_render_task', None)
        if render_task is None or render_task.done():
            self._render_task = asyncio.create_task(
                self._render_and_push(task, now)
            )

    async def _render_and_push(self, task, now):
        # Render frame off the main thread
        img = await asyncio.to_thread(task.render, now)

        # Push to touchscreen off the main thread
        await asyncio.to_thread(self.renderer.set_touchscreen_image, img)
        self.last_render_time = now
