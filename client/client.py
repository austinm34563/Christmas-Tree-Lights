import socket
import json
from time import sleep
from enum import Enum
import subprocess
import signal
import os


HOST = 'raspberrypi.local'  # Replace with the Raspberry Pi's IP address on the Wi-Fi network
PORT = 65432          # The port used by the server

CHRISTMAS_PALETTES = {}
ANIMATION_OPTIONS = {}
VOLUME_STATE = 100 # initial value

_ffmpeg_proc = None

class CachedId(Enum):
    VOLUME_STATE=1
    PALLETES=2
    ANIMATION_EFFECTS=3
    NONE=4


def pick_command():
    """
    Helper method to prompt the user to pick a command.

    :return: Associated command id
    """
    print("\nHere are the list of commands:")
    print("1. Set Light")
    print("2. Pick Effect")
    print("3. Pick Pallette")
    print("4. Enable Audio Sync")
    print("5. Disable Audio Sync")
    print("6. Create and start animation playlist")
    print("7. Stop animation playlist")
    print("8. Set Volume")
    print("9. Get Volume")
    return input("Enter command to send to server (or 'exit' to quit): ")


def convert_integer_input(integer: str):
    """
    Helper method to allow users to enter hex or dec for colors. Ideally
    users will enter colors in 0xRRGGBB format, but the option is there if
    they want to ented the value in dec.

    :param integer: integer string value
    :return: converted string into int
    """
    # Check if the input starts with '0x' or '0X' to identify hex
    return int(integer, 16) \
           if integer.startswith("0x") or integer.startswith("0X") \
           else int(integer)


def set_audio_output(device_name="BlackHole 2ch"):
    """
    Sets the output of the macbook
    """
    subprocess.run(["SwitchAudioSource", "-t", "output", "-s", device_name])


def start_stream_detached():
    global _ffmpeg_proc
    if _ffmpeg_proc and _ffmpeg_proc.poll() is None:
        print("FFmpeg already running")
        return

    FFmpeg_CMD = [
        "ffmpeg",
        "-f", "avfoundation",
        "-i", ":BlackHole 2ch",
        "-ac", "2",
        "-ar", "44100",
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "tcp://raspberrypi.local:5005"
    ]

    # Fully detach from Python process, ignore stdin/stdout/stderr
    _ffmpeg_proc = subprocess.Popen(
        FFmpeg_CMD,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid
    )

    # Give it a moment to fail if the device is busy
    sleep(1)
    if _ffmpeg_proc.poll() is not None:
        print("FFmpeg failed to start. Device may be busy.")
        _ffmpeg_proc = None
    else:
        print("FFmpeg stream started.")


def stop_stream():
    """
    Stops the running FFmpeg stream safely.
    """
    global _ffmpeg_proc

    if not _ffmpeg_proc or _ffmpeg_proc.poll() is not None:
        print("FFmpeg stream is not running.")
        return

    print("Stopping FFmpeg stream…")

    # Kill whole process group
    os.killpg(os.getpgid(_ffmpeg_proc.pid), signal.SIGTERM)

    _ffmpeg_proc = None
    print("FFmpeg stream stopped.")


def send_set_light_command():
    """
    Prompts user to enter color info. This color info is then sent to the
    rasberry pi server via JSON-RPC.

    :return: associated JSON-RPC request string
    """
    color = convert_integer_input(input("Enter a color: "))
    json_data = {
        "method" : "set_light",
        "params" : {
            "color" : str(hex(color))
        }
    }
    return json.dumps(json_data), False, CachedId.NONE



