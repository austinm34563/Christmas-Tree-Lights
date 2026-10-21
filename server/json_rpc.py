
from json import loads, dumps
from random import choice
from alsaaudio import Mixer
from logger import Logger
from light_control import LightControl
from animation_constants import *
from animation import *
from animation_playlist import AnimationPlaylist, AnimationPlaylistData
from animation_playlist_manager import AnimationPlaylistManager
from enum import Enum
from color_palette_manager import ColorPaletteManager, ColorPaletteReturnStatus
from tcp_audio_sync import AudioVisualReceiver

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
PALETTES_TAG = "palettes"
PALETTE_COLORS_TAG = "palette_colors"
SPEED_TAG = "speed"
COLOR_SCHEME_TAG = "color_scheme"
ANIMATION_EFFECT_ID_TAG = "animation_id"
ANIMATION_NAME_TAG = "animation_name"
ANIMATIONS_TAG = "animations"
COLOR_SCHEMES_TAG = "color_schemes"
PLAYLIST_TIME_DELAY_TAG = "time_delay"
URL_TAG = "url"
VOLUME_TAG = "volume"
LED_COUNT_TAG = "led_count"
IS_ENABLED_TAG = "is_enabled"
PLAYLIST_NAME_TAG = "playlist_name"

# error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
MUSIC_NOT_PLAYING_ERROR = -32000
ANIMATION_PLAYLIST_NOT_PLAYING_ERROR = -32001
MODIFY_DEFAULT_PALETTE_ERROR = -32002
UNKNOWN_ERROR = -32003

