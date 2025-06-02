import time

class VolumeToastTask:
    """Temporary toast for showing a smooth volume-change animation.
    Animates over `animation_duration` seconds, then lingers for `linger_duration` seconds."""
    def __init__(self, screen, start_volume, target_volume,
                 animation_duration=0.5, linger_duration=1.0):
        self.screen = screen
        self.start_volume = start_volume
        self.target_volume = target_volume
        self.animation_duration = animation_duration
        self.linger_duration = linger_duration
        self.start_time = time.time()

    def expired(self, now):
        return now - self.start_time > (self.animation_duration + self.linger_duration)

    def render(self, now):
        elapsed = now - self.start_time
        if elapsed >= self.animation_duration:
            current = self.target_volume
        else:
            frac = elapsed / self.animation_duration
            current = int(round(
                self.start_volume +
                (self.target_volume - self.start_volume) * frac
            ))
        return self.screen.renderer.render_volume_toast_image(current)