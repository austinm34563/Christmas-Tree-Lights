
import neopixel
import board
from logger import Logger

logger = Logger()
TAG = "LightControl"

# LED strip configuration:
LED_COUNT  = 50          # Number of LED pixels.
LED_PIN    = board.D18   # GPIO pin connected to the pixels (18 uses PWM!).

class LightControl:
    def __init__(self, led_size):
        self.mLeds = neopixel.NeoPixel(LED_PIN, led_size, pixel_order=neopixel.RGB)

    def setColor(self, color):
        logger.info(TAG, "Setting color to " + str(hex(color)).upper())
        self.mLeds.fill(color)
        self.show()

    def show(self):
        self.mLeds.show()

if __name__ == '__main__':
    lights = LightControl(LED_COUNT)
    lights.setColor()