def send_trigger_effect_command():
    """
    Prompts user for trigger info. Once info is received,
    info is converted to JSON and sent to rasberry pi.

    :return: associated JSON-RPC request string
    """
    # present animation IDs
    print()
    names = list(ANIMATION_OPTIONS.keys())
    for index, effect in enumerate(names):
        info = ANIMATION_OPTIONS[effect]
        description = info["description"]
        print(f"{index + 1}. {effect}:\n  - {description}")
    effect_index = int(input("Enter an animation id from above: "))
    effect = ANIMATION_OPTIONS[names[effect_index - 1]]["id"]

    # specify color scheme/palette options
    print("\nPick the following Color Scheme:")
    names = list(CHRISTMAS_PALETTES.keys())
    for index, pallete in enumerate(names):
        print(f"{index + 1}. {pallete}")

    # specifies an option for pre-loaded color on pi server
    print(f"{len(names) + 1}. Default colors loaded on pi server.")

    scheme_choice = abs(int(input("Choose a scheme from the list above: ")))
    scheme = CHRISTMAS_PALETTES[names[scheme_choice - 1]] if scheme_choice <= len(names) else []

    # present speed options
    print("Enter a desired speed.\n - 1.0 = default\n - 2.0 = double speed\n - 0.5 = half speed")
    speed = float(input("Enter speed: "))

    # fill json data
    json_data = {
        "method" : "trigger_effect",
        "params" : {
            "animation_id" : effect,
            "color_scheme" : scheme,
            "speed" : speed
        }
    }
    return json.dumps(json_data), False, CachedId.NONE


def send_set_pallete_command():
    """
    Prompts user for color pallete info. Once info is received, the JSON
    data is created and returned.

    @return associated JSON-RPC request string
    """
    print("Pick the following Pallete:")
    names = list(CHRISTMAS_PALETTES.keys())
    for index, pallete in enumerate(names):
        print(f"{index + 1}. {pallete}")
    pallete_choice = int(input("Choose a pallete from the list above: "))
    if pallete_choice > len(names) or pallete_choice <= 0:
        print("Invalid coice, defaulting to 1")
        pallete_choice = 1
    json_data = {
        "method" : "set_pallete",
        "params" : {
            "pallete" : CHRISTMAS_PALETTES[names[pallete_choice - 1]]
        }
    }
    return json.dumps(json_data), False, CachedId.NONE


def _set_is_audio_sync_enabled(is_enabled):
    """Constructs `is_audio_sync_enabled` command"""
    # fill json data
    json_data = {
        "method" : "audio_sync_is_enabled",
        "params" : {
            "is_enabled" : is_enabled
        }
    }
    return json.dumps(json_data), False, CachedId.NONE

def send_enable_audio_sync_command():
    set_audio_output("BlackHole 2ch")
    start_stream_detached()
    return _set_is_audio_sync_enabled(True)


def send_disable_audio_sync_command():
    set_audio_output("MacBook Pro Speakers")
    stop_stream()
    return _set_is_audio_sync_enabled(False)

def send_start_animation_playlist_command():
    """Prompts a user to generate and send a playlist of animations"""
    add_animation = True
    animations = []
    while add_animation:
        print()
        names = list(ANIMATION_OPTIONS.keys())
        for index, effect in enumerate(names):
            info = ANIMATION_OPTIONS[effect]
            description = info["description"]
            print(f"{index + 1}. {effect}:\n  - {description}")
        effect_index = int(input("Enter an animation id from above: "))
        effect = ANIMATION_OPTIONS[names[effect_index - 1]]["id"]

        # present speed options
        print("Enter a desired speed.\n - 1.0 = default\n - 2.0 = double speed\n - 0.5 = half speed")
        speed = float(input("Enter speed: "))

        animations.append(
            {
                "animation_id": effect,
                "speed": speed
            }
        )

        add_animation = input("\nWould you like to add another animation to the playlist? (Y/n): ").strip().upper() == "Y"

    add_color_scheme = True
    color_schemes = []
    while add_color_scheme:
        # specify color scheme/palette options
        print("\nPick the following Color Scheme:")
        names = list(CHRISTMAS_PALETTES.keys())
        for index, pallete in enumerate(names):
            print(f"{index + 1}. {pallete}")

        # specifies an option for pre-loaded color on pi server
        print(f"{len(names) + 1}. Default colors loaded on pi server.")

        scheme_choice = abs(int(input("Choose a scheme from the list above: ")))
        scheme = CHRISTMAS_PALETTES[names[scheme_choice - 1]] if scheme_choice <= len(names) else []
        color_schemes.append(scheme)

        add_color_scheme = input("\nWould you like to add another color scheme? (Y/n): ").strip().upper() == "Y"

    time_delay = int(input("\nEnter the time delay between each animation (in seconds): "))

    json_data = {
        "method" : "start_animation_playlist",
        "params" : {
            "animations" : animations,
            "color_schemes" : color_schemes,
            "time_delay" : time_delay
        }
    }
    return json.dumps(json_data), False, CachedId.NONE


