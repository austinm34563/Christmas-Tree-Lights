
import neopixel
import board
from logger import Logger

TAG = "LightControl"

# LED strip configuration:
LED_COUNT  = 200         # Number of LED pixels.
LED_PIN    = board.D18   # GPIO pin connected to the pixels (18 uses PWM!).

class LightControl:
    def __init__(self, led_size=LED_COUNT):
        self.leds = neopixel.NeoPixel(LED_PIN, led_size, pixel_order=neopixel.RGB, auto_write=False, brightness=1.0)

    def set_color(self, color):
        Logger.info(TAG, f"Setting color to {str(hex(color)).upper()}")
        self.leds.fill(color)
        self.show()

    def set_color_pallete(self, colors):
        Logger.info(TAG, f"Setting color palette with {len(colors)} colors for {LED_COUNT} LEDs.")

        # Log the color palette with indices
        for index, color in enumerate(colors):
            Logger.info(TAG, f"{index}: {str(hex(color)).upper()}")

        # Apply the colors to the LEDs, cycling through the palette if necessary
        for index in range(LED_COUNT):
            self.leds[index] = colors[index % len(colors)]

        # Show the updated LED states
        self.show()

    def show(self):
        self.leds.show()

    def get_pixels(self):
        return self.leds

    def get_size(self):
        return self.leds.n

if __name__ == '__main__':
    lights = LightControl()
    lights.set_color()
