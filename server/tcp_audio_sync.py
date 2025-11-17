import socket
import numpy as np
import sounddevice as sd
import threading
import time
import sys
import queue

PI_PORT = 5005
SAMPLE_RATE = 44100
CHANNELS = 2
CHUNK_SIZE = 2048  # frames per chunk
CHUNK_BYTES = CHUNK_SIZE * CHANNELS * 2  # int16

NUM_BANDS = 120
MAX_HEIGHT = 20
MIN_FREQ = 30
MAX_FREQ = SAMPLE_RATE // 2

class AudioReceiver:
    def __init__(self):
        # --- Networking ---
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("0.0.0.0", PI_PORT))
        self.sock.listen(1)
        print("Waiting for Mac to connect...")
        self.conn, _ = self.sock.accept()
        print("Mac connected!")

        # --- Audio output ---
        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE
        )
        self.stream.start()

        # --- Queue for both playback and FFT ---
        self.audio_queue = queue.Queue(maxsize=256)

        # --- FFT smoothing ---
        self.prev_mags = None
        self.max_mag = 1e-6
        self.freq_bins = np.logspace(np.log10(MIN_FREQ), np.log10(MAX_FREQ), NUM_BANDS + 1)

        # --- Control ---
        self.running = True
        threading.Thread(target=self._network_loop, daemon=True).start()
        threading.Thread(target=self._playback_and_visual_loop, daemon=True).start()

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

    # Play audio and visualize simultaneously
    def _playback_and_visual_loop(self):
        last_block = np.zeros((CHUNK_SIZE, CHANNELS), dtype=np.int16)
        while self.running:
            try:
                pcm = self.audio_queue.get(timeout=0.01)
                last_block = pcm
            except queue.Empty:
                pcm = last_block  # repeat last frame if no new data

            # Playback
            self.stream.write(pcm)

            # Mono for FFT
            mono = pcm.mean(axis=1).astype(np.float32)

            # FFT
            mags = self.perform_fft(mono)
            bands = self.compute_bands(mags)
            self.draw_fft(bands)

    # FFT with smoothing and max magnitude tracking
    def perform_fft(self, chunk):
        if np.all(chunk == 0):
            # No audio: reset max magnitude smoothly
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

    # Map FFT to log-frequency bands
    def compute_bands(self, mags):
        N = len(mags) * 2
        freq_per_bin = SAMPLE_RATE / N
        band_vals = []
        for i in range(NUM_BANDS):
            start = int(self.freq_bins[i] / freq_per_bin)
            end = int(self.freq_bins[i+1] / freq_per_bin)
            slice_vals = mags[start:end] if end > start else np.array([0])
            avg = np.mean(slice_vals)
            band_vals.append(avg)
        # Normalize
        return [min(int((b / max(self.max_mag, 1e-6)) * MAX_HEIGHT), MAX_HEIGHT) for b in band_vals]

    # Terminal visualization
    def draw_fft(self, bands):
        sys.stdout.write("\x1b[H\x1b[2J")  # clear screen
        for level in reversed(range(1, MAX_HEIGHT + 1)):
            line = "".join("█" if b >= level else " " for b in bands)
            print(line)
        print("-" * NUM_BANDS)


# -----------------------
# Main
# -----------------------
receiver = AudioReceiver()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    receiver.running = False
