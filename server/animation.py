
import neopixel
import time
import threading
import random
from logger import Logger
from animation_constants import CANDLE_COLORS
import math
import board

class Animation:
    def __init__(self, pixel_count, pixels, delay=0.01, speed=1):
        """
        Constructor for Animation class.

        :param pixel_count: Number of pixels on LEDs
        :param pixels: Pixel RGB data
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        self.pixel_count = pixel_count
        self.pixels = pixels  # Pre-initialized NeoPixel object
        self.delay = delay / speed
        self.last_update_time = time.monotonic()
        self.last_show_time = time.monotonic()
        self.show_interval = 1 / 60  # 60 FPS, ~16.67ms per frame
        self._stop_event = threading.Event()  # Event to signal the animation thread to stop
        self._thread = None
        self.TAG = "Animation"
        Logger.info(self.TAG, "Initialize Animation")
        if speed != 1:
            Logger.info(
                self.TAG,
                f"Speed is {speed}. Delay {'increased' if speed > 1 else 'decreased'} from {delay} to {self.delay}",
            )

    def __del__(self):
        """ Destructor of Animation object. """
        self.stop_animation()

    def _show(self):
        """ Throttled method to update LED state at 60 FPS. """
        current_time = time.monotonic()
        elapsed_time = current_time - self.last_show_time

        if elapsed_time >= self.show_interval:
            self.pixels.show()  # Call the NeoPixel show method
            self.last_show_time = current_time

    def _update_with_timing(self):
        """ Update call with timing tracked. """
        current_time = time.monotonic()
        elapsed_time = current_time - self.last_update_time

        # Check if enough time has passed to update the animation
        if elapsed_time >= self.delay:
            start_time = time.monotonic()  # Start timing for processing
            self._update()  # Call the specific update method
            end_time = time.monotonic()  # End timing for processing

            processing_time = (end_time - start_time) * 1000  # Processing time in milliseconds

            if processing_time > self.delay * 1000:
                Logger.warning(self.TAG, "Animation time budget exceeded")

            self.last_update_time = current_time

            return processing_time  # Return processing time in milliseconds
        return 0  # If no update occurred, return 0

    def run_animation(self):
        """ Runs animation loaded from constructor. """
        Logger.info(self.TAG, "Animation started")
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._animation_loop)
            self._thread.start()

    def stop_animation(self):
        """ Stops the animation if running. """
        Logger.info(self.TAG, "Animation stopped")
        self._stop_event.set()  # Signal the thread to stop
        if self._thread is not None:
            self._thread.join()  # Wait for the thread to finish
            self._thread = None

    def _animation_loop(self):
        """ Animation loop used for thread. """
        while not self._stop_event.is_set():
            self._update_with_timing()
            self._show()  # Ensure _show is throttled to 60 FPS

class CycleFade(Animation):
    def __init__(self, pixel_count, pixels, colors, steps=255, delay=0.01, speed=1):
        """
        Constructor for CycleFade class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.steps = steps
        self.current_brightness = 0
        self.fade_direction = 1  # 1 for increasing, -1 for decreasing
        self.current_color_index = 0  # Track current color index
        self.TAG = "CycleFade"
        Logger.info(self.TAG, "Loading the CycleFade animation")

    def _update(self):
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


class Fade(Animation):
    def __init__(self, pixel_count, pixels, colors, steps=255, delay=0.01, speed=1):
        """
        Constructor for Fade class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param steps: Number of steps used for fade animation.
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.steps = steps
        self.current_brightness = 0
        self.fade_direction = 1  # 1 for increasing, -1 for decreasing
        self.adjusted_colors = [(0, 0, 0)] * pixel_count  # Pre-allocate adjusted colors
        self.TAG = "Fade"
        Logger.info(self.TAG, "Loading the Fade animation")

    def _update(self):
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


class Blink(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.5, speed=1):
        """
        Constructor for Blink class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.current_color_index = 0
        self.TAG = "Blink"
        Logger.info(self.TAG, "Loading the Blink animation")

    def _update(self):
        current_color = self.colors[self.current_color_index]
        self.pixels[:] = [current_color] * self.pixel_count  # Set all pixels to the current color

        # Cycle to the next color
        self.current_color_index = (self.current_color_index + 1) % len(self.colors)


