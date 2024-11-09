
import neopixel
import time
import threading
import random
from logger import Logger
from animation_constants import CANDLE_COLORS
import math
import board

logger = Logger()

class Animation:
    def __init__(self, pixel_count, pixels, delay=0.01):
        self.pixel_count = pixel_count
        self.pixels = pixels  # Now accept a pre-initialized NeoPixel object
        self.delay = delay
        self.last_update_time = time.monotonic()
        self._stop_event = threading.Event()  # Event to signal the animation thread to stop
        self._thread = None
        self.TAG = "Animation"
        logger.info(self.TAG, "Initialize Animation")

    def __del__(self):
        self.stop_animation()

    def show(self):
        self.pixels.show()  # Call the NeoPixel show method

    def _update_with_timing(self):
        current_time = time.monotonic()
        elapsed_time = current_time - self.last_update_time

        # Check if enough time has passed to update the animation
        if elapsed_time >= self.delay:
            start_time = time.monotonic()  # Start timing for processing
            self.update()  # Call the specific update method
            end_time = time.monotonic()  # End timing for processing

            processing_time = (end_time - start_time) * 1000  # Processing time in milliseconds

            if processing_time > self.delay * 1000:
                logger.warning(self.TAG, "Animation time budget exceeded")

            self.last_update_time = current_time

            return processing_time  # Return processing time in milliseconds
        return 0  # If no update occurred, return 0

    def run_animation(self):
        logger.info(self.TAG, "Animation started")
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._animation_loop)
            self._thread.start()

    def stop_animation(self):
        logger.info(self.TAG, "Animation stopped")
        self._stop_event.set()  # Signal the thread to stop
        if self._thread is not None:
            self._thread.join()  # Wait for the thread to finish
            self._thread = None

    def _animation_loop(self):
        while not self._stop_event.is_set():
            self._update_with_timing()
            time.sleep(self.delay)  # Ensure the thread sleeps to avoid overloading the CPU


class CycleFade(Animation):
    def __init__(self, pixel_count, pixels, colors, steps=255, delay=0.01):
        super().__init__(pixel_count, pixels, delay)
        self.colors = colors
        self.steps = steps
        self.current_brightness = 0
        self.fade_direction = 1  # 1 for increasing, -1 for decreasing
        self.current_color_index = 0  # Track current color index
        self.TAG = "CycleFade"
        logger.info(self.TAG, "Loading the CycleFade animation")

    def update(self):
        # Update brightness
        self.current_brightness += self.fade_direction

        # Reverse direction if at the limits
        if self.current_brightness >= self.steps:
            self.current_brightness = self.steps
            self.fade_direction = -1
        elif self.current_brightness <= 0:
            self.current_brightness = 0
            self.fade_direction = 1
            # Move to the next color in the list
            self.current_color_index = (self.current_color_index + 1) % len(self.colors)

        # Get the current color
        current_color = self.colors[self.current_color_index]

        # Set the pixel color based on the current brightness
        self.pixels.fill((
            int(current_color[0] * self.current_brightness / self.steps),
            int(current_color[1] * self.current_brightness / self.steps),
            int(current_color[2] * self.current_brightness / self.steps)
        ))
        self.show()


class Fade(Animation):
    def __init__(self, pixel_count, pixels, colors, steps=255, delay=0.01):
        super().__init__(pixel_count, pixels, delay)
        self.colors = colors
        self.steps = steps
        self.current_brightness = 0
        self.fade_direction = 1  # 1 for increasing, -1 for decreasing
        self.adjusted_colors = [(0, 0, 0)] * pixel_count  # Pre-allocate adjusted colors
        self.TAG = "Fade"
        logger.info(self.TAG, "Loading the Fade animation")

    def update(self):
        """Perform a fade in and fade out animation, cycling through the pixel colors."""
        # Update the brightness
        self.current_brightness += self.fade_direction

        if self.current_brightness >= self.steps:
            self.current_brightness = self.steps
            self.fade_direction = -1
        elif self.current_brightness <= 0:
            self.current_brightness = 0
            self.fade_direction = 1
            # Rotate the colors
            self.colors.append(self.colors.pop(0))  # Shift colors by 1

        # Calculate adjusted colors only if brightness changed
        for i in range(self.pixel_count):
            color_index = i % len(self.colors)
            base_color = self.colors[color_index]
            # Calculate the adjusted color and store it
            self.adjusted_colors[i] = (
                int(base_color[0] * self.current_brightness / self.steps),
                int(base_color[1] * self.current_brightness / self.steps),
                int(base_color[2] * self.current_brightness / self.steps)
            )

        # Set the pixel colors in one go
        self.pixels[:] = self.adjusted_colors
        self.show()


