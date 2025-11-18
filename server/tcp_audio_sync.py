import socket
import numpy as np
import sounddevice as sd
import threading
import time
import queue
import neopixel
import board
from logger import Logger

PI_PORT = 5005
SAMPLE_RATE = 44100
CHANNELS = 2
AUDIO_CHUNK_SIZE = 4096
AUDIO_CHUNK_BYTES = AUDIO_CHUNK_SIZE * CHANNELS * 2

VIS_CHUNK_SIZE = 1024

MIN_FREQ = 30
MAX_FREQ = SAMPLE_RATE // 2


class AudioVisualReceiver:
    def __init__(self, pixels, color_palette, enabled = False):
        self.tag = "AudioVisualReceiver"

        self.visualization_enabled = enabled
        self.visualization_lock = threading.Lock()

        # Networking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("0.0.0.0", PI_PORT))
        self.sock.listen(1)

        self.conn = None          # active connection
        self.connected = False    # connection state
        self.conn_lock = threading.Lock()

        # Audio output
        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=AUDIO_CHUNK_SIZE,
            latency="high"
        )
        self.stream.start()

        # LEDs
        self.pixels = pixels
        self.color_palette = color_palette
        self.num_pixels = len(pixels)
        self.palette_lock = threading.Lock()

        # Queues
        self.audio_queue = queue.Queue(maxsize=256)
        self.led_queue = queue.Queue(maxsize=2)

        # FFT state
        self.prev_mags = None
        self.max_mag = 1e-6
        self.freq_bins = np.logspace(np.log10(MIN_FREQ), np.log10(MAX_FREQ), self.num_pixels + 1)

        self.running = True

        # Start workers
        threading.Thread(target=self._connection_manager, daemon=True).start()
        threading.Thread(target=self._network_loop, daemon=True).start()
        threading.Thread(target=self._audio_loop, daemon=True).start()
        threading.Thread(target=self._led_worker, daemon=True).start()

    # set color palette safely
    def set_color_palette(self, new_palette):
        """Safely update color palette. Accepts either:
        - list of (r,g,b) tuples
        - list of ints (0xRRGGBB)
        - mixed list (ints + tuples)
        """
        processed = []

        for item in new_palette:
            if isinstance(item, int):
                # Convert 0xRRGGBB → (R,G,B)
                r = (item >> 16) & 0xFF
                g = (item >> 8) & 0xFF
                b = item & 0xFF
                processed.append((r, g, b))

            elif isinstance(item, (tuple, list)) and len(item) == 3:
                # Already an RGB triple
                r, g, b = item
                processed.append((int(r), int(g), int(b)))

            else:
                raise ValueError(
                    f"Invalid palette entry: {item}. "
                    "Expected int (0xRRGGBB) or (r,g,b) tuple."
                )

        # Store safely
        with self.palette_lock:
            self.color_palette = processed

    def set_visualization_enabled(self, enabled: bool):
        with self.visualization_lock:
            self.visualization_enabled = bool(enabled)

        if not enabled:
            # turn LEDs off
            for i in range(self.num_pixels):
                self.pixels[i] = (0,0,0)
            self.pixels.show()

        Logger.info(self.tag, f"Visualization/audio enabled = {enabled}")

    def is_enabled(self):
        with self.visualization_lock:
            return self.visualization_enabled

    # worker to manager TCP connection
    def _connection_manager(self):
        """Accepts incoming connections and handles reconnects."""
        while self.running:
            if not self.connected:
                Logger.info(self.tag, "Waiting for Mac to connect...")
                try:
                    new_conn, _ = self.sock.accept()
                except OSError:
                    continue

                with self.conn_lock:
                    self.conn = new_conn
                    self.connected = True

                Logger.info(self.tag, "Mac connected!")

            time.sleep(0.2)

    def _network_loop(self):
        buffer = b""
        while self.running:
            if not self.connected:
                time.sleep(0.05)
                continue

            try:
                data = self.conn.recv(8192)
            except (ConnectionResetError, OSError):
                self._handle_disconnect()
                continue

            if not data:
                # client closed connection
                self._handle_disconnect()
                continue

            buffer += data

            while len(buffer) >= AUDIO_CHUNK_BYTES:
                raw = buffer[:AUDIO_CHUNK_BYTES]
                buffer = buffer[AUDIO_CHUNK_BYTES:]
                pcm = np.frombuffer(raw, dtype=np.int16).reshape((-1, CHANNELS))

                try:
                    self.audio_queue.put_nowait(pcm)
                except queue.Full:
                    pass

    # Disconnect cleanup
    def _handle_disconnect(self):
        Logger.info(self.tag, "Mac disconnected.")
        with self.conn_lock:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
            self.connected = False

        # clear state
        while not self.audio_queue.empty():
            self.audio_queue.get_nowait()
        while not self.led_queue.empty():
            self.led_queue.get_nowait()

        self.prev_mags = None
        self.max_mag = 1e-6

    # audio thread
    def _audio_loop(self):
        silence = np.zeros((AUDIO_CHUNK_SIZE, CHANNELS), dtype=np.int16)

        while self.running:

            # If not connected, output silence
            if not self.connected:
                self.stream.write(silence)
                time.sleep(0.01)
                continue

            try:
                pcm = self.audio_queue.get(timeout=0.01)
            except queue.Empty:
                pcm = silence

            # Check visualization state (controls both audio + LED)
            with self.visualization_lock:
                vis_enabled = self.visualization_enabled

            if not vis_enabled:
                # Output silence instead of audio
                self.stream.write(silence)
                continue

            # Otherwise normal audio output
            self.stream.write(pcm)

            # Now handle FFT + LED visualization (only when enabled)
            for i in range(0, AUDIO_CHUNK_SIZE, VIS_CHUNK_SIZE):
                vis = pcm[i:i+VIS_CHUNK_SIZE]

                if len(vis) < VIS_CHUNK_SIZE:
                    vis = np.pad(vis, ((0, VIS_CHUNK_SIZE-len(vis)), (0,0)))

                mono = vis.mean(axis=1).astype(np.float32)
                mags = self._perform_fft(mono)
                led_frame = self._compute_led_colors(mags)

                try:
                    self.led_queue.put_nowait(led_frame)
                except queue.Full:
                    pass


    # led worker thread
    def _led_worker(self):
        while self.running:
            try:
                frame = self.led_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            with self.visualization_lock:
                if not self.visualization_enabled:
                    continue

            for i, color in enumerate(frame):
                self.pixels[i] = color

            self.pixels.show()

    ## calculate DFT using FFT
    def _perform_fft(self, chunk):
        if np.all(chunk == 0):
            self.max_mag *= 0.9
            if self.prev_mags is None:
                self.prev_mags = np.zeros(VIS_CHUNK_SIZE // 2)
            else:
                self.prev_mags *= 0.8
            return self.prev_mags

        windowed = chunk * np.hanning(len(chunk))
        fft = np.fft.fft(windowed)
        mags = np.abs(fft[:len(fft)//2])

        if self.prev_mags is None:
            self.prev_mags = mags

        smoothed = 0.25*mags + 0.75*self.prev_mags
        self.prev_mags = smoothed
        self.max_mag = max(self.max_mag * 0.999, np.max(smoothed))
        return smoothed

    def _compute_led_colors(self, mags):
        colors = []
        N = len(mags) * 2
        freq_per_bin = SAMPLE_RATE / N
        local_max = max(self.max_mag, 1e-6)

        with self.palette_lock:
            palette = self.color_palette

        for i in range(self.num_pixels):
            lo = int(self.freq_bins[i] / freq_per_bin)
            hi = int(self.freq_bins[i+1] / freq_per_bin)
            if hi <= lo:
                hi = lo + 1

            band_mag = np.mean(mags[lo:hi])
            b = band_mag / local_max
            c = palette[i % len(palette)]
            colors.append((int(c[0]*b), int(c[1]*b), int(c[2]*b)))

        return colors


if __name__ == "__main__":
    LED_COUNT = 50
    LED_PIN = board.D18
    COLOR_PALETTE = [(30, 124, 32), (182, 0, 0), (0, 55, 251), (223, 101, 0), (129, 0, 219)]
    pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)
    receiver = AudioVisualReceiver(pixels, COLOR_PALETTE, True)

    time.sleep(10)
    new_palette = [	(7,132,181), (202,222,239)]
    receiver.set_color_palette(new_palette)

    time.sleep(5)
    receiver.set_visualization_enabled(False)

    time.sleep(5)
    receiver.set_visualization_enabled(True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        receiver.running = False