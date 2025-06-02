import time

class VolumeToastTask:
    """Temporary toast for showing volume changes."""
    def __init__(self, screen, volume, duration=1.0):
        self.screen = screen
        self.volume = volume
        self.start_time = time.time()
        self.duration = duration

    def expired(self, now):
        return now - self.start_time > self.duration

    def render(self, now):
        return self.screen.renderer.render_volume_toast_image(self.volume)