# error messages
ERRROR_MESSAGES = {
    PARSE_ERROR : "Parse error",
    INVALID_REQUEST : "Invalid Request",
    METHOD_NOT_FOUND : "Method not found",
    INVALID_PARAMS : "Invalid params",
    MUSIC_NOT_PLAYING_ERROR : "No music is currently playing",
    ANIMATION_PLAYLIST_NOT_PLAYING_ERROR : "No animation playlist is currently playing",
    MODIFY_DEFAULT_PALETTE_ERROR : "Cannot modify a default palette",
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
            "start_animation_playlist" : self._start_playlist,
            "stop_animation_playlist" : self._stop_playlist,
            "audio_sync_is_enabled" : self._set_audio_sync_is_enabled,
            "set_volume" : self._set_volume,
            "set_led_count" : self._set_led_count,
            "get_volume" : self._get_volume,
            "get_palettes" : self._get_palletes,
            "get_effects" : self._get_effects,
            "get_audio_sync_state": self._get_audio_sync_state,
            "add_palette": self._add_color_palette,
            "remove_palette": self._remove_color_palette,
            "add_animation_playlist" : self._add_playlist,
            "remove_animation_playlist" : self._remove_playlist,
            "get_playlists" : self._get_playlists,
        }
        self.light_controller = LightControl()
        self.animation_controller = None
        self.animation_playlist = None
        self.volume_mixer = Mixer()
        self.audio_visual_receiver = AudioVisualReceiver(self.light_controller.get_pixels(), DEFAULT_COLOR_PALLETE)
        self.color_palette_manager = ColorPaletteManager()
        self.animation_playlist_manager = AnimationPlaylistManager()

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

    def _set_light(self, params):
        Logger.info(TAG, "Calling set light")
        if params.get(COLOR_TAG) is None:
            Logger.error(TAG, "invalid color")
            return self._construct_error(INVALID_PARAMS)

        self._generic_teardown()
        color = int(params.get(COLOR_TAG), 16)
        if self.audio_visual_receiver.is_enabled():
            self.audio_visual_receiver.set_color_palette([color])
        else:
            self.light_controller.set_color(color)
        return self._construct_result(True)

    def _set_pallete(self, params):
        Logger.info(TAG, "Calling set pallete")
        if params.get(PALLETE_TAG) is None:
            Logger.error(TAG, "invalid pallete")
            return self._construct_error(INVALID_PARAMS)

        self._generic_teardown()

        color_pallete = params.get(PALLETE_TAG)
        color_pallete = self._validate_color_list(color_pallete, DEFAULT_COLOR_PALLETE)

        if self.audio_visual_receiver.is_enabled():
            self.audio_visual_receiver.set_color_palette(color_pallete)
        else:
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

        # default speed to 1 if not defined
        speed = params.get(SPEED_TAG, 1)

        # Instantiate the appropriate animation class
        if effect_id in EFFECTS:
            self.animation_controller = EFFECTS[effect_id](pixel_count, pixels, color_scheme, speed=speed)
        else:
            Logger.error(TAG, "No associated animation")
            return self._construct_error(INVALID_PARAMS)

        if self.animation_controller is None:
            Logger.error(TAG, "Could not run animation")
            return self._construct_error(INVALID_PARAMS)

        self.animation_controller.run_animation()
        return self._construct_result(True)

    def _start_playlist(self, params):
        playlist_name = params.get(PLAYLIST_NAME_TAG)
        if playlist_name is None:
            Logger.error(TAG, "No playlist provided")
            return self._construct_error(INVALID_PARAMS)

        playlists = self.animation_playlist_manager.get_playlists()
        playlist = playlists.get(playlist_name)
        if playlist is None:
            Logger.error(TAG, "Invalid playlist provided")
            return self._construct_error(INVALID_PARAMS)
        self._generic_teardown()

        pixels = self.light_controller.get_pixels()
        time_delay = params.get(PLAYLIST_TIME_DELAY_TAG, DEFAULT_PLAYLIST_TIME_DELAY)
        self.animation_playlist = AnimationPlaylist(pixels, AnimationPlaylistData(**playlist), time_delay)
        self.animation_playlist.start_playlist()
        return self._construct_result(True)

    def _stop_playlist(self, params):
        if self.animation_playlist is None:
            return self._construct_error(ANIMATION_PLAYLIST_NOT_PLAYING_ERROR)
        self.animation_playlist.stop_playlist()
        self.animation_playlist = None

        # now that is stopped display a the last palette
        if not self.light_controller.reset_palette():
            Logger.warning(TAG, "Using a random color palette")
            random_palette = choice(list(self.color_palette_manager.get_color_palettes().values()))
            self.light_controller.set_color_pallete(random_palette)

        return self._construct_result(True)

    def _add_playlist(self, params):
        playlist_name = params.get(PLAYLIST_NAME_TAG)
        if playlist_name is None:
            Logger.error(TAG, "No playlist name provided")
            return self._construct_error(INVALID_PARAMS)

        animations_id = params.get(ANIMATIONS_TAG)
        if animations_id is None:
            Logger.error(TAG, "No animations provided")
            return self._construct_error(INVALID_PARAMS)

        palette_names = params.get(PALETTES_TAG)
        if palette_names is None:
            Logger.error(TAG, "No color schemes provided")
            return self._construct_error(INVALID_PARAMS)

        animations = []
        speeds = []
        for animation in animations_id:
            animation_name = animation.get(ANIMATION_NAME_TAG)
            if animation_name is None:
                Logger.warning(TAG, "Invalid animation provided. Skipping from playlist")
                continue
            animations.append(animation_name)
            speeds.append(animation.get(SPEED_TAG, 1.0))

        self.animation_playlist_manager.add(playlist_name, AnimationPlaylistData(animations, palette_names, speeds))
        return self._construct_result(True)

    def _remove_playlist(self, params):
        playlist_name = params.get(PLAYLIST_NAME_TAG)
        if playlist_name is None:
            Logger.error(TAG, "No playlist provided")
            return self._construct_error(INVALID_PARAMS)
        self.animation_playlist_manager.remove(playlist_name)
        return self._construct_result(True)


    def _set_audio_sync_is_enabled(self, params):
        is_enabled = params.get(IS_ENABLED_TAG)
        if is_enabled is None:
            Logger.error(TAG, "No audio sync enablement flag provided")
            return self._construct_error(INVALID_PARAMS)
        self._generic_teardown()
        self.audio_visual_receiver.set_visualization_enabled(is_enabled)
        return self._construct_result(True)

    def _add_color_palette(self, params):
        palette_name = params.get(PALLETE_TAG)
        if palette_name is None:
            Logger.error(TAG, "No palette name provided")
            return self._construct_error(INVALID_PARAMS)

        palette_colors = params.get(PALETTE_COLORS_TAG)
        if palette_colors is None:
            Logger.error(TAG, "Palette colors not provided")
            return self._construct_error(INVALID_PARAMS)

        err = self.color_palette_manager.add(palette_name, palette_colors)
        match err:
            case ColorPaletteReturnStatus.OK:
                return self._construct_result(True)
            case ColorPaletteReturnStatus.MODIFIED_DEFAULT_ERR:
                return self._construct_error(MODIFY_DEFAULT_PALETTE_ERROR)
            case _:
                return self._construct_result(UNKNOWN_ERROR)

    def _remove_color_palette(self, params):
        palette_name = params.get(PALLETE_TAG)
        if palette_name is None:
            Logger.error(TAG, "No palette name provided")
            return self._construct_error(INVALID_PARAMS)

        err = self.color_palette_manager.remove(palette_name)
        match err:
            case ColorPaletteReturnStatus.OK:
                return self._construct_result(True)
            case ColorPaletteReturnStatus.MODIFIED_DEFAULT_ERR:
                return self._construct_error(MODIFY_DEFAULT_PALETTE_ERROR)
            case _:
                return self._construct_result(UNKNOWN_ERROR)

    def _set_volume(self, params):
        volume_percentage = params.get(VOLUME_TAG)
        if volume_percentage is None:
            Logger.error(TAG, "Invalid params")
            return self._construct_error(INVALID_PARAMS)

        self.volume_mixer.setvolume(volume_percentage)
        return self._construct_result(True)

    def _set_led_count(self, params):
        led_count = params.get(LED_COUNT_TAG)
        if led_count is None:
            Logger.error(TAG, "Invalid params")
            return self._construct_error(INVALID_PARAMS)

        if self.light_control.get_size() != led_count:
            self.light_controller = LightControl(led_count)
        return self._construct_result(True)

    def _get_volume(self, params):
        volume_result = {
            VOLUME_TAG : self.volume_mixer.getvolume()[0]
        }
        return self._construct_result(volume_result)

    def _get_palletes(self, params):
        return self._construct_result(self.color_palette_manager.get_color_palettes())

    def _get_effects(self, params):
        return self._construct_result(ANIMATIONS)

    def _get_audio_sync_state(self, params):
        return self._construct_result(self.audio_visual_receiver.is_enabled())

    def _get_playlists(self, params):
        return self._construct_result(self.animation_playlist_manager.get_playlists())

    def _generic_teardown(self):
        if self.animation_controller is not None:
            self.animation_controller.stop_animation()
            self.animation_controller = None

        if self.animation_playlist is not None:
            self.animation_playlist.stop_playlist()
            self.animation_playlist = None
