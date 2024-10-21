
import neopixel
import board
from logger import Logger

logger = Logger()
TAG = "LightControl"

# LED strip configuration:
LED_COUNT  = 50          # Number of LED pixels.
LED_PIN    = board.D18   # GPIO pin connected to the pixels (18 uses PWM!).

class LightControl:
    def __init__(self, led_size=LED_COUNT):
        self.mLeds = neopixel.NeoPixel(LED_PIN, led_size, pixel_order=neopixel.RGB, auto_write=False)

    def setColor(self, color):
        logger.info(TAG, "Setting color to " + str(hex(color)).upper())
        self.mLeds.fill(color)
        self.show()

    def show(self):
        self.mLeds.show()

    def get_pixels(self):
        return self.mLeds

    def get_size(self):
        return self.mLeds.n

if __name__ == '__main__':
    lights = LightControl()
    lights.setColor()
