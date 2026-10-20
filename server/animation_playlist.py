
import threading
from animation_constants import *
from random import randrange
from dataclasses import dataclass

from color_palette_manager import ColorPaletteManager

@dataclass
class AnimationPlaylistData:
    animation_names: list[str]
    color_scheme_names: list[str]
    speeds: list[int]

class AnimationPlaylist:
    def __init__(self, pixels, playlist, time_delay=60):
        self.pixels = pixels
        self.pixel_count = pixels.n
        self.playlist = playlist
        self.time_delay = time_delay
        self.thread = None
        self._stop_event = threading.Event()
        self.current_animation = None
        self.current_color_index = None
        self.palette_manager = ColorPaletteManager()

        self.TAG = "Animation Playlist"

    def start_playlist(self):
        Logger.info(self.TAG, "Starting Playlist")
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
            for animation_index, animation_name in enumerate(self.playlist.animation_names):
                if self._stop_event.is_set():
                    break

                # Stop the previous animation
                if self.current_animation:
                    self.current_animation.stop_animation()

                # Pick a random color scheme
                color_scheme_index = randrange(len(self.playlist.color_scheme_names))
                if self.current_color_index is not None and self.current_color_index == color_scheme_index:
                    color_scheme_index = (color_scheme_index + 1) % len(self.playlist.color_scheme_names)
                self.current_color_index = color_scheme_index
                color_palette_name = self.playlist.color_scheme_names[color_scheme_index]
                color_scheme = self.palette_manager.get_color_palettes().get(color_palette_name)

                # pick the animation corresponding to the name
                animation_id = ANIMATIONS[animation_name]["id"]
                self.current_animation = EFFECTS[animation_id](
                    self.pixel_count,
                    self.pixels,
                    colors=color_scheme,
                    speed=self.playlist.speeds[animation_index],
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
