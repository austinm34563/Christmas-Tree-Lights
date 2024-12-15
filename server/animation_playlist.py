
import threading
from animation_constants import *
import random

class AnimationPlaylist:
    def __init__(self, pixels, animations, color_schemes, speeds, time_delay=60):
        self.pixels = pixels
        self.pixel_count = pixels.n
        self.animations = animations
        self.color_schemes = color_schemes
        self.speeds = speeds
        self.time_delay = time_delay
        self.thread = None
        self.shuffle = False
        self._stop_event = threading.Event()
        self.current_animation = None
        self.current_color_index = None

        self.TAG = "Animation Playlist"

    def start_playlist(self, shuffle=False):
        Logger.info(self.TAG, "Starting Playlist")
        self.shuffle = shuffle
        if self.thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._playlist_loop, daemon=True)
            self.thread.start()

    def stop_playlist(self):
        Logger.info(self.TAG, "Stopping Playlist")
        self._stop_event.set()
        if self.thread is not None:
            self.thread.join()  # Wait for the thread to finish
            self.thread = None

    def _playlist_loop(self):
        while not self._stop_event.is_set():
            for animation_index, animation in enumerate(self.animations):
                if self._stop_event.is_set():
                    break

                # Stop the previous animation
                if self.current_animation:
                    self.current_animation.stop_animation()

                # Pick a random color scheme
                color_scheme_index = random.randrange(len(self.color_schemes))
                if self.current_color_index is not None and self.current_color_index == color_scheme_index:
                    color_scheme_index = (color_scheme_index + 1) % len(self.color_schemes)
                self.current_color_index = color_scheme_index
                self.current_animation = effect_classes[animation](
                    self.pixel_count,
                    self.pixels,
                    colors=self.color_schemes[color_scheme_index],
                    speed=self.speeds[animation_index],
                    fps_render=30
                )

                # Play the animation
                self.current_animation.run_animation()
                start_time = time.monotonic()

                while time.monotonic() - start_time < self.time_delay:
                    if self._stop_event.is_set():
                        break

        # Ensure the last animation is stopped
        if self.current_animation:
            self.current_animation.stop_animation()



from color_palettes import *

if __name__ == "__main__":
    LED_COUNT  = 400         # Number of LED pixels.
    LED_PIN    = board.D18   # GPIO pin connected to the pixels (18 uses PWM!).
    pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)

    color_scheme_1 = [(255,0,0), (0,255,0), (255,255,255)]
    color_scheme_2 = [(255,255,255), (0,0,255)]
    color_schemes = [color_scheme_1, color_scheme_2]
    animations = [AnimationId.Twinkle.value, AnimationId.TwinkleStars.value, AnimationId.RainbowWave.value, AnimationId.Cylon.value]
    speeds = [1.0, 2.0, 0.5, 4.0]

    animation_playlist = AnimationPlaylist(pixels, animations, color_schemes, speeds, time_delay=10)
    animation_playlist.start_playlist()



