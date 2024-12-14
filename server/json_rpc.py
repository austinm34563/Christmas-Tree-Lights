
from json import loads, dumps
from logger import Logger
from light_control import LightControl
from animation_constants import *
from animation import *
from music_sync import MusicSync
from enum import Enum
from song_scraper import *
from color_palettes import COLOR_PALETTES

# json-rpc commnd tags
METHOD_TAG = "method"
PARAMS_TAG = "params"
RESULT_TAG = "result"
ERROR_TAG = "error"
ERROR_MESSAGE_TAG = "message"
ERROR_CODE_TAG = "code"

# params tags
COLOR_TAG = "color"
PALLETE_TAG = "pallete"
SPEED_TAG = "speed"
COLOR_SCHEME_TAG = "color_scheme"
ANIMATION_EFFECT_ID_TAG = "animation_id"
SONG_ID_TAG = "song_id"
SONG_FILE_TAG = "file"

# error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
MUSIC_NOT_PLAYING_ERROR = -32000

# error messages
ERRROR_MESSAGES = {
    PARSE_ERROR : "Parse error",
    INVALID_REQUEST : "Invalid Request",
    METHOD_NOT_FOUND : "Method not found",
    INVALID_PARAMS : "Invalid params",
    MUSIC_NOT_PLAYING_ERROR : "No music is currently playing"
}

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
    AnimationId.Cylon.value: Cylon,
    AnimationId.RainbowWave.value: RainbowWave,
}

TAG = "JsonRpc"

