"""
volume_toast_task.py - Task for displaying a temporary volume change toast.

Creates and renders a volume level bar that lingers briefly before expiring.
"""
import time

class VolumeToastTask:
    """Temporary toast for showing the current volume level.
    Lingers for `linger_duration` seconds before expiring."""
    def __init__(self, screen, start_volume, target_volume,
                 animation_duration=0.0, linger_duration=1.0):
        self.screen = screen
        self.target_volume = target_volume
        self.linger_duration = linger_duration
        self.start_time = time.time()

    def expired(self, now):
        return now - self.start_time > self.linger_duration

    def render(self, now):
        return self.screen.renderer.render_volume_toast_image(self.target_volume)
