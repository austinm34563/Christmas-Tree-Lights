import socket
import numpy as np
import sounddevice as sd
import threading
import time
import queue
import neopixel
import board
from logger import Logger
from visualization_info import (
    VisualizationnId,
    VISUALIZATIONS,
    VISUALIZATION_MAPPING,
)
from visualization import (
    Visualization,
    FftVisualization,
    WaveformVisualization,
    BeatVisualization,
    EnergyVisualization,
)

PI_PORT = 5005
SAMPLE_RATE = 44100
CHANNELS = 2
AUDIO_CHUNK_SIZE = 4096
AUDIO_CHUNK_BYTES = AUDIO_CHUNK_SIZE * CHANNELS * 2

VIS_CHUNK_SIZE = 1024

MIN_FREQ = 30
# MAX_FREQ = 20000
MAX_FREQ = 7902


class AudioVisualReceiver:
    def __init__(self, pixels, color_palette, enabled = False):
        self.tag = "AudioVisualReceiver"

        self.visualization_enabled = enabled
        self.visualization_lock = threading.Lock()

        # Networking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        # self.color_palette = color_palette
        self.num_pixels = len(pixels)
        self.palette_lock = threading.Lock()

        # Active visualization
        self.visualization_lock = threading.Lock()
        self._visualizer_lock = threading.Lock()

        self.visualizer = FftVisualization(
            num_pixels=self.num_pixels,
            sample_rate=SAMPLE_RATE,
            min_freq=MIN_FREQ,
            max_freq=MAX_FREQ,
        )

        # Queues
        self.audio_queue = queue.Queue(maxsize=256)
        self.led_queue = queue.Queue(maxsize=2)

        self.running = True

        # Start workers
        threading.Thread(target=self._connection_manager, daemon=True).start()
        threading.Thread(target=self._network_loop, daemon=True).start()
        threading.Thread(target=self._audio_loop, daemon=True).start()
        threading.Thread(target=self._led_worker, daemon=True).start()

        self.set_color_palette(color_palette)

    def set_visualization(self, visualizationId: int):
        """Switch visualization using its registered ID."""
        visualizationClass = VISUALIZATION_MAPPING.get(visualizationId)

        if visualizationClass is None:
            Logger.error(
                self.tag,
                f"Unknown visualization ID: {visualizationId}",
            )
            return

        visualization = visualizationClass(
            self.num_pixels,
            SAMPLE_RATE,
        )

        with self._visualizer_lock:
            visualization.reset()
            self.visualizer = visualization

        # Discard queued frames from the previous visualization.
        while True:
            try:
                self.led_queue.get_nowait()
            except queue.Empty:
                break

        Logger.info(
            self.tag,
            f"Visualization changed to {type(visualization).__name__}",
        )

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

            # Generate LED frames using the active visualization.
            for i in range(0, AUDIO_CHUNK_SIZE, VIS_CHUNK_SIZE):
                vis = pcm[i:i+VIS_CHUNK_SIZE]

                if len(vis) < VIS_CHUNK_SIZE:
                    vis = np.pad(vis, ((0, VIS_CHUNK_SIZE-len(vis)), (0,0)))

                # Convert stereo int16 PCM to normalized mono float32.
                mono = vis.mean(axis=1).astype(np.float32) / 32768.0

                with self._visualizer_lock:
                    visualizer = self.visualizer

                with self.palette_lock:
                    palette = list(self.color_palette)

                led_frame = visualizer.process(mono, palette)

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



if __name__ == "__main__":
    LED_COUNT = 50
    LED_PIN = board.D18

    COLOR_PALETTE = [
        (30, 124, 32),
        (182, 0, 0),
        (0, 55, 251),
        (223, 101, 0),
        (129, 0, 219),
    ]

    pixels = neopixel.NeoPixel(
        LED_PIN,
        LED_COUNT,
        pixel_order=neopixel.RGB,
        auto_write=False,
        brightness=1.0,
    )

    receiver = AudioVisualReceiver(
        pixels,
        COLOR_PALETTE,
        True,
    )

    # Build the interactive menu from visualization_info.py.
    visualizations_by_id = {
        str(info["id"]): (name, info)
        for name, info in VISUALIZATIONS.items()
    }

    def print_menu():
        print("\n========== Music-to-LED Visualizations ==========")

        for key, (name, info) in visualizations_by_id.items():
            print(f"\n  {key}. {name}")
            print(f"     {info['description']}")

        print("\n  q. Quit")
        print("=================================================")

    try:
        # Start with the original FFT visualization.
        receiver.set_visualization(VisualizationnId.FFT.value)

        print_menu()
        print("\nCurrent visualization: FFT")

        while True:
            choice = input(
                "\nSelect visualization (1-4, q to quit): "
            ).strip().lower()

            if choice == "q":
                break

            selection = visualizations_by_id.get(choice)

            if selection is None:
                print("Invalid selection. Enter 1, 2, 3, 4, or q.")
                continue

            name, info = selection

            receiver.set_visualization(info["id"])
            print(f"\nSwitched to: {name}")
            print(info["description"])

    except KeyboardInterrupt:
        print("\nStopping visualization...")

    finally:
        receiver.running = False

        # Close the network socket to unblock accept().
        receiver.sock.close()

        # Close the active client connection, if any.
        with receiver.conn_lock:
            if receiver.conn is not None:
                receiver.conn.close()
                receiver.conn = None
                receiver.connected = False

        receiver.stream.stop()
        receiver.stream.close()

        pixels.fill((0, 0, 0))
        pixels.show()

        print("Music-to-LED receiver stopped.")
