import numpy as np
import neopixel
import board
from pydub import AudioSegment
import pyaudio
import time
import threading
from os.path import join
from logger import Logger
from song_scraper import *


class MusicSync:
    def __init__(self, pixels, audio_file, color_palette, chunk_size=1024):
        self.tag = "MusicSync"

        Logger.info(self.tag, f"Loading {audio_file}")

        self.audio_file = join(SONG_DIRECTORY, audio_file)
        print(self.audio_file)
        self.num_pixels = len(pixels)
        self.chunk_size = chunk_size
        self.pixels = pixels
        self.color_palette = color_palette  # List of RGB color tuples

        # Load stereo audio without converting to mono
        self.audio = AudioSegment.from_file(self.audio_file)
        self.audio_data = np.array(self.audio.get_array_of_samples()).reshape((-1, 2))  # Reshape for stereo
        self.sample_rate = self.audio.frame_rate

        self.audio_manager = pyaudio.PyAudio()

        self.stream = None
        try:
            self.stream = self.audio_manager.open(format=self.audio_manager.get_format_from_width(self.audio.sample_width),
                            channels=self.audio.channels,
                            rate=self.sample_rate,
                            output=True)
        except OSError as e:
            Logger.error(self.tag, f"Error initializing audio stream: {e}")

        # Calculate the time duration for each chunk
        self.chunk_duration = self.chunk_size / self.sample_rate

        # Store frames for pre-processed LED updates
        self.frames = []

        # Thread management
        self._thread = None
        self._stop_event = threading.Event()

        # callback info
        self.timing_callback = None  # Placeholder for the timing callback
        self.total_duration = len(self.audio_data) / self.sample_rate  # Total playtime in seconds

        # log audio
        Logger.info(
            self.tag,
            "Audio Information:\n"
            f" - Number of channels: {self.audio.channels}\n"
            f" - Sample Rate: {self.audio.frame_rate}\n"
            f" - Sample Width: {self.audio.sample_width}\n"
            f" - Frame Width: {self.audio.frame_width}\n"
        )

    def start_sync(self):
        """Start the music synchronization in a separate thread."""
        if self._thread and self._thread.is_alive():
            Logger.warning(self.tag, "MusicSync is already running.")
            return False

        if self.stream is None:
            Logger.error(self.tag, "Stream not set up properly.")
            return False

        Logger.info(self.tag, "Start sync requested")
        # Clear the stop event and start a new thread
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_sync, daemon=True)
        self._thread.start()
        return True

    def stop_sync(self):
        """Stop the music synchronization and wait for the thread to finish."""
        if not self._thread or not self._thread.is_alive():
            Logger.info(self.tag, "MusicSync is not running.")
            return

        Logger.info(self.tag, "Stopping music sync")
        self._stop_event.set()
        self._thread.join()
        Logger.info(self.tag, "Music Stopped")


    def register_timing_callback(self, callback):
        """Register a timing callback that gets the current and total playtime."""
        if not callable(callback):
            raise ValueError("The provided callback must be callable.")
        self.timing_callback = callback

    def _smooth_magnitudes(self, magnitudes, alpha=0.2):
        """Smooth magnitudes using exponential moving average."""
        if not hasattr(self, '_previous_magnitudes'):
            self._previous_magnitudes = magnitudes
        smoothed = alpha * magnitudes + (1 - alpha) * self._previous_magnitudes
        self._previous_magnitudes = smoothed
        return smoothed

    def _teardown_audio(self):
        """Clean up PyAudio and stream objects."""
        Logger.info(self.tag, "Tearing down audio")
        self.stream.stop_stream()
        self.stream.close()
        self.audio_manager.terminate()

    def _combine_stereo_channels(self, chunk):
        """Combine left and right channels into a single signal."""
        left_channel = chunk[:, 0]
        right_channel = chunk[:, 1]
        # Combine channels by averaging
        return (left_channel + right_channel) / 2

    def _perform_fft(self, chunk):
        """Performs FFT on a combined stereo signal."""
        combined_signal = self._combine_stereo_channels(chunk)
        frequencies = np.fft.fft(combined_signal)
        magnitudes = np.abs(frequencies[:self.chunk_size // 2])  # Positive frequencies
        return magnitudes

    def _prepare_frames(self):
        """Pre-compute frequency data for each audio chunk."""
        for i in range(0, len(self.audio_data), self.chunk_size):
            chunk = self.audio_data[i:i + self.chunk_size]
            if len(chunk) < self.chunk_size:
                break  # Skip short chunks at the end

            # Perform FFT analysis on the combined stereo chunk
            magnitudes = self._perform_fft(chunk)
            smoothed_magnitudes = self._smooth_magnitudes(magnitudes)
            self.frames.append(smoothed_magnitudes)

    def _interpolate_color(self, color1, color2, t):
        """Interpolate smoothly between two colors."""
        return tuple(
            int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2)
        )

    def _map_frequencies_to_leds(self, magnitudes):
        """Map frequency magnitudes to LED indices with balanced low, mid, and high frequency emphasis."""
        max_magnitude = np.max(magnitudes) if np.max(magnitudes) > 0 else 1
        led_colors = []

        # Calculate the frequency range per LED
        frequency_bands = np.linspace(0, len(magnitudes), self.num_pixels + 1, dtype=int)

        for i in range(self.num_pixels):
            # Average magnitudes in the current frequency band
            band_start = frequency_bands[i]
            band_end = frequency_bands[i + 1]
            band_magnitude = np.mean(magnitudes[band_start:band_end])

            # Normalize the magnitude to a brightness value
            brightness = int(min(band_magnitude * 255 / max_magnitude, 255))

            # Cycle through the color palette
            color = self.color_palette[i % len(self.color_palette)]

            # Scale color by brightness
            led_color = tuple(int(brightness * c / 255) for c in color)
            led_colors.append(led_color)

        return led_colors

    def _display_colors(self, led_colors):
        """Update the LED strip with the new color values."""
        for i, color in enumerate(led_colors):
            self.pixels[i] = color
        self.pixels.show()

    def _play_audio(self):
        """Play audio using pyaudio for better timing control."""

        # Write audio data to the stream in chunks
        for i in range(0, len(self.audio_data), self.chunk_size):
            if self._stop_event.is_set():  # Graceful stopping
                Logger.info(self.tag, "Stopping audio thread.")
                break
            chunk = self.audio_data[i:i + self.chunk_size]
            self.stream.write(chunk.tobytes())

    def _run_sync(self):
        """Internal method to run the sync_with_music loop with enhanced smoothness."""
        time.sleep(2)
        Logger.info(self.tag, "Sync started")
        self._prepare_frames()

        # Start audio playback in a separate thread
        audio_thread = threading.Thread(target=self._play_audio)
        audio_thread.start()

        start_time = time.time()
        previous_colors = [(0, 0, 0)] * self.num_pixels  # Start with all LEDs off

        for index, magnitudes in enumerate(self.frames):
            if self._stop_event.is_set():
                break

            # Calculate current playtime
            current_playtime = index * self.chunk_duration

            # Invoke the timing callback if registered
            if self.timing_callback:
                self.timing_callback(current_playtime, self.total_duration)

            # Map frequencies to LEDs and update colors
            led_colors = self._map_frequencies_to_leds(magnitudes)

            # Interpolate between current and previous LED colors for smooth transitions
            interpolated_colors = [
                self._interpolate_color(previous_colors[i], led_colors[i], t=0.5)
                for i in range(self.num_pixels)
            ]

            # Update LEDs with the interpolated colors
            self._display_colors(interpolated_colors)

            # Save the current colors for the next frame's interpolation
            previous_colors = interpolated_colors

            # Calculate exact sleep time for the next frame
            next_frame_time = start_time + (index + 1) * self.chunk_duration
            time.sleep(max(0, next_frame_time - time.time()))

        Logger.info(self.tag, "End of sync")

        # Ensure audio finishes
        self._stop_event.set()
        audio_thread.join()

        # teardown audio
        self._teardown_audio()

        # Smooth fade-out to black if not stopped prematurely
        self._fade_to_black(previous_colors, duration=1.0)


    def _fade_to_black(self, start_colors, duration=1.0):
        """Gradually fades the LEDs to black over a given duration."""
        Logger.info(self.tag, "Fading to black")
        delay = 0.01 # smooth transition
        steps = int(duration // delay)

        for step in range(steps):
            t = step / steps
            faded_colors = [
                self._interpolate_color(color, (0, 0, 0), t)
                for color in start_colors
            ]
            self._display_colors(faded_colors)
            time.sleep(delay)

        # Ensure all LEDs are turned off at the end
        self._display_colors([(0, 0, 0)] * self.num_pixels)

# Example usage
if __name__ == "__main__":
    LED_COUNT = 200
    LED_PIN = board.D18
    pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)

    CHRISTMAS_TREE_PALLETE = [(30, 124, 32), (182, 0, 0), (0, 55, 251), (223, 101, 0), (129, 0, 219)]

    def timing_callback(current_time, total_time):
        # print(f"Current time: {current_time:.2f}s / {total_time:.2f}s")
        pass

    available_songs = get_songs()
    available_songs.sort()
    for ind, song in enumerate(available_songs):
        print(f"{ind+1}. {song}")
    song_choice = int(input("Choose from above: "))

    led_music_sync = MusicSync(pixels, available_songs[song_choice - 1], CHRISTMAS_TREE_PALLETE)
    led_music_sync.register_timing_callback(timing_callback)
    led_music_sync.start_sync()

    # time.sleep(10)
    # led_music_sync.stop_sync()