class Chase(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.1, speed=1, block_size=1):
        """
        Constructor for Chase class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        "param block_size: Specify the size of the chase block
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.index = 0
        self.block_size = block_size
        self.TAG = "Chase"
        Logger.info(self.TAG, "Loading the Chase animation")

        # Initialize strip with background color
        self.pixels.fill(self.colors[1])

        # Set initial block to chase color
        for i in range(self.block_size):
            self.pixels[i % self.pixel_count] = self.colors[0]

    def _update(self):
        # Clear the first pixel of the previous block
        self.pixels[self.index % self.pixel_count] = self.colors[1]

        # Set the new tail pixel of the block to the chase color
        new_tail = (self.index + self.block_size) % self.pixel_count
        self.pixels[new_tail] = self.colors[0]

        # Move the starting index for the next update
        self.index = (self.index + 1) % self.pixel_count


class TwinkleStars(Animation):
    def __init__(self, pixel_count, pixels, colors, twinkle_rate=0.05, delay=0.1, speed=1):
        """
        Constructor for TwinkleStars class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param twinkle_rate: Probability any pixel will "twinkle" on an update
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = [(color[0] / 2, color[1] / 2, color[2] / 2) for color in colors]  # The base color when not twinkling
        self.twinkle_color = 0xfff220  # The brighter twinkle color
        self.twinkle_rate = twinkle_rate  # Chance that any pixel will twinkle on an update
        for i in range(self.pixel_count):
            self.pixels[i] = self.colors[i % len(self.colors)]
        self.TAG = "TwinkleStars"
        Logger.info(self.TAG, "Loading the TwinkleStars animation")

    def _update(self):
        for i in range(self.pixel_count):
            if random.random() < self.twinkle_rate:
                # Make the pixel "twinkle" (switch to twinkle color)
                self.pixels[i] = self.twinkle_color
            else:
                # Restore pixel to base color
                self.pixels[i] = self.colors[i % len(self.colors)]


class CandleFlicker(Animation):
    def __init__(self, pixel_count, pixels, colors=None, delay=0.1, speed=1, min_brightness=0, max_brightness=1.0):
        """
        Constructor for CandleFlicker class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        :param min_brightness: Minimum brightness for flickering
        :param max_brightness: Maximum brightness for flickering
        """
        super().__init__(pixel_count, pixels, delay, speed)

        # Initialize the colors for each pixel
        self.colors = colors if colors else CANDLE_COLORS  # Default to a single candle color if none provided
        self.base_colors = [random.choice(self.colors) for _ in range(pixel_count)]  # Randomly choose base colors
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.last_brightness = [1.0] * pixel_count  # Track last brightness for smooth transitions

        self.TAG = "CandleFlicker"
        Logger.info(self.TAG, "Loading the CandleFlicker animation")

    def smooth_flicker(self):
        for i in range(len(self.last_brightness)):
            # Create a random target brightness within the specified range
            target_brightness = random.uniform(self.min_brightness, self.max_brightness)
            # Interpolate between the last brightness and the target brightness
            self.last_brightness[i] += (target_brightness - self.last_brightness[i]) * 0.3  # Smooth transition

    def _update(self):
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

class Bouncing(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.01, speed=1, block_size=25):
        """
        Constructor for Bouncing class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        :param block_size: Block size of the bouncing animation
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.block_size = block_size
        self.indexInner = pixel_count // 2 - block_size
        self.indexOutter = pixel_count // 2
        self.indexInnerMoveRight = False
        self.indexOutterMoveRight = True

        self.TAG = "Bouncing"
        Logger.info(self.TAG, "Loading the Bouncing animation")

    def _update(self):
        self.pixels.fill(self.colors[1])

        # Determine ranges for inner and outer blocks
        inner_start = max(0, int(self.indexInner))
        inner_end = min(self.pixel_count - 1, int(self.indexInner + self.block_size - 1))
        outer_start = max(0, int(self.indexOutter))
        outer_end = min(self.pixel_count - 1, int(self.indexOutter + self.block_size - 1))

        # Set pixels for inner and outer blocks
        self.pixels[inner_start:inner_end + 1] = [self.colors[0]] * (inner_end - inner_start + 1)
        self.pixels[outer_start:outer_end + 1] = [self.colors[0]] * (outer_end - outer_start + 1)

        # Calculate distance remaining for realistic speed adjustment
        distance_inner = abs(self.indexInner - (self.pixel_count // 2 - self.block_size))
        distance_outer = abs(self.indexOutter - (self.pixel_count // 2))

        # Smooth speed based on distance remaining (acceleration/deceleration effect)
        speed_factor_inner = 1.0 / (1 + distance_inner / (self.pixel_count / 2))
        speed_factor_outer = 1.0 / (1 + distance_outer / (self.pixel_count / 2))

        # Set move_amount based on speed factors
        move_amount_inner = 1.0 * speed_factor_inner
        move_amount_outer = 1.0 * speed_factor_outer

        # Update indices for bouncing
        self.indexInner += move_amount_inner if self.indexInnerMoveRight else -move_amount_inner
        self.indexOutter += move_amount_outer if self.indexOutterMoveRight else -move_amount_outer

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


class Twinkle(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.01, speed=1, seed=42, delta=1):
        """
        Constructor for Twinkle class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        :param seed: Random seed
        :param delta: Tracks change rate of brightness per pixel
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.seed = seed
        self.delta = delta
        self.mDelta = 0
        self.random_start_points = []
        self.TAG = "Twinkle"

        # Initialize the pseudo-random starting points for each pixel
        random.seed(self.seed)
        for _ in range(self.pixel_count):
            self.random_start_points.append(random.randint(0, 255))

    def _triwave8(self, x):
        return int(127.5 * (1 + math.sin(math.radians(x * 360 / 255))))

    def _dim8_lin(self, x):
        return int((x / 255) ** 2.5 * 255)

    def _update(self):
        for i in range(self.pixel_count):
            # Calculate brightness based on wave function and random starting point
            start_point = self.random_start_points[i]
            radians = (start_point + self.mDelta) % 255
            raw_brightness = self._triwave8(radians)
            brightness = self._dim8_lin(raw_brightness)

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