def send_stop_animation_playlist_command():
    json_data = {
        "method" : "stop_animation_playlist",
        "params" : {},
    }
    return json.dumps(json_data), False, CachedId.NONE


def set_volume():
    global VOLUME_STATE
    print(f"\nVolume is currently = {VOLUME_STATE}%")
    volume = int(input("Enter a volume between 0-100: "))
    json_data = {
        "method": "set_volume",
        "params" : {
            "volume" : volume
        },
    }
    VOLUME_STATE = volume
    return json.dumps(json_data), False, CachedId.NONE


def get_volume():
    json_data = {
        "method" : "get_volume",
        "params" : {},
    }
    return json.dumps(json_data), True, CachedId.VOLUME_STATE


def get_palettes():
    """Constructs `get_palettes` command"""
    json_data = {
        "method" : "get_palettes",
        "params" : {}
    }
    return json.dumps(json_data), True, CachedId.PALLETES


def get_effects():
    """Constructs `get_effects` command"""
    json_data = {
        "method" : "get_effects",
        "params" : {}
    }
    return json.dumps(json_data), True, CachedId.ANIMATION_EFFECTS

def construct_json(command) -> str:
    """
    Constructs a JSON-RPC request based on the provided command. This
    will call an associated method that returns the associated JSON-RPC
    request as a string.

    :param command: command id lookup. Ultimately points to function to call
    :return: JSON-RPC request string
    """
    commands = {
        1: send_set_light_command,
        2: send_trigger_effect_command,
        3: send_set_pallete_command,
        4: send_enable_audio_sync_command,
        5: send_disable_audio_sync_command,
        6: send_start_animation_playlist_command,
        7: send_stop_animation_playlist_command,
        8: set_volume,
        9: get_volume,
    }
    return commands[command]()

def recv_all(s):
    # Receive the response from the server
    data = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed before receiving valid JSON.")
            data += chunk
            json_data = json.loads(data.decode('utf-8'))
            break  # Exit the loop once JSON is successfully parsed
        except json.JSONDecodeError:
            # Continue receiving more data if JSON is incomplete
            continue
    return json_data


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        global CHRISTMAS_PALETTES
        global ANIMATION_OPTIONS
        global VOLUME_STATE
        s.connect((HOST, PORT))  # Connect to the server
        print(f"Connected to server at {HOST}:{PORT}")

        palette_command, _, _ = get_palettes()
        s.sendall(palette_command.encode('utf-8'))
        CHRISTMAS_PALETTES = recv_all(s)["result"]

        effects_command, _, _ = get_effects()
        s.sendall(effects_command.encode('utf-8'))
        ANIMATION_OPTIONS = recv_all(s)["result"]

        volume_command, _, _ = get_volume()
        s.sendall(volume_command.encode('utf-8'))
        VOLUME_STATE = recv_all(s)["result"]["volume"]

        while True:
            command = pick_command()
            if command.lower() == 'exit':
                print("Exiting...")
                break

            # Send the command to the server
            json_command, is_getter, cache_type = construct_json(int(command))
            s.sendall(json_command.encode('utf-8'))
            json_data = recv_all(s)

            if is_getter:
                result = json_data["result"]
                if cache_type == CachedId.VOLUME_STATE:
                    VOLUME_STATE = result["volume"]
                    print(f"Volume = {VOLUME_STATE}")
                elif cache_type == CachedId.PALLETES:
                    CHRISTMAS_PALETTES = result
                elif cache_type == CachedId.ANIMATION_EFFECTS:
                    ANIMATION_OPTIONS = result
                print(f"Succesfully received data from server")
            else:
                print(f"Received from server:\n{json.dumps(json_data, indent=4)}")

if __name__ == "__main__":
    main()
