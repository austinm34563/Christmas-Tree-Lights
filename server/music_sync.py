import numpy as np
import neopixel
import board
from pydub import AudioSegment
import pyaudio
import time
import threading

class MusicSync:
    def __init__(self, pixels, audio_file, color_palette, chunk_size=1024):
        self.audio_file = audio_file
        self.num_pixels = len(pixels)
        self.chunk_size = chunk_size
        self.pixels = pixels
        self.color_palette = color_palette  # List of RGB color tuples

        # Load stereo audio without converting to mono
        self.audio = AudioSegment.from_file(audio_file)
        self.audio_data = np.array(self.audio.get_array_of_samples()).reshape((-1, 2))  # Reshape for stereo
        self.sample_rate = self.audio.frame_rate

        # Calculate the time duration for each chunk
        self.chunk_duration = self.chunk_size / self.sample_rate

        # Store frames for pre-processed LED updates
        self.frames = []

    def combine_stereo_channels(self, chunk):
        """Combine left and right channels into a single signal."""
        left_channel = chunk[:, 0]
        right_channel = chunk[:, 1]
        # Combine channels by averaging
        return (left_channel + right_channel) / 2

    def perform_fft(self, chunk):
        """Performs FFT on a combined stereo signal."""
        combined_signal = self.combine_stereo_channels(chunk)
        frequencies = np.fft.fft(combined_signal)
        magnitudes = np.abs(frequencies[:self.chunk_size // 2])  # Positive frequencies
        return magnitudes

    def prepare_frames(self):
        """Pre-compute frequency data for each audio chunk."""
        for i in range(0, len(self.audio_data), self.chunk_size):
            chunk = self.audio_data[i:i + self.chunk_size]
            if len(chunk) < self.chunk_size:
                break  # Skip short chunks at the end

            # Perform FFT analysis on the combined stereo chunk
            magnitudes = self.perform_fft(chunk)
            self.frames.append(magnitudes)

    def interpolate_color(self, color1, color2, t):
        """Interpolate between two colors by a factor t (0 to 1)."""
        return (
            int(color1[0] + (color2[0] - color1[0]) * t),
            int(color1[1] + (color2[1] - color1[1]) * t),
            int(color1[2] + (color2[2] - color1[2]) * t),
        )

    def map_frequencies_to_leds(self, magnitudes):
        """Map frequency magnitudes to LED indices."""
        max_magnitude = np.max(magnitudes) if np.max(magnitudes) > 0 else 1
        led_colors = []

        for i in range(self.num_pixels):
            # Map each LED to a frequency band
            freq_index = int((i / self.num_pixels) * len(magnitudes))
            intensity = magnitudes[freq_index]

            # Normalize intensity and apply to color
            brightness = int(min(intensity * 255 / max_magnitude, 255))
            color = self.color_palette[i % len(self.color_palette)]

            # Apply brightness to color values
            led_colors.append(tuple(int(brightness * c / 255) for c in color))

        return led_colors

    def display_colors(self, led_colors):
        """Update the LED strip with the new color values."""
        for i, color in enumerate(led_colors):
            self.pixels[i] = color
        self.pixels.show()

    def play_audio(self):
        """Play audio using pyaudio for better timing control."""
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(self.audio.sample_width),
                        channels=2,
                        rate=self.sample_rate,
                        output=True)

        # Write audio data to the stream in chunks
        for i in range(0, len(self.audio_data), self.chunk_size):
            chunk = self.audio_data[i:i + self.chunk_size]
            stream.write(chunk.tobytes())

        stream.stop_stream()
        stream.close()
        p.terminate()

    def sync_with_music(self):
        """Main loop to synchronize LEDs with music playback."""
        self.prepare_frames()

        # Start audio playback in a separate thread
        audio_thread = threading.Thread(target=self.play_audio)
        audio_thread.start()

        start_time = time.time()
        previous_colors = [self.pixels[i] for i in range(self.num_pixels)]  # Store initial LED state

        # Synchronize LEDs with music frames
        for index, magnitudes in enumerate(self.frames):
            led_colors = self.map_frequencies_to_leds(magnitudes)

            # Interpolate between current and previous LED colors for smooth transitions
            interpolated_colors = [
                self.interpolate_color(previous_colors[i], led_colors[i], t=1.0)
                for i in range(self.num_pixels)
            ]

            # Update LEDs with the interpolated colors
            self.display_colors(interpolated_colors)

            # Save the current colors for the next frame's interpolation
            previous_colors = interpolated_colors

            # Calculate exact sleep time for the next frame
            next_frame_time = start_time + (index + 1) * self.chunk_duration
            time.sleep(max(0, next_frame_time - time.time()))

        # Ensure audio finishes
        audio_thread.join()

        # Smooth fade-out to black
        self.fade_to_black(previous_colors, duration=1.0)  # 2-second fade-out

    def fade_to_black(self, start_colors, duration=1.0):
        """Gradually fades the LEDs to black over a given duration."""
        steps = 30  # Number of steps in the fade-out
        delay = duration / steps

        for step in range(steps):
            t = step / steps
            faded_colors = [
                self.interpolate_color(color, (0, 0, 0), t)
                for color in start_colors
            ]
            self.display_colors(faded_colors)
            time.sleep(delay)

        # Ensure all LEDs are turned off at the end
        self.display_colors([(0, 0, 0)] * self.num_pixels)


# Example usage
LED_COUNT = 200
LED_PIN = board.D18
pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)

CHRISTMAS_TREE_PALLETE = [(30, 124, 32), (182, 0, 0), (0, 55, 251), (223, 101, 0), (129, 0, 219)]

SONGS = [
    "AllIWantForChristmas.mp3",
    "bleep.mp3",
    "CarolBells.mp3",
    "ChopinBirthday.mp3",
    "FelizNavidad.mp3",
    "Jupiter.mp3",
    "Most_Wonderful_time.mp3",
    "RockYou.mp3",
    "1_minute.mp3",
]

led_music_sync = MusicSync(pixels, f"./songs/{SONGS[2]}", CHRISTMAS_TREE_PALLETE)
led_music_sync.sync_with_music()
