
from abc import ABC, abstractmethod

import numpy as np


class Visualization(ABC):
    """Base interface for audio-reactive LED visualizations."""

    def __init__(
        self,
        num_pixels,
        sample_rate=44100,
        min_freq=30,
        max_freq=7902,
    ):
        self.num_pixels = num_pixels
        self.sample_rate = sample_rate
        self.min_freq = min_freq
        self.max_freq = max_freq

    @abstractmethod
    def process(self, audio_buffer, palette):
        """
        Process a mono float32 audio buffer and return an RGB frame.

        audio_buffer: NumPy array containing audio samples, typically
                      normalized to [-1.0, 1.0].
        palette: List of (r, g, b) tuples.
        Returns: List of num_pixels RGB tuples.
        """
        raise NotImplementedError

    def reset(self):
        """Reset effect state when switching visualizations."""
        pass

    def get_color(self, index, brightness, palette):
        """Get a palette color scaled by brightness."""
        if not palette:
            return (0, 0, 0)

        brightness = float(np.clip(brightness, 0.0, 1.0))
        color = palette[index % len(palette)]

        return tuple(
            int(np.clip(channel * brightness, 0, 255))
            for channel in color
        )

    def solid_frame(self, brightness, palette):
        """Return a uniformly colored frame."""
        return [
            self.get_color(i, brightness, palette)
            for i in range(self.num_pixels)
        ]




class FftVisualization(Visualization):
    """Original FFT visualization, preserving legacy behavior."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prev_mags = None
        self.max_mag = 1e-6

        self.freq_bins = np.logspace(
            np.log10(self.min_freq),
            np.log10(self.max_freq),
            self.num_pixels + 1,
        )

    def reset(self):
        self.prev_mags = None
        self.max_mag = 1e-6

    def process(self, audio_buffer, palette):
        if not palette:
            return [(0, 0, 0)] * self.num_pixels

        # Original _perform_fft(): silence handling and decay.
        if np.all(audio_buffer == 0):
            self.max_mag *= 0.9

            if self.prev_mags is None:
                self.prev_mags = np.zeros(len(audio_buffer) // 2)
            else:
                self.prev_mags *= 0.8

            mags = self.prev_mags

        else:
            # Original FFT calculation.
            windowed = audio_buffer * np.hanning(len(audio_buffer))
            fft = np.fft.fft(windowed)
            mags = np.abs(fft[:len(fft) // 2])

            if self.prev_mags is None:
                self.prev_mags = mags

            smoothed = 0.25 * mags + 0.75 * self.prev_mags
            self.prev_mags = smoothed

            self.max_mag = max(
                self.max_mag * 0.999,
                float(np.max(smoothed)),
            )

            mags = smoothed

        # Original _compute_led_colors(): frequency mapping.
        colors = []
        N = len(mags) * 2
        freq_per_bin = self.sample_rate / N
        local_max = max(self.max_mag, 1e-6)

        for i in range(self.num_pixels):
            lo = int(self.freq_bins[i] / freq_per_bin)
            hi = int(self.freq_bins[i + 1] / freq_per_bin)

            if hi <= lo:
                hi = lo + 1

            band_mag = np.mean(mags[lo:hi])
            brightness = band_mag / local_max

            color = palette[i % len(palette)]

            colors.append((
                int(color[0] * brightness),
                int(color[1] * brightness),
                int(color[2] * brightness),
            ))
        # return colors[::-1]
        return colors


class WaveformVisualization(Visualization):
    """
    Displays audio amplitude across the strip.

    Samples are divided into groups, one group per LED.
    Stronger signals produce brighter LEDs.
    """

    def process(self, audio_buffer, palette):
        if not palette or len(audio_buffer) == 0:
            return [(0, 0, 0)] * self.num_pixels

        groups = np.array_split(audio_buffer, self.num_pixels)
        colors = []

        for i, group in enumerate(groups):
            if len(group) == 0:
                brightness = 0.0
            else:
                # RMS provides a smoother amplitude display than
                # looking at a single sample.
                rms = float(np.sqrt(np.mean(group ** 2)))
                brightness = min(rms * 3.0, 1.0)

            colors.append(self.get_color(i, brightness, palette))

        return colors


class BeatVisualization(Visualization):
    """
    Flashes the whole strip when audio energy rises sharply.

    This is a lightweight energy-onset detector, not a full
    musical beat tracker.
    """

    def __init__(
        self,
        *args,
        threshold=1.6,
        decay=0.72,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.threshold = threshold
        self.decay = decay
        self.previous_energy = 0.0
        self.pulse = 0.0

    def reset(self):
        self.previous_energy = 0.0
        self.pulse = 0.0

    def process(self, audio_buffer, palette):
        if not palette or len(audio_buffer) == 0:
            return [(0, 0, 0)] * self.num_pixels

        energy = float(np.sqrt(np.mean(audio_buffer ** 2)))

        # Detect a sudden increase over the recent energy level.
        if (
            energy > 0.015
            and energy > self.previous_energy * self.threshold
        ):
            self.pulse = 1.0
        else:
            self.pulse *= self.decay

        self.previous_energy = max(
            energy,
            self.previous_energy * 0.85,
        )

        return self.solid_frame(self.pulse, palette)


class EnergyVisualization(Visualization):
    """
    A loudness meter: quiet audio lights few LEDs, while
    loud audio lights most or all of the strip.
    """

    def __init__(
        self,
        *args,
        sensitivity=4.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.sensitivity = sensitivity
        self.smoothed_energy = 0.0

    def reset(self):
        self.smoothed_energy = 0.0

    def process(self, audio_buffer, palette):
        if not palette or len(audio_buffer) == 0:
            return [(0, 0, 0)] * self.num_pixels

        rms = float(np.sqrt(np.mean(audio_buffer ** 2)))
        self.smoothed_energy = (
            0.35 * rms + 0.65 * self.smoothed_energy
        )

        level = min(self.smoothed_energy * self.sensitivity, 1.0)
        lit_count = int(round(level * self.num_pixels))

        colors = []

        for i in range(self.num_pixels):
            if i < lit_count:
                # A little brightness variation makes the meter
                # less visually flat.
                brightness = 0.5 + 0.5 * level
                colors.append(self.get_color(i, brightness, palette))
            else:
                colors.append((0, 0, 0))

        return colors
