
from json import loads
from logger import Logger
from light_control import LightControl
from animation_constants import *
from animation import *

METHOD_TAG = "method"
PARAMS_TAG = "params"
COLOR_TAG = "color"
PALLETE_TAG = "pallete"
SPEED_TAG = "speed"
COLOR_SCHEME_TAG = "color_scheme"
ANIMATION_EFFECT_ID_TAG = "animation_id"

VALID_TAGS = [METHOD_TAG, PARAMS_TAG]

DEFAULT_COLOR_SCHEME = [(255, 0, 0), (0, 255, 0)]
DEFAULT_COLOR_PALLETE = [(30,124,32), (182,0,0), (0,55,251), (223,101,0), (129,0,219)]

# Map effects to their corresponding classes
effect_classes = {
    AnimationId.CycleFade.value: CycleFade,
    AnimationId.Fade.value: Fade,
    AnimationId.Blink.value: Blink,
    AnimationId.Chase.value: Chase,
    AnimationId.TwinkleStars.value: TwinkleStars,
    AnimationId.CandleFlicker.value: CandleFlicker,
    AnimationId.Bouncing.value: Bouncing,
    AnimationId.Twinkle.value: Twinkle,
    AnimationId.TwinkleCycle.value: TwinkleCycle,
    AnimationId.Cover.value: Cover,
}

logger = Logger()
TAG = "JsonRpc"

class JsonRpc:
    def __init__(self):
        # todo add more commands
        self.mCommands = {
            "set_light" : self._set_light,
            "set_pallete" : self._set_pallete,
            "trigger_effect" : self._trigger_effect,
        }
        self.mLightControl = LightControl()
        self.mAnimationControl = None

    def process_json(self, json_str):
        try:
            json_obj = loads(json_str)
        except:
            logger.error(TAG, "Error: Could not read json")
            return False

        if not self._validate_json(json_obj):
            return False

        self._call_command(json_obj[METHOD_TAG], json_obj[PARAMS_TAG])
        return True

    def _validate_json(self, json_obj):
        if not isinstance(json_obj, dict):
            logger.error(TAG, "Error: Invalid JSON dictionary.")
            return False

        for tag in VALID_TAGS:
            if json_obj.get(tag) is None:
                logger.error(TAG, "Error: Invalid JSON. Missing the following tag: ", tag)
                return False

        return True

    def _call_command(self, command, params):
        if self.mCommands.get(command) is None:
            logger.error(TAG, "Error: JSON-RPC command not found")
            return False

        self.mCommands[command](params)
        return True

    def _validate_color_list(self, color_list, default_list):
        if color_list is None or len(color_list) == 0:
            logger.warning(TAG, "Warning: no color list provided. Defaulting to Christmas theme.")
            color_list = default_list
        return color_list

    def _set_light(self, params):
        logger.info(TAG, "Calling set light")
        if params.get(COLOR_TAG) is None:
            logger.error(TAG, "Error: invalid color")
            return

        # stop any animations that are playing
        if self.mAnimationControl is not None:
            self.mAnimationControl.stop_animation()
            self.mAnimationControl = None

        self.mLightControl.setColor(int(params.get(COLOR_TAG), 16))

    def _set_pallete(self, params):
        logger.info(TAG, "Calling set pallete")
        if params.get(PALLETE_TAG) is None:
            logger.error(TAG, "Error: invalid pallete")
            return

        # stop any animation that are playing
        if self.mAnimationControl is not None:
            self.mAnimationControl.stop_animation()
            self.mAnimationControl = None

        if self.mAnimationControl is not None:
            self.mAnimationControl.stop_animation()

        color_pallete = params.get(PALLETE_TAG)
        color_pallete = self._validate_color_list(color_pallete, DEFAULT_COLOR_PALLETE)

        self.mLightControl.setColorPallete(color_pallete)

    def _trigger_effect(self, params):
        logger.info(TAG, "Triggering some effect")
        effect_id = params.get(ANIMATION_EFFECT_ID_TAG)

        if effect_id is None:
            logger.error(TAG, "Error: animation effect id not found")
            return

        if effect_id not in AnimationId._value2member_map_:
            logger.error(TAG, f"Error: animation effect invalid: {effect_id}")
            return

        pixels = self.mLightControl.get_pixels()
        pixel_count = self.mLightControl.get_size()
        color_scheme = params.get(COLOR_SCHEME_TAG)

        if self.mAnimationControl is not None:
            self.mAnimationControl.stop_animation()

        # Set the default color scheme based on the animation effect
        color_scheme = self._validate_color_list(color_scheme, CANDLE_COLORS if effect_id == AnimationId.CandleFlicker.value else DEFAULT_COLOR_SCHEME)

        # convert to list of tuples if values are integers
        color_scheme = [
            ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF) if isinstance(color, int) else color
            for color in color_scheme
        ]

        # default speed to 1 if not defined
        speed = params.get(SPEED_TAG) if params.get(SPEED_TAG) is not None else 1

        # Instantiate the appropriate animation class
        if effect_id in effect_classes:
            self.mAnimationControl = effect_classes[effect_id](pixel_count, pixels, color_scheme, speed=speed)
        else:
            logger.error(TAG, "Error: No associated animation")
            return

        if self.mAnimationControl is not None:
            self.mAnimationControl.run_animation()
        else:
            logger.error(TAG, "Error: Could not run animation")

    # TODOs
    #  - Be able to query basic info (Animation ids, Music songs, Color palettes)