class JsonRpc:
    def __init__(self):
        # todo add more commands
        self.mCommands = {
            "set_light" : self._set_light,
            "set_pallete" : self._set_pallete,
            "trigger_effect" : self._trigger_effect,
            "play_song" : self._play_song,
            "stop_song" : self._stop_song,
            "get_palettes" : self._get_palletes,
            "get_songs" : self._get_songs,
            "get_effects" : self._get_effects,
        }
        self.light_controller = LightControl()
        self.animation_controller = None
        self.music_sync = None

    def process_json(self, json_str):
        try:
            json_obj = loads(json_str)
        except:
            Logger.error(TAG, "Could not read json")
            return self._construct_error(PARSE_ERROR)

        if not self._validate_json(json_obj):
            return self._construct_error(INVALID_REQUEST)

        return self._call_command(json_obj[METHOD_TAG], json_obj[PARAMS_TAG])

    def _validate_json(self, json_obj):
        if not isinstance(json_obj, dict):
            Logger.error(TAG, "Invalid JSON dictionary.")
            return False

        for tag in VALID_TAGS:
            if json_obj.get(tag) is None:
                Logger.error(TAG, "Invalid JSON. Missing the following tag: ", tag)
                return False

        return True

    def _construct_error(self, code):
        return dumps(
            {
                ERROR_TAG:
                {
                    ERROR_CODE_TAG: code,
                    ERROR_MESSAGE_TAG: ERRROR_MESSAGES.get(code, "Unknown error")
                }
            }
        )

    def _construct_result(self, result):
        return dumps(
            {
                RESULT_TAG: result
            }
        )

    def _call_command(self, command, params):
        if self.mCommands.get(command) is None:
            Logger.error(TAG, "JSON-RPC command not found")
            return self._construct_error(METHOD_NOT_FOUND)

        return self.mCommands[command](params)

    def _validate_color_list(self, color_list, default_list):
        if color_list is None or len(color_list) == 0:
            Logger.warning(TAG, "Warning: no color list provided. Defaulting to Christmas theme.")
            color_list = default_list
        return color_list

    def _convert_hex_to_colors(self, color_list):
        return [
            ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF) if isinstance(color, int) else color
            for color in color_list
        ]

    def _set_light(self, params):
        Logger.info(TAG, "Calling set light")
        if params.get(COLOR_TAG) is None:
            Logger.error(TAG, "invalid color")
            return self._construct_error(INVALID_PARAMS)

        # stop any animations that are playing
        if self.animation_controller is not None:
            self.animation_controller.stop_animation()
            self.animation_controller = None

        if self.music_sync is not None:
            self.music_sync.stop_sync()
            self.music_sync = None

        self.light_controller.set_color(int(params.get(COLOR_TAG), 16))
        return self._construct_result(True)

    def _set_pallete(self, params):
        Logger.info(TAG, "Calling set pallete")
        if params.get(PALLETE_TAG) is None:
            Logger.error(TAG, "invalid pallete")
            return self._construct_error(INVALID_PARAMS)

        # stop any animation that are playing
        if self.animation_controller is not None:
            self.animation_controller.stop_animation()
            self.animation_controller = None

        if self.music_sync is not None:
            self.music_sync.stop_sync()
            self.music_sync = None

        color_pallete = params.get(PALLETE_TAG)
        color_pallete = self._validate_color_list(color_pallete, DEFAULT_COLOR_PALLETE)

        self.light_controller.set_color_pallete(color_pallete)
        return self._construct_result(True)

    def _trigger_effect(self, params):
        Logger.info(TAG, "Triggering some effect")
        effect_id = params.get(ANIMATION_EFFECT_ID_TAG)

        if effect_id is None:
            Logger.error(TAG, "animation effect id not found")
            return self._construct_error(INVALID_PARAMS)

        if effect_id not in AnimationId._value2member_map_:
            Logger.error(TAG, f"animation effect invalid: {effect_id}")
            return self._construct_error(INVALID_PARAMS)

        pixels = self.light_controller.get_pixels()
        pixel_count = self.light_controller.get_size()
        color_scheme = params.get(COLOR_SCHEME_TAG)

        if self.animation_controller is not None:
            self.animation_controller.stop_animation()

        if self.music_sync is not None:
            self.music_sync.stop_sync()
            self.music_sync = None

        # Set the default color scheme based on the animation effect
        color_scheme = self._validate_color_list(color_scheme, CANDLE_COLORS if effect_id == AnimationId.CandleFlicker.value else DEFAULT_COLOR_SCHEME)

        # convert to list of tuples if values are integers
        color_scheme = self._convert_hex_to_colors(color_scheme)

        # default speed to 1 if not defined
        speed = params.get(SPEED_TAG) if params.get(SPEED_TAG) is not None else 1

        # Instantiate the appropriate animation class
        if effect_id in effect_classes:
            self.animation_controller = effect_classes[effect_id](pixel_count, pixels, color_scheme, speed=speed)
        else:
            Logger.error(TAG, "No associated animation")
            return self._construct_error(INVALID_PARAMS)

        if self.animation_controller is None:
            Logger.error(TAG, "Could not run animation")
            return self._construct_error(INVALID_PARAMS)

        self.animation_controller.run_animation()
        return self._construct_result(True)

    def _play_song(self, params):
        song_id = params.get(SONG_ID_TAG)
        if song_id is None:
            Logger.error(TAG, "Song not provided")
            return self._construct_error(INVALID_PARAMS)

        color_pallete = self._validate_color_list(params.get(PALLETE_TAG), DEFAULT_COLOR_PALLETE)

        # convert to list of tuples if values are integers
        color_pallete = self._convert_hex_to_colors(color_pallete)

        if self.animation_controller is not None:
            self.animation_controller.stop_animation()

        if self.music_sync is not None:
            self.music_sync.stop_sync()

        pixels = self.light_controller.get_pixels()
        self.music_sync = MusicSync(pixels, get_mp3_metadata()[song_id][SONG_FILE_TAG], color_pallete)
        result = self.music_sync.start_sync()
        return self._construct_result(result)

    def _stop_song(self, params):
        if self.music_sync is None:
            return self._construct_error(MUSIC_NOT_PLAYING_ERROR)

        self.music_sync.stop_sync()
        self.music_sync = None
        return self._construct_result(True)

    def _get_songs(self, params):
        return self._construct_result(get_mp3_metadata())

    def _get_palletes(self, params):
        return self._construct_result(COLOR_PALETTES)

    def _get_effects(self, params):
        return self._construct_result(ANIMATIONS)

    # TODOs
    #  - Be able to query basic info (Animation ids, Music songs, Color palettes)
