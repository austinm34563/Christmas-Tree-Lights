import numpy as np
import neopixel
import board
from pydub import AudioSegment
import pyaudio
import time
import threading
import math

class MusicSync:
    def __init__(self, pixels, audio_file, color_palette, chunk_size=1024):
        self.audio_file = audio_file
        self.num_pixels = len(pixels)
        self.chunk_size = chunk_size
        self.pixels = pixels
        self.color_palette = color_palette  # List of RGB color tuples

        # Load and preprocess audio
        self.audio = AudioSegment.from_file(audio_file)
        self.audio = self.audio.set_channels(1)  # Convert to mono
        self.audio_data = np.array(self.audio.get_array_of_samples())
        self.sample_rate = self.audio.frame_rate

        # Calculate the time duration for each chunk
        self.chunk_duration = self.chunk_size / self.sample_rate

        # Store frames for pre-processed LED updates
        self.frames = []

    def perform_fft(self, chunk):
        """Performs FFT on a chunk of audio data and returns frequency intensities for each frequency band."""
        # Perform FFT on the chunk of audio data
        frequencies = np.fft.fft(chunk)
        magnitudes = np.abs(frequencies[:self.chunk_size // 2])  # Get magnitudes of positive frequencies

        return magnitudes

    def prepare_frames(self):
        """Pre-compute frequency data for each audio chunk."""
        for i in range(0, len(self.audio_data), self.chunk_size):
            chunk = self.audio_data[i:i + self.chunk_size]
            if len(chunk) < self.chunk_size:
                break  # Skip short chunks at the end

            # Perform FFT analysis and get frequency magnitudes
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
        """Map frequency magnitudes to LED indices with piecewise scaling for dramatic volume effect."""
        # Apply logarithmic scaling for low frequencies
        log_bands = np.logspace(0, np.log10(len(magnitudes) // 2), self.num_pixels // 2)

        # Apply a custom scaling for high frequencies (for example, exponential scaling)
        high_bands = np.linspace(len(magnitudes) // 2, len(magnitudes), self.num_pixels // 2)
        high_bands = np.power(high_bands, 1.3)  # Exponentiate high frequencies to make them more dramatic

        # Combine both
        all_bands = np.concatenate([log_bands, high_bands])

        led_colors = []
        for i in range(self.num_pixels):
            # Get the frequency index based on the combined scaling
            freq_index = int(all_bands[i])

            # Ensure the index is within bounds of the magnitudes array
            if freq_index >= len(magnitudes):
                freq_index = len(magnitudes) - 1

            # Get the intensity for this frequency band
            intensity = magnitudes[freq_index]

            # Normalize intensity to a range of 0 to 255
            max_magnitude = np.max(magnitudes) if np.max(magnitudes) > 0 else 1
            brightness = int(min(intensity * 255 / max_magnitude, 255))

            # Apply brightness scaling to color
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
                        channels=1,
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

        for index, magnitudes in enumerate(self.frames):
            led_colors = self.map_frequencies_to_leds(magnitudes)

            # Interpolate between current and previous LED colors for smooth transitions
            interpolated_colors = [
                self.interpolate_color(previous_colors[i], led_colors[i], t=0.1)
                for i in range(self.num_pixels)
            ]

            # Update LEDs with the interpolated colors
            self.display_colors(interpolated_colors)

            # Save the current colors for the next frame's interpolation
            previous_colors = interpolated_colors

            # Calculate exact sleep time for next frame
            next_frame_time = start_time + (index + 1) * self.chunk_duration
            time.sleep(max(0, next_frame_time - time.time()))

        audio_thread.join()


# Example usage
LED_COUNT  = 200         # Number of LED pixels.
LED_PIN    = board.D18   # GPIO pin connected to the pixels (18 uses PWM!).
pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)

# Define a color palette
color_palette = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Yellow
    (0, 255, 255),  # Cyan
    (255, 0, 255),  # Magenta
]

CHRISTMAS_TREE_PALLETE = [(30, 124, 32), (182, 0, 0), (0, 55, 251), (223, 101, 0), (129, 0, 219)]


# Initialize and start sync
led_music_sync = MusicSync(pixels, "./songs/Most_Wonderful_time.mp3", color_palette=CHRISTMAS_TREE_PALLETE)
led_music_sync.sync_with_music()