class Blink(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.5):
        super().__init__(pixel_count, pixels, delay)
        self.colors = colors
        self.current_color_index = 0
        self.TAG = "Blink"
        logger.info(self.TAG, "Loading the Blink animation")

    def update(self):
        current_color = self.colors[self.current_color_index]
        self.pixels[:] = [current_color] * self.pixel_count  # Set all pixels to the current color
        self.show()

        # Cycle to the next color
        self.current_color_index = (self.current_color_index + 1) % len(self.colors)


class Chase(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.1, block_size=1):
        super().__init__(pixel_count, pixels, delay)
        self.colors = colors
        self.index = 0
        self.block_size = block_size
        self.TAG = "Chase"
        logger.info(self.TAG, "Loading the Chase animation")

    def update(self):
        # Fill the entire strip with the background color (colors[1])
        self.pixels.fill(self.colors[1])

        # Set the block of pixels to the chase color (colors[0])
        for i in range(self.block_size):
            # Use modulo to wrap the index around if it exceeds pixel_count
            self.pixels[(self.index + i) % self.pixel_count] = self.colors[0]

        # Move the starting index for the next update
        self.index += 1
        if self.index >= self.pixel_count:
            self.index = 0

        self.show()


class TwinkleStars(Animation):
    def __init__(self, pixel_count, pixels, colors, twinkle_rate=0.05, delay=0.1):
        super().__init__(pixel_count, pixels, delay)
        self.base_color = colors[0]  # The base color when not twinkling
        self.twinkle_color = colors[1]  # The brighter twinkle color
        self.twinkle_rate = twinkle_rate  # Chance that any pixel will twinkle on an update
        self.pixels.fill(self.base_color)  # Initialize all pixels to the base color
        self.TAG = "TwinkleStars"
        logger.info(self.TAG, "Loading the TwinkleStars animation")

    def update(self):
        for i in range(self.pixel_count):
            if random.random() < self.twinkle_rate:
                # Make the pixel "twinkle" (switch to twinkle color)
                self.pixels[i] = self.twinkle_color
            else:
                # Restore pixel to base color
                self.pixels[i] = self.base_color

        self.show()


class CandleFlicker(Animation):
    def __init__(self, pixel_count, pixels, colors=None, delay=0.1, min_brightness=0, max_brightness=1.0):
        super().__init__(pixel_count, pixels, delay)

        # Initialize the colors for each pixel
        self.colors = colors if colors else CANDLE_COLORS  # Default to a single candle color if none provided
        self.base_colors = [random.choice(self.colors) for _ in range(pixel_count)]  # Randomly choose base colors
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.last_brightness = [1.0] * pixel_count  # Track last brightness for smooth transitions

        self.TAG = "CandleFlicker"
        logger.info(self.TAG, "Loading the CandleFlicker animation")

    def smooth_flicker(self):
        for i in range(len(self.last_brightness)):
            # Create a random target brightness within the specified range
            target_brightness = random.uniform(self.min_brightness, self.max_brightness)
            # Interpolate between the last brightness and the target brightness
            self.last_brightness[i] += (target_brightness - self.last_brightness[i]) * 0.3  # Smooth transition

    def update(self):
        self.smooth_flicker()  # Update brightness values smoothly

        current_colors = []  # Create a new list for the current colors
        for i, base_color in enumerate(self.base_colors):
            # Apply brightness to the selected base color
            flickered_color = (
                int(base_color[0] * self.last_brightness[i]),
                int(base_color[1] * self.last_brightness[i]),
                int(base_color[2] * self.last_brightness[i])
            )
            current_colors.append(flickered_color)  # Append the flickered color to the list

        # Set all pixel colors in one go
        self.pixels[:] = current_colors
        self.show()  # Update the NeoPixel strip


