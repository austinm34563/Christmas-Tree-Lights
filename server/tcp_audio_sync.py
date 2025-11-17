import socket
import numpy as np
import sounddevice as sd
import threading
import time
import sys
import queue
import neopixel
import board

# -----------------------
# Config
# -----------------------
PI_PORT = 5005
SAMPLE_RATE = 44100
CHANNELS = 2
CHUNK_SIZE = 4096  # frames per chunk
CHUNK_BYTES = CHUNK_SIZE * CHANNELS * 2  # int16

NUM_BANDS = 120
NUM_LEDS = 50
LED_PIN = board.D18
COLOR_PALETTE = [(30, 124, 32), (182, 0, 0), (0, 55, 251), (223, 101, 0), (129, 0, 219)]

# -----------------------
# Audio + LED Receiver
# -----------------------
class AudioReceiver:
    def __init__(self):
        # Networking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("0.0.0.0", PI_PORT))
        self.sock.listen(1)
        print("Waiting for Mac to connect...")
        self.conn, _ = self.sock.accept()
        print("Mac connected!")

        # Audio output
        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            latency='high'
        )
        self.stream.start()

        # LED strip
        self.pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, auto_write=False, pixel_order=neopixel.RGB, brightness=1.0)

        # Queues
        self.audio_queue = queue.Queue(maxsize=256)

        # FFT smoothing
        self.prev_mags = None
        self.max_mag = 1e-6
        self.freq_bins = np.logspace(np.log10(30), np.log10(12000), NUM_LEDS + 1)

        self.running = True
        threading.Thread(target=self._network_loop, daemon=True).start()
        threading.Thread(target=self._playback_and_led_loop, daemon=True).start()

    # Receive audio from network
    def _network_loop(self):
        buffer = b""
        while self.running:
            data = self.conn.recv(8192)
            if not data:
                continue
            buffer += data
            while len(buffer) >= CHUNK_BYTES:
                raw = buffer[:CHUNK_BYTES]
                buffer = buffer[CHUNK_BYTES:]
                pcm = np.frombuffer(raw, dtype=np.int16).reshape((-1, 2))
                try:
                    self.audio_queue.put_nowait(pcm)
                except queue.Full:
                    pass

    # Play audio and update LEDs simultaneously
    def _playback_and_led_loop(self):
        last_block = np.zeros((CHUNK_SIZE, CHANNELS), dtype=np.int16)
        while self.running:
            try:
                pcm = self.audio_queue.get(timeout=0.01)
                last_block = pcm
            except queue.Empty:
                pcm = last_block

            # Playback
            self.stream.write(pcm)

            # Mono for FFT
            mono = pcm.mean(axis=1).astype(np.float32)

            # FFT
            mags = self.perform_fft(mono)
            led_colors = self.compute_led_colors(mags)
            self.update_leds(led_colors)

    # FFT with smoothing
    def perform_fft(self, chunk):
        if np.all(chunk == 0):
            self.max_mag *= 0.9
            self.prev_mags = np.zeros_like(self.prev_mags) if self.prev_mags is not None else np.zeros(len(chunk)//2)
            return self.prev_mags

        windowed = chunk * np.hanning(len(chunk))
        fft = np.fft.fft(windowed)
        mags = np.abs(fft[:len(fft)//2])

        if self.prev_mags is None:
            self.prev_mags = mags

        smoothed = 0.25 * mags + 0.75 * self.prev_mags
        self.prev_mags = smoothed
        self.max_mag = max(self.max_mag * 0.999, np.max(smoothed))
        return smoothed

    # Map FFT magnitudes to LED colors
    def compute_led_colors(self, mags):
        led_colors = []
        N = len(mags)*2
        freq_per_bin = SAMPLE_RATE / N
        min_mag = 0
        max_mag = max(self.max_mag, 1e-6)
        for i in range(NUM_LEDS):
            start = int(self.freq_bins[i] / freq_per_bin)
            end = int(self.freq_bins[i+1] / freq_per_bin)
            if end <= start:
                end = start + 1
            band_mag = np.mean(mags[start:end])
            brightness = band_mag / max_mag
            color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
            led_colors.append(tuple(int(c*brightness) for c in color))
        return led_colors

    # Update LEDs
    def update_leds(self, colors):
        for i, color in enumerate(colors):
            self.pixels[i] = color
        self.pixels.show()


# -----------------------
# Main
# -----------------------
receiver = AudioReceiver()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    receiver.running = False
