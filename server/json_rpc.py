
from json import loads, dumps
from logger import Logger
from light_control import LightControl
from animation_constants import *
from animation import *
from music_sync import MusicSync
from animation_playlist import AnimationPlaylist
from enum import Enum
from song_scraper import *
from color_palettes import COLOR_PALETTES, CHRISTMAS_TREE_PALLETE

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
ANIMATIONS_TAG = "animations"
COLOR_SCHEMES_TAG = "color_schemes"
PLAYLIST_TIME_DELAY_TAG = "time_delay"

# error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
MUSIC_NOT_PLAYING_ERROR = -32000
ANIMATION_PLAYLIST_NOT_PLAYING_ERROR = -32001

# error messages
ERRROR_MESSAGES = {
    PARSE_ERROR : "Parse error",
    INVALID_REQUEST : "Invalid Request",
    METHOD_NOT_FOUND : "Method not found",
    INVALID_PARAMS : "Invalid params",
    MUSIC_NOT_PLAYING_ERROR : "No music is currently playing",
    ANIMATION_PLAYLIST_NOT_PLAYING_ERROR : "No animation playlist is currently playing"
}

VALID_TAGS = [METHOD_TAG, PARAMS_TAG]

DEFAULT_COLOR_SCHEME = [(255, 0, 0), (0, 255, 0)]
DEFAULT_COLOR_PALLETE = [(30,124,32), (182,0,0), (0,55,251), (223,101,0), (129,0,219)]
DEFAULT_PLAYLIST_TIME_DELAY = 120 # 2 minutes of delay

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
            "start_animation_playlist" : self._start_playlist,
            "stop_animation_playlist" : self._stop_playlist,
            "get_palettes" : self._get_palletes,
            "get_songs" : self._get_songs,
            "get_effects" : self._get_effects,
        }
        self.light_controller = LightControl()
        self.animation_controller = None
        self.music_sync = None
        self.animation_playlist = None

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

        self._generic_teardown()
        self.light_controller.set_color(int(params.get(COLOR_TAG), 16))
        return self._construct_result(True)

    def _set_pallete(self, params):
        Logger.info(TAG, "Calling set pallete")
        if params.get(PALLETE_TAG) is None:
            Logger.error(TAG, "invalid pallete")
            return self._construct_error(INVALID_PARAMS)

        self._generic_teardown()

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

        self._generic_teardown()

        # Set the default color scheme based on the animation effect
        color_scheme = self._validate_color_list(color_scheme, DEFAULT_COLOR_SCHEME)

        # convert to list of tuples if values are integers
        color_scheme = self._convert_hex_to_colors(color_scheme)

        # default speed to 1 if not defined
        speed = params.get(SPEED_TAG, 1)

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

        self._generic_teardown()

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

    def _start_playlist(self, params):
        animations_id = params.get(ANIMATIONS_TAG)
        if animations_id is None:
            Logger.error(TAG, "No animations provided")
            return self._construct_error(INVALID_PARAMS)

        color_schemes_id = params.get(COLOR_SCHEMES_TAG)
        if color_schemes_id is None:
            Logger.error(TAG, "No color schemes provided")
            return self._construct_error(INVALID_PARAMS)

        animations = []
        speeds = []
        for animation in animations_id:
            animation_id = animation.get(ANIMATION_EFFECT_ID_TAG)
            speed = animation.get(SPEED_TAG, 1.0)
            if animation_id is None:
                Logger.warning(TAG, "Invalid animation provided. Skipping from playlist")
                continue
            animations.append(animation_id)
            speeds.append(speed)

        color_schemes = []
        for color_scheme in color_schemes_id:
            color_scheme = self._validate_color_list(color_scheme, DEFAULT_COLOR_PALLETE)
            color_scheme = self._convert_hex_to_colors(color_scheme)
            color_schemes.append(color_scheme)

        self._generic_teardown()

        pixels = self.light_controller.get_pixels()
        time_delay = params.get(PLAYLIST_TIME_DELAY_TAG, DEFAULT_PLAYLIST_TIME_DELAY)
        self.animation_playlist = AnimationPlaylist(pixels, animations, color_schemes, speeds, time_delay)
        self.animation_playlist.start_playlist()
        return self._construct_result(True)

    def _stop_playlist(self, params):
        if self.animation_playlist is None:
            return self._construct_error(ANIMATION_PLAYLIST_NOT_PLAYING_ERROR)
        self.animation_playlist.stop_playlist()
        self.animation_playlist = None

        # now that is stopped display a default palette
        self.light_controller.set_color_pallete(CHRISTMAS_TREE_PALLETE)

        return self._construct_result(True)

    def _get_songs(self, params):
        return self._construct_result(get_mp3_metadata())

    def _get_palletes(self, params):
        return self._construct_result(COLOR_PALETTES)

    def _get_effects(self, params):
        return self._construct_result(ANIMATIONS)

    def _generic_teardown(self):
        if self.animation_controller is not None:
            self.animation_controller.stop_animation()
            self.animation_controller = None

        if self.music_sync is not None:
            self.music_sync.stop_sync()
            self.music_sync = None

        if self.animation_playlist is not None:
            self.animation_playlist.stop_playlist()
            self.animation_playlist = None