class Bouncing(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.01, block_size=5):
        super().__init__(pixel_count, pixels, delay)
        self.colors = colors
        self.block_size = block_size
        self.indexInner = pixel_count // 2 - block_size
        self.indexOutter = pixel_count // 2
        self.indexInnerMoveRight = False
        self.indexOutterMoveRight = True

        self.TAG = "Bouncing"
        logger.info(self.TAG, "Loading the Bouncing animation")

    def update(self):
        self.pixels.fill(self.colors[1])

        # Determine ranges for inner and outer blocks
        inner_start = max(0, int(self.indexInner))
        inner_end = min(self.pixel_count - 1, int(self.indexInner + self.block_size - 1))
        outer_start = max(0, int(self.indexOutter))
        outer_end = min(self.pixel_count - 1, int(self.indexOutter + self.block_size - 1))

        # Set pixels for inner and outer blocks
        self.pixels[inner_start:inner_end + 1] = [self.colors[0]] * (inner_end - inner_start + 1)
        self.pixels[outer_start:outer_end + 1] = [self.colors[0]] * (outer_end - outer_start + 1)

        # Calculate distance and movement speeds
        distance = self.indexOutter - (self.indexInner + self.block_size)
        speed_factor = max(1, abs(distance) // 2)
        move_amount = 1.0 / speed_factor if distance > 0 else speed_factor

        # Update indices for bouncing
        self.indexInner += move_amount if self.indexInnerMoveRight else -move_amount
        self.indexOutter += move_amount if self.indexOutterMoveRight else -move_amount

        # Boundary conditions for inner block
        if self.indexInner <= 0:
            self.indexInnerMoveRight = True
        elif self.indexInner >= (self.pixel_count // 2 - self.block_size):
            self.indexInnerMoveRight = False

        # Boundary conditions for outer block
        if self.indexOutter >= self.pixel_count - self.block_size:
            self.indexOutterMoveRight = False
        elif self.indexOutter <= (self.pixel_count // 2):
            self.indexOutterMoveRight = True

        # Ensure outer block does not overlap with inner block
        if self.indexOutter <= self.indexInner + self.block_size:
            self.indexOutterMoveRight = True  # Change direction if they overlap

        self.show()

class Twinkle(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.01, seed=42, delta=1):
        super().__init__(pixel_count, pixels, delay)
        self.pixels = pixels
        self.num_pixels = pixel_count
        self.colors = colors
        self.seed = seed
        self.delta = delta
        self.mDelta = 0
        self.random_start_points = []
        self.TAG = "Twinkle"

        # Initialize the pseudo-random starting points for each pixel
        random.seed(self.seed)
        for _ in range(self.num_pixels):
            self.random_start_points.append(random.randint(0, 255))

    def triwave8(self, x):
        """Approximate FastLED's triwave8 function using a sine wave."""
        return int(127.5 * (1 + math.sin(math.radians(x * 360 / 255))))

    def dim8_lin(self, x):
        """Approximate FastLED's dimming function."""
        return int((x / 255) ** 2.5 * 255)

    def update(self):
        for i in range(self.num_pixels):
            # Calculate brightness based on wave function and random starting point
            start_point = self.random_start_points[i]
            radians = (start_point + self.mDelta) % 255
            raw_brightness = self.triwave8(radians)
            brightness = self.dim8_lin(raw_brightness)

            # Scale color by brightness
            color = self.colors[i % len(self.colors)]
            scaled_color = (
                int(color[0] * brightness / 255),
                int(color[1] * brightness / 255),
                int(color[2] * brightness / 255)
            )

            # Set pixel color
            self.pixels[i] = scaled_color

        # Increment the delta for the next update
        self.mDelta += self.delta
        self.pixels.show()

# main method below can be used to test animations
# if __name__ == '__main__':
#     pixel_count = 100  # Number of LEDs
#     pin = board.D18   # Pin where the LED strip is connected
#     DEFAULT_COLOR_SCHEME = [(255, 0, 0), (0, 255, 0)]
#     pixels = neopixel.NeoPixel(pin, pixel_count, pixel_order=neopixel.RGB, auto_write=False)
#     animation = Twinkle(pixel_count, pixels, DEFAULT_COLOR_SCHEME, delay=0.01)
#     animation.run_animation()
