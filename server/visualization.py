
from abc import ABC, abstractmethod

import numpy as np

MIN_FREQ = 30
MAX_FREQ = 4000


class Visualization(ABC):
    """Base interface for audio-reactive LED visualizations."""

    def __init__(
        self,
        num_pixels,
        sample_rate=44100,
        min_freq=MIN_FREQ,
        max_freq=MAX_FREQ,
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


    def get_colors(self, brightness, palette):
        """
        Generate an entire RGB frame using vectorized NumPy operations.

        brightness: Array of brightness values, one per LED.
        palette: List of RGB tuples.
        """
        if not palette:
            return [(0, 0, 0)] * self.num_pixels

        brightness = np.asarray(brightness, dtype=np.float32)
        brightness = np.clip(brightness, 0.0, 1.0)

        palette_array = np.asarray(palette, dtype=np.float32)

        indices = np.arange(self.num_pixels) % len(palette)

        colors = palette_array[indices] * brightness[:, np.newaxis]

        colors = np.clip(colors, 0, 255).astype(np.uint8)

        return [tuple(color) for color in colors]

    def solid_frame(self, brightness, palette):
        """Return a uniformly colored frame."""
        return self.get_colors(
            np.full(self.num_pixels, brightness, dtype=np.float32),
            palette,
        )

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
    Smooth, flowing audio-reactive waveform.

    Uses low-resolution RMS analysis, interpolation,
    and temporal smoothing for a more organic appearance.
    """

    def __init__(
        self,
        *args,
        sensitivity=8.0,
        attack=0.75,
        release=0.20,
        num_bands=32,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.sensitivity = sensitivity
        self.attack = attack
        self.release = release
        self.num_bands = num_bands

        self.smoothed_brightness = np.zeros(
            self.num_pixels,
            dtype=np.float32,
        )

    def reset(self):
        self.smoothed_brightness.fill(0.0)

    def process(self, audio_buffer, palette):
        if not palette or len(audio_buffer) == 0:
            return [(0, 0, 0)] * self.num_pixels

        # Divide audio into a smaller number of groups.
        groups = np.array_split(
            audio_buffer,
            self.num_bands,
        )

        # Calculate RMS for each group.
        levels = np.array([
            np.sqrt(np.mean(group ** 2))
            if len(group) > 0 else 0.0
            for group in groups
        ], dtype=np.float32)

        # Expand the audio data across all LEDs.
        brightness = np.interp(
            np.linspace(0, self.num_bands - 1, self.num_pixels),
            np.arange(self.num_bands),
            levels,
        )

        # Scale audio sensitivity.
        brightness = np.clip(
            brightness * self.sensitivity,
            0.0,
            1.0,
        )

        # Gamma adjustment for better visibility.
        brightness = np.power(brightness, 1.3)

        # Smooth transitions using separate attack/release rates.
        rising = brightness > self.smoothed_brightness

        smoothing = np.where(
            rising,
            self.attack,
            self.release,
        )

        self.smoothed_brightness += (
            brightness - self.smoothed_brightness
        ) * smoothing

        return self.get_colors(
            self.smoothed_brightness,
            palette,
        )



class BeatVisualization(Visualization):
    """
    Bass-focused beat detector using spectral flux.

    Detects sudden increases in low-frequency energy rather
    than relying on overall audio volume.

    Includes adaptive sensitivity, beat cooldown, and
    smooth LED pulse decay.
    """

    def __init__(
        self,
        *args,
        threshold=1.8,
        decay=0.82,
        min_interval=0.18,
        min_energy=0.008,
        min_flux=0.12,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.threshold = threshold
        self.decay = decay
        self.min_interval = min_interval
        self.min_energy = min_energy
        self.min_flux = min_flux

        self.previous_bass = None
        self.flux_baseline = 0.0

        self.samples_since_beat = float("inf")

        self.pulse = 0.0

    def reset(self):
        self.previous_bass = None
        self.flux_baseline = 0.0
        self.samples_since_beat = float("inf")
        self.pulse = 0.0

    def process(self, audio_buffer, palette):
        if not palette or len(audio_buffer) == 0:
            return [(0, 0, 0)] * self.num_pixels

        # Overall audio energy.
        rms = float(np.sqrt(np.mean(audio_buffer ** 2)))

        # Ignore near-silence.
        if rms < self.min_energy:
            self.pulse *= self.decay
            self.previous_bass = None
            return self.solid_frame(self.pulse, palette)

        # Calculate FFT.
        windowed = audio_buffer * np.hanning(len(audio_buffer))

        fft = np.fft.rfft(windowed)
        magnitudes = np.abs(fft)

        # Isolate approximately 40-170 Hz.
        frequencies = np.fft.rfftfreq(
            len(audio_buffer),
            d=1.0 / self.sample_rate,
        )

        bass = magnitudes[
            (frequencies >= 40) &
            (frequencies <= 170)
        ]

        if len(bass) == 0:
            return self.solid_frame(self.pulse, palette)

        # Calculate positive spectral changes.
        if self.previous_bass is None:
            self.previous_bass = bass.copy()
            self.pulse *= self.decay
            return self.solid_frame(self.pulse, palette)

        flux = float(
            np.sum(np.maximum(bass - self.previous_bass, 0.0))
            / (np.sum(self.previous_bass) + 1e-6)
        )

        self.previous_bass = bass.copy()

        # Determine whether this is a new beat.
        threshold = max(
            self.min_flux,
            self.flux_baseline * self.threshold,
        )

        self.samples_since_beat += len(audio_buffer)

        cooldown_samples = (
            self.min_interval * self.sample_rate
        )

        beat_detected = (
            flux > threshold
            and self.samples_since_beat >= cooldown_samples
        )

        if beat_detected:
            self.pulse = 1.0
            self.samples_since_beat = 0
        else:
            self.pulse *= self.decay

        # Slowly adapt to the current music.
        self.flux_baseline = (
            0.95 * self.flux_baseline +
            0.05 * flux
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

        level = min(
            self.smoothed_energy * self.sensitivity,
            1.0,
        )

        lit_count = int(round(level * self.num_pixels))

        brightness = np.zeros(
            self.num_pixels,
            dtype=np.float32,
        )

        brightness[:lit_count] = 0.5 + 0.5 * level

        return self.get_colors(brightness, palette)