class TwinkleCycle(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.01, speed=1, seed=42, delta=1):
        """
        Constructor for TwinkleCycle class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        :param seed: Random seed
        :param delta: Tracks change rate of brightness per pixel
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.colors = colors
        self.seed = seed
        self.delta = delta
        self.mDelta = 0
        self.random_start_points = []
        self.color_indices = [random.randint(0, len(colors) - 1) for _ in range(pixel_count)]
        self.brightness_hit_zero = [False] * self.pixel_count
        self.TAG = "TwinkleCycle"

        # Initialize the pseudo-random starting points for each pixel
        random.seed(self.seed)
        for _ in range(self.pixel_count):
            self.random_start_points.append(random.randint(0, 255))

    def _triwave8(self, x):
        return int(127.5 * (1 + math.sin(math.radians(x * 360 / 255))))

    def _dim8_lin(self, x):
        return int((x / 255) ** 2.5 * 255)

    def _update(self):
        for i in range(self.pixel_count):
            # Calculate brightness based on wave function and random starting point
            start_point = self.random_start_points[i]
            radians = (start_point + self.mDelta) % 255
            raw_brightness = self._triwave8(radians)
            brightness = self._dim8_lin(raw_brightness)

            # If brightness is zero, move to the next color in the palette
            if brightness == 0 and not self.brightness_hit_zero[i]:
                self.color_indices[i] = (self.color_indices[i] + 1) % len(self.colors)
                self.brightness_hit_zero[i] = True
            elif brightness != 0 and self.brightness_hit_zero[i]:
                self.brightness_hit_zero[i] = False

            # Get the current color for this pixel
            color = self.colors[self.color_indices[i]]

            # Scale color by brightness
            scaled_color = (
                int(color[0] * brightness / 255),
                int(color[1] * brightness / 255),
                int(color[2] * brightness / 255)
            )

            # Set pixel color
            self.pixels[i] = scaled_color

        # Increment the delta for the next update
        self.mDelta += self.delta

class Cover(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.03, speed=1):
        """
        Constructor for Cover class.

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color scheme of animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.current_color_index = 0
        self.pixel_index = 0
        self.colors = colors
        self.TAG = "Cover"

    def _update(self):
        self.pixels[self.pixel_index] = self.colors[self.current_color_index]
        self.pixel_index += 1

        if self.pixel_index >= self.pixel_count:
            self.pixel_index = 0
            self.current_color_index += 1
            self.current_color_index %= len(self.colors)

class Cylon(Animation):
    def __init__(self, pixel_count, pixels, colors, delay=0.03, fade_amount=1.5, speed=1):
        """
        Constructor for Cylon class (Larson Scanner effect).

        :param pixel_count: Number of pixels on leds
        :param pixels: Pixel RGB data
        :param colors: Color palette for animation
        :param delay: Delay set between update calls. Defaults to 10ms delay (~100 FPS)
        :param fade_amount: Amount of fade for LEDs (0-255)
        :param speed: Speed rate relative to delay. (2.0 = double speed, 0.5 = half speed)
        """
        super().__init__(pixel_count, pixels, delay, speed)
        self.fade_amount = fade_amount
        self.position = 0
        self.reverse = False
        self.color_index = 0  # To track the current color in the palette
        self.colors = colors  # Store the color palette
        self.TAG = "Cylon"

    def _update(self):
        # Set the current LED to the color from the palette
        self.pixels[self.position] = self.colors[self.color_index]

        # Fade all LEDs
        for i in range(self.pixel_count):
            self.pixels[i] = self.fade(self.pixels[i], self.fade_amount)

        # Move the position back and forth
        if self.reverse:
            self.position -= 1
            if self.position < 0:
                self.position = 1
                self.reverse = False
        else:
            self.position += 1
            if self.position >= self.pixel_count:
                self.position = self.pixel_count - 2
                self.reverse = True

        # Cycle through colors in the palette
        self.color_index += 1
        if self.color_index >= len(self.colors):
            self.color_index = 0

    def fade(self, color, fade_amount):
        """
        Fades an RGB color by applying a fade amount.

        :param color: A tuple representing the RGB color (r, g, b)
        :param fade_amount: The fade amount (0-255)
        :return: The faded color (r, g, b)
        """
        r, g, b = color
        r = max(0, r - fade_amount)
        g = max(0, g - fade_amount)
        b = max(0, b - fade_amount)
        return (r, g, b)

if __name__ == "__main__":
    LED_COUNT  = 400         # Number of LED pixels.
    LED_PIN    = board.D18   # GPIO pin connected to the pixels (18 uses PWM!).
    pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    animation = Cylon(pixels.n, pixels, colors, speed=2)
    animation.run_animation()
